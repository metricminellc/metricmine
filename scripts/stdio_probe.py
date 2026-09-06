"""An experiment, not a gate: which fix makes the third answer arrive on Windows?

Probe 1 (run 34042155102) settled the behavior: on a Windows runner the
server the desktop config launches answers `initialize` and `tools/list`
at once, dispatches `tools/call list_fact_categories`, and writes that
third answer (the first larger than 8 KB) only when the next line or the
end-of-file arrives on its stdin: a `ping` after the deadline brought the
answer within half a second, the same with stdout redirected to a file,
the same through the base interpreter. The instrumented layers showed the
write itself is instant once it is called; the delay is before the SDK's
stdout writer is called at all. On ubuntu every variant answered at once.

This probe runs the same walk four times: a control, then three candidate
fixes applied as launch wrappers that patch the SDK's stdio run before the
server's own entry point starts. Nothing on main changes; the branch never
merges (CLAUDE.md rule 19).

    uv run python scripts/stdio_probe.py

  P1 control: the server as shipped (expected to stop at the third answer
     on Windows, as in probe 1).
  P2 sync-stdout: the server's stdout handed to `stdio_server()` as an
     object whose write and flush run on the event loop itself, with no
     worker thread and with `newline="\\n"` (no CRLF on Windows).
  P3 selector-loop: `asyncio.WindowsSelectorEventLoopPolicy` set before
     the server starts, so anyio runs on a selector loop instead of the
     proactor (no-op on Linux).
  P4 ticker: a task that sleeps 100 ms in a loop beside the server, so the
     event loop wakes on a timer whatever else happens.

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


WRAP_SYNC_STDOUT = r"""
import io, runpy, sys
import mcp.server.stdio as stdio
import mcp.server.fastmcp.server as fs
class SyncStdout:
    def __init__(self):
        self._fp = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n", write_through=True)
    async def write(self, text):
        self._fp.write(text)
    async def flush(self):
        self._fp.flush()
async def run_stdio_async(self):
    async with stdio.stdio_server(stdout=SyncStdout()) as (read_stream, write_stream):
        await self._mcp_server.run(read_stream, write_stream, self._mcp_server.create_initialization_options())
fs.FastMCP.run_stdio_async = run_stdio_async
sys.stderr.write("[wrapper] sync stdout on the loop, newline=\\n\n"); sys.stderr.flush()
runpy.run_module("metricmine.server", run_name="__main__")
"""

WRAP_SELECTOR = r"""
import asyncio, runpy, sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
sys.stderr.write(f"[wrapper] policy {type(asyncio.get_event_loop_policy()).__name__}\n"); sys.stderr.flush()
runpy.run_module("metricmine.server", run_name="__main__")
"""

WRAP_TICKER = r"""
import runpy, sys
import anyio
import mcp.server.fastmcp.server as fs
orig = fs.FastMCP.run_stdio_async
async def run_stdio_async(self):
    async with anyio.create_task_group() as tg:
        async def tick():
            while True:
                await anyio.sleep(0.1)
        tg.start_soon(tick)
        try:
            await orig(self)
        finally:
            tg.cancel_scope.cancel()
fs.FastMCP.run_stdio_async = run_stdio_async
sys.stderr.write("[wrapper] 100 ms ticker beside the server\n"); sys.stderr.flush()
runpy.run_module("metricmine.server", run_name="__main__")
"""


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
            "clientInfo": {"name": "metricmine-stdio-probe", "version": "2"},
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
        results["P1 control"] = run_variant(
            "P1 control", [str(exe), "-m", "metricmine.server"], env, cwd
        )
        results["P2 sync-stdout"] = run_variant(
            "P2 sync-stdout", [str(exe), "-c", WRAP_SYNC_STDOUT], env, cwd
        )
        results["P3 selector-loop"] = run_variant(
            "P3 selector-loop", [str(exe), "-c", WRAP_SELECTOR], env, cwd
        )
        results["P4 ticker"] = run_variant(
            "P4 ticker", [str(exe), "-c", WRAP_TICKER], env, cwd
        )
    say(
        "SUMMARY "
        + "; ".join(f"{k}: {'PASS' if v else 'FAIL'}" for k, v in results.items())
    )
    say("probe done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
