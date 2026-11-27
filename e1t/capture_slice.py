"""Slice one conversation out of the live shim's capture file (E1T, Claude Desktop).

    uv run python e1t/capture_slice.py begin
    uv run python e1t/capture_slice.py end <transcript-dir>
    uv run python e1t/capture_slice.py count <capture-file>

Claude Desktop keeps one server process per app session, so one capture
file holds every conversation since the last restart. `begin` finds the
live shim process (exactly one `e1t/capture_shim.py` process must be
running, the one Desktop launched), records its capture file and the
file's current line count in e1t/capture/MARK.json, and prints the file
and the offset. `end` copies the lines written since the mark into
<transcript-dir>/capture.jsonl, removes the mark, and prints the
message counts: lines, client requests by method, and the tool calls
with their names. `count` prints the same counts for any capture file.
Every printed line is a measurement.

The capture directory is read from MM_E1T_CAPTURE, defaulting to
e1t/capture under the worktree. Nothing here opens a model or a network.
"""

from __future__ import annotations

import collections
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
        pids = live_shim_pids()
        if len(pids) != 1:
            print(f"SLICE-STOP: {len(pids)} live shim process(es) {pids}; exactly one is expected (Desktop's)")
            return 1
        path = file_for_pid(pids[0])
        if path is None:
            print(f"SLICE-STOP: no capture file for shim pid {pids[0]} under {rel(capture_dir())}")
            return 1
        offset = len(path.read_text(encoding="utf-8").splitlines())
        MARK.parent.mkdir(parents=True, exist_ok=True)
        MARK.write_text(json.dumps({"file": str(path), "offset": offset, "pid": pids[0]}) + "\n", encoding="utf-8")
        print(f"MARK {path.name} at line {offset} (shim pid {pids[0]})")
        return 0
    if cmd == "end":
        if not MARK.exists():
            print("SLICE-STOP: no mark; run `begin` before the conversation")
            return 1
        mark = json.loads(MARK.read_text(encoding="utf-8"))
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
