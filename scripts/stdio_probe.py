"""An experiment, not a gate: do buffered streams or a heartbeat free the answer?

Probes 1 through 4 ruled out the stdout write path (to_thread, a dedicated
thread, an inline write), both event loops (proactor and selector), the
stdin read mechanism, interpreter buffering, a loop timer, and the tool run
in a worker thread. The stall is upstream of the stdout write and released
only by a stdin event, and it is size-gated. Two candidates remain, both
from the upstream lead (SDK issue #1141 fingers the buffer-0 memory streams
at `stdio.py` L57):

    uv run python scripts/stdio_probe.py

  U0 control: the shipped server, for the reproduction.
  U1 buffered: the transport's memory-object streams created with a real
     buffer instead of 0, so the handler's response send never has to
     rendezvous with the writer to complete.
  U2 heartbeat: a background task sends a logging notification every 150 ms
     through the same write stream, so the server generates outbound traffic
     on its own; if that frees the answer, a keepalive is a real fix (and it
     shows whether the loop is even servicing its own timers).
  U3 both: buffered streams and the heartbeat together.

Every wait is bounded; the whole probe takes about three minutes even when
every candidate fails. The `faulthandler` stack dumps stay on. Keyless; no
network.
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from mcp.client.stdio import get_default_environment
from mcp.types import LATEST_PROTOCOL_VERSION

REPO = Path(__file__).resolve().parents[1]
REQUEST_TIMEOUT = 30.0
DRAIN = 5.0
T0 = time.monotonic()


def now() -> float:
    return time.monotonic() - T0


def say(line: str) -> None:
    print(f"[{now():8.3f}] {line}", flush=True)


def interpreter() -> Path:
    if sys.platform == "win32":
        return REPO / ".venv" / "Scripts" / "python.exe"
    return REPO / ".venv" / "bin" / "python"


DUMP = "import faulthandler, sys; faulthandler.dump_traceback_later(8, repeat=True, file=sys.stderr)\n"

# Shared prelude: a buffered stdio_server and a heartbeat installer. install()
# swaps FastMCP.run_stdio_async for one that picks the buffered transport
# and/or starts the heartbeat task, then the module runs as usual.
COMMON = r"""
import anyio, sys, runpy
from io import TextIOWrapper
from contextlib import asynccontextmanager
import mcp.types as types
from mcp.shared.message import SessionMessage
import mcp.server.stdio as stdio
import mcp.server.fastmcp.server as fs

BUF = 256

def _hb_message():
    return SessionMessage(types.JSONRPCMessage.model_validate(
        {"jsonrpc": "2.0", "method": "notifications/message",
         "params": {"level": "debug", "logger": "hb", "data": "heartbeat"}}
    ))

@asynccontextmanager
async def _buffered_server():
    _stdin = anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace"))
    _stdout = anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding="utf-8"))
    rsw, rs = anyio.create_memory_object_stream(BUF)
    ws, wsr = anyio.create_memory_object_stream(BUF)
    async def _rd():
        async with rsw:
            async for line in _stdin:
                try:
                    m = types.JSONRPCMessage.model_validate_json(line)
                except Exception as exc:
                    await rsw.send(exc); continue
                await rsw.send(SessionMessage(m))
    async def _wr():
        async with wsr:
            async for m in wsr:
                j = m.message.model_dump_json(by_alias=True, exclude_none=True)
                await _stdout.write(j + "\n"); await _stdout.flush()
    async with anyio.create_task_group() as tg:
        tg.start_soon(_rd); tg.start_soon(_wr)
        yield rs, ws

