"""The Claude Desktop switch (E1T): point Desktop's one server entry at the
branch's server through the capture shim, and prove the line it wrote.

    uv run python e1t/desktop_switch.py backup  [--config <path>]
    uv run python e1t/desktop_switch.py set --worktree <dir> --served <file> [--config <path>]
    uv run python e1t/desktop_switch.py check   [--config <path>]
    uv run python e1t/desktop_switch.py restore [--config <path>]

Desktop's config holds one server, `metricmine-gold`. This command edits
that one entry and nothing else (HW-03's rules: a backup first, merge and
never replace, never print another entry's values, prove by spawning the
line it wrote). `backup` copies the config once to e1t/local/ (gitignored)
and refuses to overwrite a backup. `set` points the entry at the capture
shim in the branch's worktree with the worktree's own interpreter, and
names the pinned served file (MM_SERVE_DB) and the capture directory
(MM_E1T_CAPTURE). `check` spawns the exact configured launch line
(command, args, env) from a temporary directory with the SDK's minimal
environment, the way Desktop does, and prints the instructions' sha256
and length against the key, the served file's sha256 against the key,
and the tool count against the key. `restore` writes the backup back and
proves it by sha256. A full Desktop restart follows every `set`; this
command cannot do that and says so.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from key import INSTRUCTIONS_LENGTH, INSTRUCTIONS_SHA256, SERVED_SHA256, SERVER_NAME, TOOL_COUNT  # noqa: E402

ENTRY = SERVER_NAME
DEFAULT_CONFIG = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
BACKUP = HERE / "local" / "claude_desktop_config.backup.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(config: Path) -> dict:
    return json.loads(config.read_text(encoding="utf-8"))


def cmd_backup(config: Path) -> int:
    if BACKUP.exists():
        print(f"BACKUP-EXISTS {sha256_file(BACKUP)} ({BACKUP.stat().st_size} bytes); not overwritten")
        return 0
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config, BACKUP)
    print(f"BACKUP-OK {sha256_file(BACKUP)} ({BACKUP.stat().st_size} bytes)")
    return 0


def entry_for(worktree: Path, served: Path) -> dict:
    # Absolute paths, symlinks kept: the venv's `python` is a symlink to the
    # interpreter, and resolving it would name the system interpreter with no
    # venv (measured in Prep D's tests).
    return {
        "command": os.path.abspath(worktree / ".venv" / "bin" / "python"),
        "args": [os.path.abspath(worktree / "e1t" / "capture_shim.py")],
        "env": {
            "MM_SERVE_DB": os.path.abspath(served),
            "MM_E1T_CAPTURE": os.path.abspath(worktree / "e1t" / "capture"),
        },
    }


def cmd_set(config: Path, worktree: Path, served: Path) -> int:
    if not BACKUP.exists():
        print("SWITCH-STOP no backup; run `backup` first")
        return 1
    data = load(config)
    servers = data.get("mcpServers")
    if not isinstance(servers, dict) or ENTRY not in servers:
        print(f"SWITCH-STOP the config has no {ENTRY!r} entry")
        return 1
    others_before = {k: json.dumps(v, sort_keys=True) for k, v in servers.items() if k != ENTRY}
    servers[ENTRY] = entry_for(worktree, served)
    config.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    after = load(config)["mcpServers"]
    unchanged = sum(1 for k, v in others_before.items() if json.dumps(after.get(k), sort_keys=True) == v)
    print(f"SWITCH-OK entry={ENTRY} other-entries={len(others_before)} unchanged={unchanged}")
    print("RESTART-DESKTOP: quit Claude Desktop fully and open it again; only a restart runs the new entry")
    return 0


async def spawn_check(entry: dict) -> tuple[str, int, int, list[str]]:
    import mcp.types as T
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, get_default_environment, stdio_client

    env = dict(get_default_environment())
    env.update(entry.get("env") or {})
    params = StdioServerParameters(command=entry["command"], args=list(entry.get("args") or []), env=env, cwd=tempfile.gettempdir())
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w, client_info=T.Implementation(name="e1t-switch-check", version="1")) as s:
            init = await s.initialize()
            tools = (await s.list_tools()).tools
            instr = init.instructions or ""
            return hashlib.sha256(instr.encode()).hexdigest(), len(instr), len(tools), [t.name for t in tools]


def cmd_check(config: Path) -> int:
    entry = load(config)["mcpServers"].get(ENTRY)
    if not entry:
        print(f"CHECK-STOP the config has no {ENTRY!r} entry")
        return 1
    env = entry.get("env") or {}
    served = env.get("MM_SERVE_DB", "")
    served_sha = sha256_file(Path(served)) if served and Path(served).is_file() else "missing"
    digest, length, count, names = asyncio.run(spawn_check(entry))
    ok_instr = digest == INSTRUCTIONS_SHA256 and length == INSTRUCTIONS_LENGTH
    ok_served = served_sha == SERVED_SHA256
    ok_tools = count == TOOL_COUNT and "prepare_feedback" in names
    print(f"instructions sha256 {digest} ({length} characters) {'MATCH' if ok_instr else 'MISMATCH'} against the key")
    print(f"served sha256 {served_sha} {'MATCH' if ok_served else 'MISMATCH'} against the key")
    print(f"tools {count} {' '.join(names)} {'MATCH' if ok_tools else 'MISMATCH'} against the key")
    print("CHECK-OK" if ok_instr and ok_served and ok_tools else "CHECK-STOP")
    return 0 if ok_instr and ok_served and ok_tools else 1


def cmd_restore(config: Path) -> int:
    if not BACKUP.exists():
        print("RESTORE-STOP no backup to restore")
        return 1
    shutil.copyfile(BACKUP, config)
    a, b = sha256_file(config), sha256_file(BACKUP)
    print(f"RESTORED {a}")
    print("RESTORE-MATCH" if a == b else "RESTORE-MISMATCH")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["backup", "set", "check", "restore"])
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--worktree")
    ap.add_argument("--served")
    a = ap.parse_args(argv)
    config = Path(os.path.expanduser(a.config))
    if a.command == "backup":
        return cmd_backup(config)
    if a.command == "set":
        if not (a.worktree and a.served):
            print("SWITCH-STOP set needs --worktree and --served")
            return 2
        return cmd_set(config, Path(a.worktree), Path(a.served))
    if a.command == "check":
        return cmd_check(config)
    return cmd_restore(config)


if __name__ == "__main__":
    sys.exit(main())
