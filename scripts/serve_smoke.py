"""Prove the command the desktop config launches answers over stdio.

docs/demo.md tells a reader to point Claude Desktop at the clone's own
interpreter with `-m metricmine.server`: `.venv/bin/python` on macOS and
Linux, `.venv\\Scripts\\python.exe` on Windows (D-42). This script spawns
exactly that command the way a desktop client does: from a directory that
is not the repository, with the mcp SDK's minimal default environment (the
kind a desktop app passes) and MM_SERVE_DB unset, so the served database
is the fetched or built `demo/demo.duckdb` by default (serving spec §5).
It initializes a session, lists the tools, calls `list_fact_categories`,
and prints what it found. Keyless; no network.

    uv run python scripts/serve_smoke.py

Exit 0 when the server names itself `metricmine-gold`, offers exactly five
tools, and lists exactly three categories; 1 otherwise, naming the miss.
The Windows CI job runs it after `demo-fetch`. What it proves is the
command, not the desktop: the click-through in Claude Desktop is the one
step no runner can measure (F-55), and the demo guide says so.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parents[1]
SERVER_NAME = "metricmine-gold"
TOOL_COUNT = 5
CATEGORY_COUNT = 3


def interpreter(repo: Path = REPO, windows: bool | None = None) -> Path:
    """The venv interpreter the demo guide tells the reader to configure."""
    if windows is None:
        windows = sys.platform == "win32"
    if windows:
        return repo / ".venv" / "Scripts" / "python.exe"
    return repo / ".venv" / "bin" / "python"


async def _walk(command: Path, cwd: str) -> dict:
    params = StdioServerParameters(
        command=str(command),
        args=["-m", "metricmine.server"],
        # env=None: the SDK's default environment, the minimal set a
        # desktop client inherits; MM_SERVE_DB is not in it, so the
        # default demo artifact is what gets proven.
        env=None,
        cwd=cwd,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            tools = (await session.list_tools()).tools
            listing = await session.call_tool("list_fact_categories", {})
            return {
                "server": init.serverInfo.name,
                "tools": [tool.name for tool in tools],
                "categories": listing.structuredContent["categories"],
            }


def main() -> int:
    command = interpreter()
    if not command.is_file():
        print(f"FAIL no interpreter at {command}; run uv sync first")
        return 1
    with tempfile.TemporaryDirectory() as cwd:
        found = anyio.run(_walk, command, cwd)
    problems = []
    if found["server"] != SERVER_NAME:
        problems.append(f"server name {found['server']!r}, expected {SERVER_NAME!r}")
    if len(found["tools"]) != TOOL_COUNT:
        problems.append(f"{len(found['tools'])} tools, expected {TOOL_COUNT}: {found['tools']}")
    if len(found["categories"]) != CATEGORY_COUNT:
        problems.append(f"{len(found['categories'])} categories, expected {CATEGORY_COUNT}")
    print(f"command: {command} -m metricmine.server")
    print(f"server: {found['server']}, {len(found['tools'])} tools")
    print(
        "categories: "
        + ", ".join(f"{c['category']} {c['row_count']}" for c in found["categories"])
    )
    for problem in problems:
        print(f"FAIL {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
