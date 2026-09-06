"""An experiment, not a gate: does importing the heavy modules at startup free it?

Probe 5 and the full probe 3 dumps settled the mechanism. The tool thread
stalls inside DuckDB's lazy `import pandas` (which loads numpy's C
extension) on the first parameterized query, and on Windows that DLL load
waits behind the pending synchronous stdin read; any stdin event releases
it. Measured off Windows: DuckDB 1.4.3 imports pandas and numpy on the
first parameterized `execute` in a process, never on literal SQL, and once
pandas and numpy are imported the parameterized query is immediate. So the
fix is to load them before the transport opens stdin.

    uv run python scripts/stdio_probe.py

  V0 control: the shipped server, for the reproduction.
  V1 fix: the same server with `import pandas` and `import numpy` done at
     startup, before the module runs and before any stdin reader exists.

Every wait is bounded. The `faulthandler` stack dumps stay on, so V0's
stall is named in the tool's import frame and V1 shows none. Keyless; no
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

WRAP_CONTROL = (
    DUMP
    + r"""
import runpy
runpy.run_module("metricmine.server", run_name="__main__")
"""
)

# The fix as it will ship: the heavy modules DuckDB imports lazily on the
# first parameterized query are loaded here, before the stdio transport
# starts its stdin reader, so the numpy C-extension DLL load never runs with
# a synchronous stdin read already pending.
WRAP_FIX = (
    DUMP
    + r"""
import sys
import pandas  # noqa: F401
import numpy  # noqa: F401
sys.stderr.write("[wrapper] pandas and numpy imported before the transport\n"); sys.stderr.flush()
import runpy
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
            "clientInfo": {"name": "metricmine-stdio-probe", "version": "6"},
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
        results["V0 control"] = run_variant(
            "V0 control", [str(exe), "-c", WRAP_CONTROL], env, cwd
        )
        results["V1 fix"] = run_variant("V1 fix", [str(exe), "-c", WRAP_FIX], env, cwd)
    say(
        "SUMMARY "
        + "; ".join(f"{k}: {'PASS' if v else 'FAIL'}" for k, v in results.items())
    )
    say("probe done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
