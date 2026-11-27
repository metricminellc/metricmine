"""Slice one conversation out of the live shim's capture file (E1T, Claude Desktop).

    uv run python e1t/capture_slice.py begin
    uv run python e1t/capture_slice.py end <transcript-dir>
    uv run python e1t/capture_slice.py count <capture-file>

Claude Desktop keeps its server processes for an app session, so one
capture file holds every conversation a connection carried since the
last restart. Desktop 6.28899.6 opens two connections to the one config
entry, two shims with their own files: one whose initialize names the
client `claude-ai` and asks for tools, prompts, and resources, and one
named `local-agent-mode-metricmine-gold` that asks for tools only. The
smoke's one tool call reached the second (both measured on the Mac of
record on November 27, 2026, the second at the Desktop smoke). So the slice
follows the calls. `begin` marks every live shim writing under the
capture folder: each one's file and current line count, with the time,
in e1t/capture/MARK.json, and prints the first file (the `claude-ai` one
when there is one) and its offset. The conversation's connection is the
one whose file holds the client's tool calls since its mark; when none
does, the first. It is a stop, with nothing written and the mark kept,
when the calls since the mark reached more than one connection, or
reached a connection that started after the mark (a server Desktop
restarted: the record would be split), which goes to the Architect. A
shim with no file under the folder is never read: one writing elsewhere
(another worktree's, a test's), one still starting before it opens its
file, or one with no capture folder set; a misconfigured entry therefore
reads as no live shim, a stop. `end` copies the conversation
connection's lines since its mark into <transcript-dir>/capture.jsonl,
removes the mark, and prints the file and the offset it sliced from and
the message counts: lines, client requests by method, the tool calls
with their names, and the server's results. `count` prints the same counts for any capture file. A
mark written by the previous form of `begin` (one file, the others named
under `watched`) is read with the others' offsets taken at the mark's
time. Every printed line is a measurement.

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


# One of Desktop 6.28899.6's two connections names itself so in its
# initialize (measured November 27, 2026); its mark is the one printed.
# The name says nothing about where the calls go: the smoke's went to the
# other connection.
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


def shims_text(shims: list[tuple[int, Path | None, str | None]]) -> str:
    return ", ".join(f"{pid} {client if client is not None else 'no initialize'}" for pid, _, client in shims) or "none"


def _time(entry: dict) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(entry["t"])
    except (ValueError, KeyError, TypeError):
        return None


def offset_at(path: Path, since: dt.datetime) -> int:
    """The number of a capture file's leading lines stamped before a time.
    The shim stamps a line before it takes the write lock, so a client
    line and a server line can land out of stamp order within a moment;
    at a mark taken while the connection is idle that cannot move the
    count. Only a mark of the previous form is read this way."""
    n = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            at = _time(json.loads(raw))
        except ValueError:
            at = None
        if at is not None and at >= since:
            break
        n += 1
    return n


def calls_in(lines: list[str]) -> int:
    """The client's tool calls among capture lines."""
    n = 0
    for raw in lines:
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        msg = _message(entry)
        if entry.get("dir") == "client" and msg is not None and msg.get("method") == "tools/call":
            n += 1
    return n


def calls_since(path: Path, since: dt.datetime) -> int:
    """The client's tool calls a capture file recorded at or after a time."""
    late = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            at = _time(json.loads(raw))
        except ValueError:
            continue
        if at is not None and at >= since:
            late.append(raw)
    return calls_in(late)


def marked_shims(mark: dict) -> list[dict]:
    """The shims a mark recorded, each with its pid, file, offset, and
    client, the printed one first. A mark from the previous form of
    `begin` names one file and lists the others under `watched`; their
    offsets are taken at the mark's time."""
    if "shims" in mark:
        return list(mark["shims"])
    out = [{"pid": mark.get("pid"), "file": mark["file"], "offset": mark["offset"], "client": mark.get("client")}]
    if mark.get("t"):
        since = dt.datetime.fromisoformat(mark["t"])
        for w in mark.get("watched", []):
            path = file_for_pid(w["pid"])
            if path is not None:
                out.append({"pid": w["pid"], "file": str(path), "offset": offset_at(path, since), "client": w.get("client")})
    return out


def since_mark(shim: dict) -> list[str]:
    return Path(shim["file"]).read_text(encoding="utf-8").splitlines()[shim["offset"] :]


def conversation(mark: dict) -> tuple[dict | None, str]:
    """The marked shim that carried the conversation: the one whose file
    holds the client's tool calls since its mark, or, when none does, the
    first. (None, the reason) when the calls reached more than one
    connection, or a connection that started after the mark."""
    shims = marked_shims(mark)
    marked_files = {Path(s["file"]).resolve() for s in shims}
    if mark.get("t"):
        since = dt.datetime.fromisoformat(mark["t"])
        late = [(p.name, client_of(p), n) for p in sorted(capture_dir().glob("capture-*.jsonl")) if p.resolve() not in marked_files and (n := calls_since(p, since))]
        if late:
            return None, "tool call(s) since the mark reached a connection that started after it: " + ", ".join(f"{name} ({client}) {n}" for name, client, n in late)
    carried = [(s, n) for s in shims if (n := calls_in(since_mark(s)))]
    if len(carried) > 1:
        return None, "tool calls since the mark reached more than one connection: " + ", ".join(f"{Path(s['file']).name} ({s.get('client')}) {n}" for s, n in carried)
    return (carried[0][0] if carried else shims[0]), ""


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
        if not shims:
            print(f"SLICE-STOP: 0 live shim process(es) writing under {rel(capture_dir())}; Desktop's must be running")
            return 1
        shims.sort(key=lambda s: (s[2] != CHAT_CLIENT, s[0]))
        at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")
        marked = [{"pid": pid, "file": str(path), "offset": len(path.read_text(encoding="utf-8").splitlines()), "client": client} for pid, path, client in shims]
        first = marked[0]
        MARK.parent.mkdir(parents=True, exist_ok=True)
        MARK.write_text(json.dumps({"t": at, "shims": marked, "file": first["file"], "offset": first["offset"], "pid": first["pid"], "client": first["client"]}) + "\n", encoding="utf-8")
        print(f"MARK {Path(first['file']).name} at line {first['offset']} (shim pid {first['pid']})")
        return 0
    if cmd == "end":
        if not MARK.exists():
            print("SLICE-STOP: no mark; run `begin` before the conversation")
            return 1
        mark = json.loads(MARK.read_text(encoding="utf-8"))
        shim, why = conversation(mark)
        if shim is None:
            print(f"SLICE-STOP: {why}; nothing was sliced and the mark stands")
            return 1
        dest = Path(argv[1])
        dest.mkdir(parents=True, exist_ok=True)
        lines = since_mark(shim)
        (dest / "capture.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        MARK.unlink()
        print(f"SLICED {len(lines)} lines from {Path(shim['file']).name} line {shim['offset']} into {rel(dest / 'capture.jsonl')}")
        print_counts(counts(lines))
        return 0
    print(f"unknown command {cmd!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
