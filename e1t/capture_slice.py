"""Slice one conversation out of the live shim's capture file (E1T, Claude Desktop).

    uv run python e1t/capture_slice.py begin
    uv run python e1t/capture_slice.py end <transcript-dir>
    uv run python e1t/capture_slice.py count <capture-file>

Claude Desktop keeps one server process per app session for its chat, so
one capture file holds every chat conversation since the last restart.
Desktop 6.28899.6 also opens a second connection to the same entry for
its local agent mode, a second shim with its own file (measured on the
Mac of record on November 27, 2026: the chat's initialize names the
client `claude-ai` and asks for tools, prompts, and resources; the agent
mode's names `local-agent-mode-metricmine-gold` and asks for tools
only). `begin` reads the live shims writing under the capture folder and
takes Desktop's chat: the one whose connection names itself `claude-ai`,
or, when none does, the one that has not initialized yet, so a lone
server that did not start still reaches the key's stop. Exactly one must
qualify. A live shim of another client is watched. A shim with no file
under the folder is never read: one writing elsewhere (another
worktree's, a test's), one still starting before it opens its file, or
one with no capture folder set; a misconfigured entry therefore reads as
no chat shim, a stop. `begin` records the chat's capture file, the
file's current line count, the time, and the watched shims in
e1t/capture/MARK.json, and prints the file and the offset. `end`
refuses, keeps the mark, and writes nothing while any other capture file
in the folder holds a client tool call made since the mark (the agent
mode's, or a chat server Desktop restarted: the record would be split,
which goes to the Architect), and otherwise copies the lines written
since the mark into <transcript-dir>/capture.jsonl, removes the mark,
and prints the message counts: lines, client requests by method, and the
tool calls with their names. `count` prints the same counts for any
capture file. Every printed line is a measurement.

The capture directory is read from MM_E1T_CAPTURE, defaulting to
e1t/capture under the worktree. Nothing here opens a model or a network.
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = HERE / "capture" / "MARK.json"


def capture_dir() -> Path:
    return Path(os.environ.get("MM_E1T_CAPTURE") or (HERE / "capture"))


def rel(path: Path) -> str:
    """A path as the worktree prints it, the same on every machine."""
    try:
        return path.resolve().relative_to(HERE.parent.resolve()).as_posix()
    except ValueError:
        return str(path)


# The interpreter's own path ends in python, python3, python3.12, or
# Python: on a python.org framework build for macOS, bin/python3.12 is a
# launcher that replaces itself with Resources/Python.app/Contents/MacOS/
# Python, with that path as its argv[0], so `ps` shows the capital-P image
# (CPython's Mac/Tools/pythonw.c; measured on the Mac of record on
# November 25, 2026).
SHIM_ARGS = re.compile(r"^\S*[Pp]ython[\d.]*\s+.*e1t/capture_shim\.py(\s|$)")


def live_shim_pids() -> list[int]:
    """The shim processes: an interpreter whose arguments name the shim
    file. A shell whose command line merely mentions the file (this
    command's own, a runbook line) is never counted."""
    out = subprocess.run(["ps", "-axww", "-o", "pid=,args="], capture_output=True, text=True).stdout
    me = os.getpid()
    pids = []
    for row in out.splitlines():
        row = row.strip()
        if not row:
            continue
        pid_text, _, args = row.partition(" ")
        if pid_text.isdigit() and int(pid_text) != me and SHIM_ARGS.match(args.strip()):
            pids.append(int(pid_text))
    return sorted(pids)


def file_for_pid(pid: int) -> Path | None:
    hits = sorted(capture_dir().glob(f"capture-*-{pid}.jsonl"))
    return hits[-1] if hits else None


# Desktop's chat names itself so in its initialize (measured on Desktop
# 6.28899.6, November 27, 2026). Its local agent mode there opens a second
# connection under another name.
CHAT_CLIENT = "claude-ai"


def _message(entry: dict) -> dict | None:
    try:
        msg = json.loads(entry["line"])
    except (ValueError, KeyError, TypeError):
        return None
    return msg if isinstance(msg, dict) else None


def client_of(path: Path | None) -> str | None:
    """The client name in the first initialize a capture file holds, or
    None when it holds none yet."""
    if path is None or not path.is_file():
        return None
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        msg = _message(entry)
        if entry.get("dir") == "client" and msg is not None and msg.get("method") == "initialize":
            info = (msg.get("params") or {}).get("clientInfo") or {}
            return str(info.get("name")) if info.get("name") is not None else ""
    return None


def live_shims() -> list[tuple[int, Path | None, str | None]]:
    """Every live shim writing under this capture folder: its pid, its
    capture file, and its client. A shim with no file here is never
    read: it writes elsewhere (another worktree's, a test's), is still
    starting before it opens its file, or has no capture folder set."""
    out = []
    for pid in live_shim_pids():
        path = file_for_pid(pid)
        if path is not None:
            out.append((pid, path, client_of(path)))
    return out


def chat_candidates(shims: list[tuple[int, Path | None, str | None]]) -> list[int]:
    """The live shims that can be Desktop's chat: those whose connection
    names itself CHAT_CLIENT; when none does, those that have not
    initialized yet, so a lone server that did not start still reaches
    the key's stop. A shim of another client is watched, never sliced,
    and so is a new shim still starting beside a named chat."""
    named = [pid for pid, _, client in shims if client == CHAT_CLIENT]
    return named or [pid for pid, _, client in shims if client is None]


def shims_text(shims: list[tuple[int, Path | None, str | None]]) -> str:
    return ", ".join(f"{pid} {client if client is not None else 'no initialize'}" for pid, _, client in shims) or "none"


def calls_since(path: Path, since: dt.datetime) -> int:
    """The client's tool calls a capture file recorded at or after a time."""
    n = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(raw)
            late = dt.datetime.fromisoformat(entry["t"]) >= since
        except (ValueError, KeyError, TypeError):
            continue
        msg = _message(entry)
        if late and entry.get("dir") == "client" and msg is not None and msg.get("method") == "tools/call":
            n += 1
    return n


def calls_elsewhere(mark: dict) -> list[tuple[str, str | None, int]]:
    """Every other capture file in the folder that holds a client tool
    call made since the mark: its name, its client, and the count. A mark
    written before the time was recorded reads as none."""
    if not mark.get("t"):
        return []
    since = dt.datetime.fromisoformat(mark["t"])
    out = []
    for path in sorted(capture_dir().glob("capture-*.jsonl")):
        if path.resolve() == Path(mark["file"]).resolve():
            continue
        n = calls_since(path, since)
        if n:
            out.append((path.name, client_of(path), n))
    return out


def elsewhere_text(items: list[tuple[str, str | None, int]]) -> str:
    return ", ".join(f"{name} ({client}) {n}" for name, client, n in items)


def counts(lines: list[str]) -> dict:
    methods: collections.Counter[str] = collections.Counter()
    tools: list[str] = []
    results = 0
    for raw in lines:
        try:
            entry = json.loads(raw)
            msg = json.loads(entry["line"])
        except (ValueError, KeyError):
            continue
        if entry.get("dir") == "client" and isinstance(msg, dict) and "method" in msg:
            methods[msg["method"]] += 1
            if msg["method"] == "tools/call":
                tools.append(str((msg.get("params") or {}).get("name")))
        if entry.get("dir") == "server" and isinstance(msg, dict) and "result" in msg:
            results += 1
    return {"lines": len(lines), "client_methods": dict(sorted(methods.items())), "tools_call": len(tools), "tools": tools, "server_results": results}


def print_counts(c: dict) -> None:
    print(f"lines: {c['lines']}")
    print(f"client methods: {c['client_methods']}")
    print(f"tools/call: {c['tools_call']} {c['tools']}")
    print(f"server results: {c['server_results']}")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "count":
        lines = Path(argv[1]).read_text(encoding="utf-8").splitlines()
        print_counts(counts(lines))
        return 0
    if cmd == "begin":
        shims = live_shims()
        pids = chat_candidates(shims)
        if len(pids) != 1:
            print(f"SLICE-STOP: {len(pids)} live shim process(es) {pids} for Desktop's chat; exactly one is expected (its connection names itself {CHAT_CLIENT!r}); live shims: {shims_text(shims)}")
            return 1
        path = file_for_pid(pids[0])
        if path is None:
            print(f"SLICE-STOP: no capture file for shim pid {pids[0]} under {rel(capture_dir())}")
            return 1
        offset = len(path.read_text(encoding="utf-8").splitlines())
        watched = [{"pid": pid, "client": client} for pid, _, client in shims if pid != pids[0]]
        at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")
        MARK.parent.mkdir(parents=True, exist_ok=True)
        MARK.write_text(json.dumps({"file": str(path), "offset": offset, "pid": pids[0], "client": client_of(path), "t": at, "watched": watched}) + "\n", encoding="utf-8")
        print(f"MARK {path.name} at line {offset} (shim pid {pids[0]})")
        return 0
    if cmd == "end":
        if not MARK.exists():
            print("SLICE-STOP: no mark; run `begin` before the conversation")
            return 1
        mark = json.loads(MARK.read_text(encoding="utf-8"))
        elsewhere = calls_elsewhere(mark)
        if elsewhere:
            print(f"SLICE-STOP: tool call(s) since the mark reached another connection: {elsewhere_text(elsewhere)}; nothing was sliced and the mark stands")
            return 1
        dest = Path(argv[1])
        dest.mkdir(parents=True, exist_ok=True)
        lines = Path(mark["file"]).read_text(encoding="utf-8").splitlines()[mark["offset"] :]
        (dest / "capture.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        MARK.unlink()
        print(f"SLICED {len(lines)} lines from {Path(mark['file']).name} line {mark['offset']} into {rel(dest / 'capture.jsonl')}")
        print_counts(counts(lines))
        return 0
    print(f"unknown command {cmd!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
