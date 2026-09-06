"""An experiment, not a gate: where is the server blocked, and what frees it?

Probe 2 (run 34043637817) failed all three candidates on Windows: stdout
written on the loop with no worker thread, the selector event loop, and a
100 ms ticker task. The third answer (the first over 8 KB) still arrived
only after the next stdin line, in every case within half a second of the
poke. A ticker task that cannot run is one that has no loop to run on, so
the main thread itself is the suspect: blocked in something synchronous
that a stdin read on another thread releases. This probe makes the server
dump every thread's stack to stderr every 8 seconds (faulthandler), so
the blocked frame is named, and tries three more candidates.

    uv run python scripts/stdio_probe.py

  Q1 control: the shipped server, with the stack dumps.
  Q2 tool-thread: the sync tool function run in a worker thread instead
     of on the event loop (the SDK's call_fn_with_arg_validation patched).
  Q3 raw-stdin: the server's stdin read by Win32 ReadFile through ctypes
     on a worker thread (os.read on Linux), never through the C runtime's
     _read and its per-descriptor lock; handed to stdio_server() as stdin.
  Q4 unbuffered: the server started with python -u (stdout and stderr
     unbuffered at the interpreter level).

Every wait is bounded; the whole probe takes under three minutes even when
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

WRAP_CONTROL = (
    DUMP
    + r"""
import runpy
runpy.run_module("metricmine.server", run_name="__main__")
"""
)

WRAP_TOOL_THREAD = (
    DUMP
    + r"""
import runpy, sys
import anyio
from mcp.server.fastmcp.utilities import func_metadata as fm
orig = fm.FuncMetadata.call_fn_with_arg_validation
async def patched(self, fn, fn_is_async, arguments_to_validate, arguments_to_pass_directly):
    if fn_is_async:
        return await orig(self, fn, fn_is_async, arguments_to_validate, arguments_to_pass_directly)
    pre = self.pre_parse_json(arguments_to_validate)
    parsed = self.arg_model.model_validate(pre).model_dump_one_level()
    parsed |= arguments_to_pass_directly or {}
    return await anyio.to_thread.run_sync(lambda: fn(**parsed))
fm.FuncMetadata.call_fn_with_arg_validation = patched
sys.stderr.write("[wrapper] sync tools run in a worker thread\n"); sys.stderr.flush()
runpy.run_module("metricmine.server", run_name="__main__")
"""
)

WRAP_RAW_STDIN = (
    DUMP
    + r"""
import runpy, sys
import anyio
import mcp.server.stdio as stdio
import mcp.server.fastmcp.server as fs
if sys.platform == "win32":
    import ctypes, msvcrt
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    HANDLE = wintypes.HANDLE(msvcrt.get_osfhandle(0))
    def read_chunk():
        buf = ctypes.create_string_buffer(65536)
        n = wintypes.DWORD(0)
        ok = k32.ReadFile(HANDLE, buf, 65536, ctypes.byref(n), None)
        return buf.raw[: n.value] if ok else b""
    HOW = "Win32 ReadFile through ctypes"
else:
    import os
    def read_chunk():
        return os.read(0, 65536)
    HOW = "os.read"
class RawStdin:
    def __init__(self):
        self._buf = b""
        self._eof = False
    def __aiter__(self):
        return self
    async def __anext__(self):
        line = await anyio.to_thread.run_sync(self._next_line)
        if line is None:
            raise StopAsyncIteration
        return line
    def _next_line(self):
        while True:
            i = self._buf.find(b"\n")
            if i >= 0:
                line, self._buf = self._buf[: i + 1], self._buf[i + 1 :]
                return line.decode("utf-8", "replace")
            if self._eof:
                if self._buf:
                    line, self._buf = self._buf, b""
                    return line.decode("utf-8", "replace")
                return None
            chunk = read_chunk()
            if not chunk:
                self._eof = True
            else:
                self._buf += chunk
async def run_stdio_async(self):
    async with stdio.stdio_server(stdin=RawStdin()) as (read_stream, write_stream):
        await self._mcp_server.run(read_stream, write_stream, self._mcp_server.create_initialization_options())
fs.FastMCP.run_stdio_async = run_stdio_async
sys.stderr.write(f"[wrapper] stdin read by {HOW} on a worker thread\n"); sys.stderr.flush()
runpy.run_module("metricmine.server", run_name="__main__")
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
            "clientInfo": {"name": "metricmine-stdio-probe", "version": "3"},
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
        results["Q1 control"] = run_variant(
            "Q1 control", [str(exe), "-c", WRAP_CONTROL], env, cwd
        )
        results["Q2 tool-thread"] = run_variant(
            "Q2 tool-thread", [str(exe), "-c", WRAP_TOOL_THREAD], env, cwd
        )
        results["Q3 raw-stdin"] = run_variant(
            "Q3 raw-stdin", [str(exe), "-c", WRAP_RAW_STDIN], env, cwd
        )
        results["Q4 unbuffered"] = run_variant(
            "Q4 unbuffered", [str(exe), "-u", "-c", WRAP_CONTROL], env, cwd
        )
    say(
        "SUMMARY "
        + "; ".join(f"{k}: {'PASS' if v else 'FAIL'}" for k, v in results.items())
    )
    say("probe done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
