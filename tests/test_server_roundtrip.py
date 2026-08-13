"""Local-lane round trip against the real server over stdio.

Marked `local`: needs the gitignored warehouse that `make ingest` and
`dbt build` produce, so CI deselects it with -m "not local". The server is
spawned as a subprocess exactly the way a desktop client spawns it —
`python -m metricmine.server`, configured entirely through MM_SERVE_DB.

The working directory is a temp directory, never the repo. Spec §5 resolves
the demo artifact off the module's own location precisely because a client's
working directory is not the repo root, and launching from the repo is the
one condition under which a CWD dependency would stay invisible.

Every asserted shape was measured against this server before it was written
down, including the one asymmetry: the query tool returns a union, which the
SDK wraps under a `result` key, while the four single-shape tools are not
wrapped. Same async rule as the surface tests — anyio.run inside synchronous
tests, no pytest plugin.
"""

import os
import sys
import tempfile
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_WAREHOUSE = Path(__file__).resolve().parents[1] / "warehouse" / "metricmine.duckdb"

DIMENSIONS_KEY = "2d27bd360b5092ff22047c65407ff05699afad98f455de2409665a5950a05e82"
FACT_ROWS = 44721

pytestmark = pytest.mark.local


async def _walk(cwd: str) -> dict:
    """One session, one spawn: collect everything the assertions need."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "metricmine.server"],
        env={**os.environ, "MM_SERVE_DB": str(_WAREHOUSE)},
        cwd=cwd,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            collected = {"init": await session.initialize()}
            collected["tools"] = (await session.list_tools()).tools
            collected["count"] = await session.call_tool(
                "query",
                {"sql": "SELECT count(*) AS n FROM gold.fact_invoice_lines_values"},
            )
            collected["refusal"] = await session.call_tool(
                "query", {"sql": "DELETE FROM gold.context_registry"}
            )
            collected["schema"] = await session.call_tool(
                "get_schema", {"schema_key": DIMENSIONS_KEY}
            )
            collected["lookup"] = await session.call_tool(
                "lookup_record", {"content_key": DIMENSIONS_KEY}
            )
            # A gated statement that cannot execute, then a normal call: the
            # non-catch is only acceptable if the session survives it.
            collected["typo"] = await session.call_tool(
                "query", {"sql": "SELECT * FROM gold.typo"}
            )
            collected["after_error"] = await session.call_tool(
                "list_fact_categories", {}
            )
            return collected


@pytest.fixture(scope="module")
def wire():
    if not _WAREHOUSE.is_file():
        pytest.skip(f"warehouse not built at {_WAREHOUSE}; run `make ingest` first")
    with tempfile.TemporaryDirectory() as cwd:
        return anyio.run(_walk, cwd)


def test_initialize_reports_the_spec_server_name(wire):
    assert wire["init"].serverInfo.name == "metricmine-gold"


def test_discovery_lists_the_five_tools(wire):
    assert len(wire["tools"]) == 5


def test_count_query_returns_structured_rows(wire):
    # Measured: the query tool's union return arrives wrapped under `result`.
    result = wire["count"].structuredContent["result"]
    assert result["rows"] == [[FACT_ROWS]]
    assert result["truncated"] is False


def test_a_refused_statement_is_a_normal_answer(wire):
    refusal = wire["refusal"]
    assert refusal.isError is False
    result = refusal.structuredContent["result"]
    assert result["refused"] is True
    assert "DELETE" in result["reason"]


def test_get_schema_returns_its_shape_unwrapped(wire):
    # Measured: single-TypedDict returns are not wrapped, unlike the union.
    schema = wire["schema"].structuredContent
    assert schema["found"] is True
    assert schema["role"] == "dimensions"


def test_lookup_record_routes_a_schema_key_to_the_registry(wire):
    lookup = wire["lookup"].structuredContent
    assert lookup["found"] is True
    assert [(hit["table"], hit["column"]) for hit in lookup["hits"]] == [
        ("context_registry", "schema_key")
    ]


def test_an_unexecutable_select_is_deliberately_not_caught(wire):
    # A statement that passes the gate and then fails to run is a mistake in
    # the SQL, not a policy decision, so it surfaces as a protocol error
    # carrying DuckDB's own diagnostic — not as a refusal. Pinned here
    # because it is a decision, and decisions that look like oversights get
    # "fixed" by the next contributor.
    typo = wire["typo"]
    assert typo.isError is True
    assert typo.structuredContent is None
    assert "typo" in typo.content[0].text


def test_the_session_survives_an_execution_error(wire):
    categories = wire["after_error"].structuredContent["categories"]
    assert categories[0]["row_count"] == FACT_ROWS
