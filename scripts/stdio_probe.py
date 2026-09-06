"""An experiment, not a gate: where does the third answer go on Windows?

Cycle one and cycle two of the Windows check (runs 34032638337 and
34038469537) both stopped at the same place: the server the desktop config
launches answered `initialize` and `tools/list`, logged the dispatch of
`tools/call list_fact_categories`, and no third answer reached the client
within the deadline, through two different clients. In cycle two the
server then exited 0 within 0.6 s of stdin closing. This probe runs six
bounded variants of the same walk in one process and prints a timestamped
line for everything that happens, on both sides of the pipe, so one runner
cycle names the layer that holds the answer. It lives on an experiment
branch and never merges (CLAUDE.md rule 19: experiments end in findings).

    uv run python scripts/stdio_probe.py

Variants:
  V1 baseline: the smoke's walk; on a timeout, a `ping` request (the poke)
     and a five-second drain; then stdin closed and a five-second drain;
     every arrival printed with its time, size, and id.
  V2 instrumented: the same walk against a server whose stdout is wrapped
     at two layers (the buffered writer the SDK's text wrapper calls, and
     the raw file the buffer calls), each write and flush logged to stderr
     with the requested length, the returned count, and the time.
  V3 file: the server's stdout redirected to a file; the four messages
     sent blind; the file's size polled for thirty seconds, then stdin
     closed, then polled again; the file's messages listed.
  V4 small first: `tools/call query` with `select 1` (a tiny answer that
     opens the warehouse) before `list_fact_categories`, to separate the
     answer's size from the first open of the warehouse in the server.
  V5 debug log: V1 with FASTMCP_LOG_LEVEL=DEBUG in the server's
     environment, so the SDK logs the dispatch and the received messages.
  V6 base interpreter: V1 with the interpreter named by the venv's
     pyvenv.cfg `home` and the venv's site directory added by hand, no
     venv launcher between the probe and the server.

Every wait is bounded; the whole probe takes under six minutes even when
every answer is late. Keyless; no network.
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
FILE_POLL = 30.0
T0 = time.monotonic()


def now() -> float:
    return time.monotonic() - T0


def say(line: str) -> None:
    print(f"[{now():8.3f}] {line}", flush=True)


def interpreter() -> Path:
    if sys.platform == "win32":
        return REPO / ".venv" / "Scripts" / "python.exe"
    return REPO / ".venv" / "bin" / "python"


def site_packages() -> Path:
    if sys.platform == "win32":
        return REPO / ".venv" / "Lib" / "site-packages"
    return (
        REPO
        / ".venv"
        / "lib"
        / f"python{sys.version_info[0]}.{sys.version_info[1]}"
        / "site-packages"
    )


def base_interpreter() -> Path | None:
    cfg = REPO / ".venv" / "pyvenv.cfg"
    if not cfg.is_file():
        return None
    for line in cfg.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "home":
            home = Path(value.strip())
            names = (
                ["python.exe"]
                if sys.platform == "win32"
                else [
                    f"python{sys.version_info[0]}.{sys.version_info[1]}",
                    "python3",
                    "python",
                ]
            )
            for name in names:
                if (home / name).is_file():
                    return home / name
            return None
    return None


# The server launched through a wrapper that logs every write and flush at
# the buffered layer (what the SDK's TextIOWrapper calls) and the raw layer
# (what reaches the OS), then runs the server's own entry point.
INSTRUMENT = r"""
import io, runpy, sys, time
T0 = time.monotonic()
ERR = sys.stderr
def log(line):
    ERR.write(f"[stdout-instrument {time.monotonic() - T0:8.3f}] {line}\n"); ERR.flush()
class RawProxy(io.RawIOBase):
    def __init__(self, fio): self.fio = fio
    def writable(self): return True
    def fileno(self): return self.fio.fileno()
    def write(self, b):
        n = len(b); t = time.monotonic()
        r = self.fio.write(b)
        log(f"raw.write({n}) -> {r} in {time.monotonic() - t:.3f} s")
        return r
    def flush(self):
        self.fio.flush()
class BufProxy(io.BufferedWriter):
    def write(self, b):
        n = len(b); t = time.monotonic()
        r = super().write(b)
        log(f"buffered.write({n}) -> {r} in {time.monotonic() - t:.3f} s")
        return r
    def flush(self):
        t = time.monotonic()
        super().flush()
        log(f"buffered.flush() in {time.monotonic() - t:.3f} s")
sys.stdout = io.TextIOWrapper(BufProxy(RawProxy(io.FileIO(1, "wb", closefd=False)), buffer_size=8192), encoding="utf-8")
log(f"instrumented stdout on {sys.platform} python {sys.version.split()[0]}")
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
        self.eof = False
        if proc.stdout is not None:
            threading.Thread(
                target=self._read, name="server-stdout", daemon=True
            ).start()

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
        """Send; wait for the answer with this id; return (result_or_None, size, secs)."""
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
                self.eof = True
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
        """Report everything that arrives in the window; return the count."""
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
                self.eof = True
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


