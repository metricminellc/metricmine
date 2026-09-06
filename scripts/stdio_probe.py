"""An experiment, not a gate: which stdout path frees the large answer?

Probe 3 (run 34045163103) named the frame. On Windows the server's main
thread sits in the asyncio ProactorEventLoop poll
(`asyncio\\windows_events.py` `_poll` -> `GetQueuedCompletionStatus`), the
anyio worker threads idle in `queue.get`, and the third answer, the first
that carries the running total past the pipe buffer, is not written until
the next stdin event wakes the completion port. The mcp SDK's stdout
writer pushes every answer through `anyio.to_thread` worker-thread writes
(`mcp/server/stdio.py`, `stdout_writer`). Every candidate so far left that
path intact and failed. This probe tries stdout paths that leave it.

    uv run python scripts/stdio_probe.py

  R0 control: the shipped server, for the reproduction.
  R1 thread-writer: stdout written by a dedicated OS thread off a plain
     queue.Queue, handed to stdio_server(stdout=...); the coroutine's write
     only enqueues, so it never waits on the loop's completion-port wakeup.
  R2 inline: stdout written synchronously in the coroutine itself, no
     worker thread at all (stdio_server(stdout=...) with blocking write).
  R3 selector: the server run on a WindowsSelectorEventLoopPolicy loop
     through a clean asyncio.run, bypassing FastMCP.run and anyio.run, so
     the loop is provably the selector and not the proactor.

Every wait is bounded; the whole probe takes about three minutes even when
every candidate fails. Keyless; no network.
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

# R0: the shipped server, unaltered but for the stack dumps.
WRAP_CONTROL = (
    DUMP
    + r"""
import runpy
runpy.run_module("metricmine.server", run_name="__main__")
"""
)

# R1: a dedicated OS thread writes stdout off a plain queue; the coroutine's
# write only enqueues. No dependency on the loop's completion-port wakeup for
# the bytes to leave the process.
WRAP_THREAD_WRITER = (
    DUMP
    + r"""
import runpy, sys, threading, queue as _q
import mcp.server.stdio as stdio
import mcp.server.fastmcp.server as fs
class ThreadWriter:
    def __init__(self):
        self._q = _q.Queue()
        self._buf = sys.stdout.buffer
        self._t = threading.Thread(target=self._run, name="stdout-writer", daemon=True)
        self._t.start()
    def _run(self):
        while True:
            data = self._q.get()
            if data is None:
                return
            self._buf.write(data); self._buf.flush()
    async def write(self, s):
        self._q.put(s.encode("utf-8"))
    async def flush(self):
        pass
async def run_stdio_async(self):
    async with stdio.stdio_server(stdout=ThreadWriter()) as (read_stream, write_stream):
        await self._mcp_server.run(read_stream, write_stream, self._mcp_server.create_initialization_options())
fs.FastMCP.run_stdio_async = run_stdio_async
sys.stderr.write("[wrapper] stdout written by a dedicated thread off a queue\n"); sys.stderr.flush()
runpy.run_module("metricmine.server", run_name="__main__")
"""
)

# R2: stdout written synchronously in the coroutine, no worker thread.
WRAP_INLINE = (
    DUMP
    + r"""
import runpy, sys
import mcp.server.stdio as stdio
import mcp.server.fastmcp.server as fs
class InlineWriter:
    def __init__(self):
        self._buf = sys.stdout.buffer
    async def write(self, s):
        self._buf.write(s.encode("utf-8"))
    async def flush(self):
        self._buf.flush()
async def run_stdio_async(self):
    async with stdio.stdio_server(stdout=InlineWriter()) as (read_stream, write_stream):
        await self._mcp_server.run(read_stream, write_stream, self._mcp_server.create_initialization_options())
fs.FastMCP.run_stdio_async = run_stdio_async
sys.stderr.write("[wrapper] stdout written inline in the coroutine, no worker thread\n"); sys.stderr.flush()
runpy.run_module("metricmine.server", run_name="__main__")
"""
)

# R3: the server on a provably selector loop, through a clean asyncio.run
# that bypasses FastMCP.run and anyio.run entirely.
WRAP_SELECTOR = (
    DUMP
    + r"""
import asyncio, sys
from mcp.server.stdio import stdio_server
from metricmine.server.app import server
async def _main():
    async with stdio_server() as (read_stream, write_stream):
        await server._mcp_server.run(read_stream, write_stream, server._mcp_server.create_initialization_options())
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
sys.stderr.write(f"[wrapper] loop policy {type(asyncio.get_event_loop_policy()).__name__}\n"); sys.stderr.flush()
asyncio.run(_main())
"""
)


class Walker:
    """Newline-delimited JSON-RPC over a child's pipes; every wait bounded."""

    def __init__(self, proc: subprocess.Popen[bytes], label: str) -> None:
        self.proc = proc
        self.label = label
        self.lines: queue.Queue[bytes | None] = queue.Queue()
        self.arrivals: list[tuple[float, int, str]] = []
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
            "clientInfo": {"name": "metricmine-stdio-probe", "version": "4"},
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
        # A second large answer, to see the fix hold past the first.
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
            f"{label} RESULT: {'PASS' if answered else 'FAIL'}; arrivals: "
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
        results["R0 control"] = run_variant(
            "R0 control", [str(exe), "-c", WRAP_CONTROL], env, cwd
        )
        results["R1 thread-writer"] = run_variant(
            "R1 thread-writer", [str(exe), "-c", WRAP_THREAD_WRITER], env, cwd
        )
        results["R2 inline"] = run_variant(
            "R2 inline", [str(exe), "-c", WRAP_INLINE], env, cwd
        )
        results["R3 selector"] = run_variant(
            "R3 selector", [str(exe), "-c", WRAP_SELECTOR], env, cwd
        )
    say(
        "SUMMARY "
        + "; ".join(f"{k}: {'PASS' if v else 'FAIL'}" for k, v in results.items())
    )
    say("probe done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