def install(buffered, heartbeat):
    server_cm = _buffered_server if buffered else stdio.stdio_server
    async def run_stdio_async(self):
        async with server_cm() as (rs, ws):
            async with anyio.create_task_group() as tg:
                if heartbeat:
                    async def _hb():
                        while True:
                            await anyio.sleep(0.15)
                            try:
                                await ws.send(_hb_message())
                            except Exception:
                                return
                    tg.start_soon(_hb)
                await self._mcp_server.run(rs, ws, self._mcp_server.create_initialization_options())
                tg.cancel_scope.cancel()
    fs.FastMCP.run_stdio_async = run_stdio_async
    sys.stderr.write("[wrapper] buffered=%s heartbeat=%s BUF=%s\n" % (buffered, heartbeat, BUF)); sys.stderr.flush()
"""

WRAP_CONTROL = (
    DUMP
    + r"""
import runpy
runpy.run_module("metricmine.server", run_name="__main__")
"""
)
WRAP_BUFFERED = (
    DUMP
    + COMMON
    + '\ninstall(True, False)\nrunpy.run_module("metricmine.server", run_name="__main__")\n'
)
WRAP_HEARTBEAT = (
    DUMP
    + COMMON
    + '\ninstall(False, True)\nrunpy.run_module("metricmine.server", run_name="__main__")\n'
)
WRAP_BOTH = (
    DUMP
    + COMMON
    + '\ninstall(True, True)\nrunpy.run_module("metricmine.server", run_name="__main__")\n'
)


class Walker:
    """Newline-delimited JSON-RPC over a child's pipes; every wait bounded.

    Heartbeat notifications are counted, not printed, so the log stays legible.
    """

    def __init__(self, proc: subprocess.Popen[bytes], label: str) -> None:
        self.proc = proc
        self.label = label
        self.lines: queue.Queue[bytes | None] = queue.Queue()
        self.arrivals: list[tuple[float, int, str]] = []
        self.heartbeats = 0
        self._next_id = 0
        threading.Thread(target=self._read, name="server-stdout", daemon=True).start()

    def _read(self) -> None:
        assert self.proc.stdout is not None
        try:
            for raw in self.proc.stdout:
                self.lines.put(raw)
        finally:
            self.lines.put(None)

    def send(self, message: dict) -> None:
        assert self.proc.stdin is not None
        data = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
        self.proc.stdin.write(data)
        self.proc.stdin.flush()

    def describe(self, raw: bytes) -> str:
        line = raw.decode("utf-8", errors="replace").strip()
        try:
            message = json.loads(line)
        except ValueError:
            return f"not JSON: {line[:60]!r}"
        if "id" in message and ("result" in message or "error" in message):
            return f"answer id={message['id']}"
        return f"method={message.get('method')}"

    def note(self, raw: bytes, tag: str) -> str:
        what = self.describe(raw)
        if what == "method=notifications/message":
            self.heartbeats += 1
            return what
        self.arrivals.append((now(), len(raw), what))
        say(f"{self.label} {tag}: {len(raw)} bytes, {what}")
        return what

    def request(
        self, method: str, params: dict | None = None, timeout: float = REQUEST_TIMEOUT
    ):
        self._next_id += 1
        rid = self._next_id
        started = now()
        self.send(
            {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
        )
        say(f"{self.label} sent {method} id={rid}")
        deadline = started + timeout
        while True:
            remaining = deadline - now()
            if remaining <= 0:
                say(f"{self.label} TIMEOUT {method} id={rid} after {timeout:g} s")
                return None, 0, now() - started
            try:
                raw = self.lines.get(timeout=remaining)
            except queue.Empty:
                say(f"{self.label} TIMEOUT {method} id={rid} after {timeout:g} s")
                return None, 0, now() - started
            if raw is None:
                say(
                    f"{self.label} EOF on stdout before {method} answered (poll={self.proc.poll()})"
                )
                return None, 0, now() - started
            what = self.note(raw, "arrival")
            if what == f"answer id={rid}":
                message = json.loads(raw.decode("utf-8", errors="replace"))
                return (
                    message.get("result", message.get("error")),
                    len(raw),
                    now() - started,
                )

    def drain(self, seconds: float, tag: str) -> int:
        end = now() + seconds
        count = 0
        while True:
            remaining = end - now()
            if remaining <= 0:
                break
            try:
                raw = self.lines.get(timeout=remaining)
            except queue.Empty:
                break
            if raw is None:
                say(
                    f"{self.label} EOF on stdout during {tag} (poll={self.proc.poll()})"
                )
                break
            self.note(raw, f"late arrival during {tag}")
            count += 1
        say(f"{self.label} drain {tag}: {count} arrival(s) in {seconds:g} s")
        return count

    def close_stdin(self) -> None:
        if self.proc.stdin is not None:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
        say(f"{self.label} stdin closed")

    def finish(self) -> None:
        started = now()
        try:
            code = self.proc.wait(timeout=DRAIN)
            say(f"{self.label} server exited {code} in {now() - started:.1f} s")
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            try:
                code = self.proc.wait(timeout=DRAIN)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                code = self.proc.wait()
            say(
                f"{self.label} server did not exit on EOF; terminated, exit code {code}"
            )


def walk(w: Walker) -> bool:
    """Return True when the third answer arrived within the deadline."""
    init, size, took = w.request(
        "initialize",
        {
            "protocolVersion": LATEST_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "metricmine-stdio-probe", "version": "5"},
        },
    )
    if init is None:
        return False
    w.send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    tools, size, took = w.request("tools/list")
    if tools is None:
        return False
    call, size, took = w.request(
        "tools/call", {"name": "list_fact_categories", "arguments": {}}
    )
    if call is not None:
        cats = (
            call.get("structuredContent", {}).get("categories", [])
            if isinstance(call, dict)
            else []
        )
        say(
            f"{w.label} tools/call answered: {size} bytes, {len(cats)} categories, {took * 1000:.0f} ms"
        )
        again, size, took = w.request(
            "tools/call", {"name": "list_fact_categories", "arguments": {}}
        )
        say(
            f"{w.label} second tools/call {'answered' if again is not None else 'NOT answered'}: {size} bytes, {took * 1000:.0f} ms"
        )
        return again is not None
    w.send({"jsonrpc": "2.0", "id": 99, "method": "ping", "params": {}})
    say(f"{w.label} poke: sent ping id=99")
    w.drain(DRAIN, "after the poke")
    return False


def run_variant(label: str, cmd: list[str], env: dict[str, str], cwd: str) -> bool:
    say(f"== {label} ==")
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
        cwd=cwd,
        env=env,
    )
    w = Walker(proc, label)
    answered = False
    try:
        answered = walk(w)
    finally:
        w.close_stdin()
        w.drain(1.0 if answered else DRAIN, "after stdin closed")
        w.finish()
        say(
            f"{label} RESULT: {'PASS' if answered else 'FAIL'}; heartbeats seen: {w.heartbeats}; arrivals: "
            + "; ".join(f"{t:.3f}s {n}b {what}" for t, n, what in w.arrivals)
        )
    return answered


def main() -> int:
    exe = interpreter()
    if not exe.is_file():
        say(f"no interpreter at {exe}")
        return 1
    env = get_default_environment()
    say(
        f"platform {sys.platform}, probe python {sys.version.split()[0]}, interpreter {exe}"
    )
    results = {}
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as cwd:
        results["U0 control"] = run_variant(
            "U0 control", [str(exe), "-c", WRAP_CONTROL], env, cwd
        )
        results["U1 buffered"] = run_variant(
            "U1 buffered", [str(exe), "-c", WRAP_BUFFERED], env, cwd
        )
        results["U2 heartbeat"] = run_variant(
            "U2 heartbeat", [str(exe), "-c", WRAP_HEARTBEAT], env, cwd
        )
        results["U3 both"] = run_variant(
            "U3 both", [str(exe), "-c", WRAP_BOTH], env, cwd
        )
    say(
        "SUMMARY "
        + "; ".join(f"{k}: {'PASS' if v else 'FAIL'}" for k, v in results.items())
    )
    say("probe done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