def launch(
    cmd: list[str],
    env: dict[str, str],
    label: str,
    stdout=subprocess.PIPE,
    cwd: str = "",
) -> subprocess.Popen[bytes]:
    say(f"{label} launch: {cmd[0]} {cmd[1]} {'...' if len(cmd) > 2 else ''} cwd={cwd}")
    return subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=stdout, stderr=None, cwd=cwd or None, env=env
    )


def walk(w: Walker, small_first: bool = False) -> bool:
    """Return True when the third answer arrived."""
    init, size, took = w.request(
        "initialize",
        {
            "protocolVersion": LATEST_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "metricmine-stdio-probe", "version": "1"},
        },
    )
    if init is None:
        return False
    w.send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    tools, size, took = w.request("tools/list")
    if tools is None:
        return False
    if small_first:
        small, size, took = w.request(
            "tools/call",
            {"name": "query", "arguments": {"sql": "select 1 as one", "row_cap": 1}},
        )
        say(
            f"{w.label} small call {'answered' if small is not None else 'NOT answered'}: {size} bytes"
        )
        if small is None:
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
        return True
    # No third answer: poke, drain, close stdin, drain.
    w.send({"jsonrpc": "2.0", "id": 99, "method": "ping", "params": {}})
    say(f"{w.label} poke: sent ping id=99")
    w.drain(DRAIN, "after the poke")
    return False


def run_variant(
    label: str, cmd: list[str], env: dict[str, str], cwd: str, small_first: bool = False
) -> None:
    say(f"== {label} ==")
    proc = launch(cmd, env, label, cwd=cwd)
    w = Walker(proc, label)
    answered = False
    try:
        answered = walk(w, small_first=small_first)
    finally:
        w.close_stdin()
        w.drain(1.0 if answered else DRAIN, "after stdin closed")
        w.finish()
        w.drain(1.0, "after exit")
        say(
            f"{label} arrivals: "
            + "; ".join(f"{t:.3f}s {n}b {what}" for t, n, what in w.arrivals)
        )


def variant_file(label: str, cmd: list[str], env: dict[str, str], cwd: str) -> None:
    say(f"== {label} ==")
    path = Path(cwd) / "stdout.jsonl"
    with open(path, "wb") as out:
        proc = launch(cmd, env, label, stdout=out, cwd=cwd)
        w = Walker(proc, label)
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": LATEST_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "metricmine-stdio-probe", "version": "1"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "list_fact_categories", "arguments": {}},
            },
        ]
        for m in messages:
            w.send(m)
            say(f"{label} sent {m.get('method')} id={m.get('id')}")
            time.sleep(1.0)
        last = -1
        end = now() + FILE_POLL
        while now() < end:
            size = path.stat().st_size
            if size != last:
                say(f"{label} file size {size}")
                last = size
            if size > 12000:
                break
            time.sleep(0.5)
        w.close_stdin()
        end = now() + DRAIN
        while now() < end:
            size = path.stat().st_size
            if size != last:
                say(f"{label} file size {size} (after stdin closed)")
                last = size
            time.sleep(0.5)
        w.finish()
    for i, raw in enumerate(path.read_bytes().splitlines(), 1):
        say(f"{label} file line {i}: {len(raw) + 1} bytes, {w.describe(raw)}")


def main() -> int:
    exe = interpreter()
    if not exe.is_file():
        say(f"no interpreter at {exe}")
        return 1
    env = get_default_environment()
    say(
        f"platform {sys.platform}, probe python {sys.version.split()[0]}, interpreter {exe}"
    )
    say(f"minimal environment keys: {sorted(env)}")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as cwd:
        run_variant("V1 baseline", [str(exe), "-m", "metricmine.server"], env, cwd)
        run_variant("V2 instrumented", [str(exe), "-c", INSTRUMENT], env, cwd)
        variant_file("V3 file", [str(exe), "-m", "metricmine.server"], env, cwd)
        run_variant(
            "V4 small-first",
            [str(exe), "-m", "metricmine.server"],
            env,
            cwd,
            small_first=True,
        )
        run_variant(
            "V5 debug-log",
            [str(exe), "-m", "metricmine.server"],
            {**env, "FASTMCP_LOG_LEVEL": "DEBUG"},
            cwd,
        )
        base = base_interpreter()
        if base is None:
            say("V6 base skipped: no home in pyvenv.cfg")
        else:
            sp = site_packages()
            code = f"import site, runpy; site.addsitedir({str(sp)!r}); runpy.run_module('metricmine.server', run_name='__main__')"
            run_variant("V6 base-interpreter", [str(base), "-c", code], env, cwd)
    say("probe done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
