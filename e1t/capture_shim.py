"""The capture shim (E1T): a measuring instrument, never a tool.

Claude Desktop's config entry launches this file with the worktree's own
interpreter. The shim starts the unchanged server, `python -m
metricmine.server`, with the same interpreter, the same environment, and
the same working directory, and passes every byte between Desktop and the
server unaltered in both directions: Desktop's stdin to the server's
stdin, the server's stdout to Desktop's stdout. Stderr is the server's
own, inherited, so Desktop's log keeps what it kept before. Beside that,
each newline-delimited message is appended, with its direction and the
UTC time it passed, to a capture file in the directory MM_E1T_CAPTURE
names (one file per shim process, named by its start time and pid).
Claude Code launches one server per conversation, so one capture file
is one conversation there; Claude Desktop keeps one server per app
session, and e1t/capture_slice.py cuts a conversation out of its file.
Nothing is printed by the shim itself: stdout carries JSON-RPC.

Why it exists: Desktop's own MCP log records each message by method and
id and never its payload (measured October 21, 2026), so a tool call's
arguments and raw result have no record of their own without this.

The server's code is the branch's: main's five tools and the experiment's
sixth. The pass-through is proven byte for byte by
e1t/tests/test_shim_and_switch.py and by each sitting's smoke conversation.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

CAPTURE_ENV_VAR = "MM_E1T_CAPTURE"


def capture_path() -> Path | None:
    root = os.environ.get(CAPTURE_ENV_VAR)
    if not root:
        return None
    folder = Path(root)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return folder / f"capture-{stamp}-{os.getpid()}.jsonl"


def record(handle, lock: threading.Lock, direction: str, line: bytes) -> None:
    if handle is None:
        return
    entry = {
        "t": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"),
        "dir": direction,
        "line": line.decode("utf-8", errors="surrogateescape").rstrip("\r\n"),
    }
    with lock:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        handle.flush()


def pump(src, dst, direction: str, handle, lock: threading.Lock) -> None:
    """Record each line, then forward it to dst unaltered: the capture never
    trails the client (a reader of the capture after the client has the
    response finds the response there)."""
    try:
        for line in iter(src.readline, b""):
            record(handle, lock, direction, line)
            dst.write(line)
            dst.flush()
    except (BrokenPipeError, ValueError, OSError):
        pass
    finally:
        try:
            dst.close()
        except (OSError, ValueError):
            pass


def main() -> int:
    path = capture_path()
    handle = open(path, "a", encoding="utf-8") if path else None
    lock = threading.Lock()
    child = subprocess.Popen(
        [sys.executable, "-m", "metricmine.server", *sys.argv[1:]],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,  # the server's stderr stays Desktop's log line for line
        env=os.environ.copy(),
    )
    assert child.stdin is not None and child.stdout is not None
    up = threading.Thread(target=pump, args=(sys.stdin.buffer, child.stdin, "client", handle, lock), daemon=True)
    down = threading.Thread(target=pump, args=(child.stdout, sys.stdout.buffer, "server", handle, lock), daemon=True)
    up.start()
    down.start()
    code = child.wait()
    down.join(timeout=5)
    if handle is not None:
        with lock:
            handle.write(json.dumps({"t": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"), "dir": "shim", "line": f"server exited {code}"}) + "\n")
            handle.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
