"""Prove the command the desktop config launches answers over stdio.

docs/demo.md tells a reader to point Claude Desktop at the clone's own
interpreter with `-m metricmine.server`: `.venv/bin/python` on macOS and
Linux, `.venv\\Scripts\\python.exe` on Windows (D-42). This script spawns
exactly that command the way a desktop client does: from a directory that
is not the repository, with the mcp SDK's minimal default environment (the
kind a desktop app passes) and MM_SERVE_DB unset, so the served database
is the fetched or built `demo/demo.duckdb` by default (serving spec §5).
It speaks the wire protocol itself, newline-delimited JSON-RPC over the
child's pipes: `initialize`, the `initialized` notification, `tools/list`,
then `tools/call` on `list_fact_categories`. Keyless; no network.

    uv run python scripts/serve_smoke.py

Every wait is bounded and every answer prints as it arrives, with its size
and its latency, so a machine that stops answering names the step that
stopped within a minute instead of hanging. Cycle one of the Windows check
hung at this step for the job's whole hour with nothing printed: the
server had dispatched the tool call within three seconds, the SDK's
asyncio pipe client never returned, and the first answer larger than 8 KB
is where it stopped (F-56). The client here is plain blocking reads on a
thread, the way a desktop app reads a server, and the mcp package supplies
only the minimal environment and the protocol version. After the answers,
stdin closes and the server's exit is measured and reported; a server
that ignores end-of-file is terminated and the line says so.

Exit 0 when the server names itself `metricmine-gold`, offers exactly five
tools, and lists exactly three categories; 1 otherwise, naming the miss.
The Windows CI job runs it after `demo-fetch`. What it proves is the
command, not the desktop: the click-through in Claude Desktop is the one
step no runner can measure (F-55), and the demo guide says so.
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
SERVER_NAME = "metricmine-gold"
TOOL_COUNT = 5
CATEGORY_COUNT = 3
TOOL = "list_fact_categories"
# Seconds a single answer may take. Cycle one of the Windows check saw
# every earlier step answer in under a second; a minute is the ceiling
# before the step is called hung and named.
REQUEST_TIMEOUT = 60.0
# Seconds the server gets to exit on its own after stdin closes, then the
# same again after terminate before kill.
SHUTDOWN_TIMEOUT = 5.0


def interpreter(repo: Path = REPO, windows: bool | None = None) -> Path:
    """The venv interpreter the demo guide tells the reader to configure."""
    if windows is None:
        windows = sys.platform == "win32"
    if windows:
        return repo / ".venv" / "Scripts" / "python.exe"
    return repo / ".venv" / "bin" / "python"


class SmokeFailure(Exception):
    """A step that did not answer as a server must; the message names it."""


def say(line: str) -> None:
    print(line, flush=True)


class Client:
    """Newline-delimited JSON-RPC over a child's pipes.

    One thread blocks on the child's stdout and hands each line to a queue;
    every request waits on that queue with a deadline. Nothing here is
    asynchronous, and nothing depends on how the platform's event loop
    reads a pipe.
    """

    def __init__(self, proc: subprocess.Popen[bytes]) -> None:
        self.proc = proc
        self.lines: queue.Queue[bytes | None] = queue.Queue()
        self.skipped = 0
        self._next_id = 0
        threading.Thread(target=self._read, name="server-stdout", daemon=True).start()

    def _read(self) -> None:
        assert self.proc.stdout is not None
        try:
            for raw in self.proc.stdout:
                self.lines.put(raw)
        finally:
            self.lines.put(None)

    def _send(self, message: dict) -> None:
        assert self.proc.stdin is not None
        data = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
        self.proc.stdin.write(data)
        self.proc.stdin.flush()

    def notify(self, method: str, params: dict | None = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def request(
        self, method: str, params: dict | None = None
    ) -> tuple[dict, int, float]:
        """Send a request; return (result, answer bytes, seconds) or raise."""
        self._next_id += 1
        rid = self._next_id
        started = time.monotonic()
        self._send(
            {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
        )
        deadline = started + REQUEST_TIMEOUT
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SmokeFailure(
                    f"{method} timed out after {REQUEST_TIMEOUT:g} s with no answer"
                )
            try:
                raw = self.lines.get(timeout=remaining)
            except queue.Empty:
                raise SmokeFailure(
                    f"{method} timed out after {REQUEST_TIMEOUT:g} s with no answer"
                ) from None
            if raw is None:
                code = self.proc.poll()
                raise SmokeFailure(
                    f"{method}: the server closed stdout before answering (exit code {code})"
                )
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                raise SmokeFailure(
                    f"{method}: a stdout line is not JSON-RPC: {line[:80]!r}"
                ) from None
            if message.get("id") != rid:
                # A notification or a server-initiated request; not this answer.
                self.skipped += 1
                continue
            if "error" in message:
                raise SmokeFailure(
                    f"{method}: error {json.dumps(message['error'])[:200]}"
                )
            return message["result"], len(raw), time.monotonic() - started


def shutdown(proc: subprocess.Popen[bytes]) -> str:
    """Close stdin, measure the exit; terminate then kill a server that stays."""
    started = time.monotonic()
    if proc.stdin is not None:
        try:
            proc.stdin.close()
        except OSError:
            pass
    try:
        code = proc.wait(timeout=SHUTDOWN_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            code = proc.wait(timeout=SHUTDOWN_TIMEOUT)
            how = "terminated"
        except subprocess.TimeoutExpired:
            proc.kill()
            code = proc.wait()
            how = "killed"
        return (
            f"shutdown: {how} after {time.monotonic() - started:.1f} s"
            f" (the server did not exit on stdin end-of-file); exit code {code}"
        )
    return f"shutdown: the server exited {code} in {time.monotonic() - started:.1f} s after stdin closed"


def walk(command: Path, cwd: str) -> dict:
    """Launch the server the way a desktop client does and walk the three answers."""
    proc = subprocess.Popen(
        [str(command), "-m", "metricmine.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        # stderr stays the parent's: the server's log lines belong beside these.
        stderr=None,
        cwd=cwd,
        # The SDK's minimal environment, the kind a desktop app passes;
        # MM_SERVE_DB is not in it, so the default demo artifact is what
        # gets proven.
        env=get_default_environment(),
    )
    found: dict = {"server": None, "tools": None, "categories": None}
    client = Client(proc)
    try:
        init, size, took = client.request(
            "initialize",
            {
                "protocolVersion": LATEST_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "metricmine-serve-smoke", "version": "2"},
            },
        )
        client.notify("notifications/initialized")
        info = init.get("serverInfo", {})
        found["server"] = info.get("name")
        say(
            f"initialize: {info.get('name')} {info.get('version', '')}".rstrip()
            + f", protocol {init.get('protocolVersion')}, {size} bytes, {took * 1000:.0f} ms"
        )
        listing, size, took = client.request("tools/list")
        found["tools"] = [tool["name"] for tool in listing.get("tools", [])]
        say(
            f"tools/list: {len(found['tools'])} tools, {size} bytes, {took * 1000:.0f} ms"
        )
        call, size, took = client.request("tools/call", {"name": TOOL, "arguments": {}})
        if call.get("isError"):
            text = " ".join(c.get("text", "") for c in call.get("content", []))[:200]
            raise SmokeFailure(
                f"tools/call {TOOL}: the server answered isError: {text}"
            )
        found["categories"] = call["structuredContent"]["categories"]
        say(
            f"tools/call {TOOL}: {len(found['categories'])} categories,"
            f" {size} bytes, {took * 1000:.0f} ms"
        )
        if client.skipped:
            say(f"skipped: {client.skipped} other message(s) on stdout")
    except SmokeFailure as exc:
        found["failure"] = str(exc)
    finally:
        say(shutdown(proc))
    return found


def main() -> int:
    command = interpreter()
    if not command.is_file():
        say(f"FAIL no interpreter at {command}; run uv sync first")
        return 1
    say(f"command: {command} -m metricmine.server")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as cwd:
        found = walk(command, cwd)
    problems = []
    if found.get("failure"):
        problems.append(found["failure"])
    if found["server"] is not None and found["server"] != SERVER_NAME:
        problems.append(f"server name {found['server']!r}, expected {SERVER_NAME!r}")
    if found["tools"] is not None:
        say(f"server: {found['server']}, {len(found['tools'])} tools")
        if len(found["tools"]) != TOOL_COUNT:
            problems.append(
                f"{len(found['tools'])} tools, expected {TOOL_COUNT}: {found['tools']}"
            )
    if found["categories"] is not None:
        say(
            "categories: "
            + ", ".join(
                f"{c['category']} {c['row_count']}" for c in found["categories"]
            )
        )
        if len(found["categories"]) != CATEGORY_COUNT:
            problems.append(
                f"{len(found['categories'])} categories, expected {CATEGORY_COUNT}"
            )
    for problem in problems:
        say(f"FAIL {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
