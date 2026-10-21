"""Local-lane round trip against the real server over stdio.

Marked `local`: needs the gitignored warehouse that `make ingest` and
`dbt build` produce, so CI deselects it with -m "not local". The server is
spawned as a subprocess exactly the way a desktop client spawns it;
`python -m metricmine.server`, configured entirely through MM_SERVE_DB.

The working directory is a temp directory, never the repo. Spec §5 resolves
the demo artifact off the module's own location precisely because a client's
working directory is not the repo root, and launching from the repo is the
one condition under which a CWD dependency would stay invisible.

Every asserted shape was measured against this server before it was written
down, including the one asymmetry: the query tool returns a union, which the
SDK wraps under a `result` key, while the four single-shape tools are not
wrapped. Same async rule as the surface tests: anyio.run inside synchronous
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
            # The scope gate at the wire (Amendment AB): the working warehouse
            # holds silver, and the default scope refuses it as an answer.
            collected["silver_refused"] = await session.call_tool(
                "query", {"sql": "SELECT count(*) AS n FROM silver.silver_nyc_flights"}
            )
            return collected


async def _walk_all_scope(cwd: str) -> dict:
    """A second spawn with the opt-in: every schema in the served file."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "metricmine.server"],
        env={**os.environ, "MM_SERVE_DB": str(_WAREHOUSE), "MM_SERVE_SCOPE": "all"},
        cwd=cwd,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            return {
                "instructions": init.instructions or "",
                "tools": (await session.list_tools()).tools,
                "silver": await session.call_tool(
                    "query", {"sql": "SELECT count(*) AS n FROM silver.silver_nyc_flights"}
                ),
            }


@pytest.fixture(scope="module")
def wire():
    if not _WAREHOUSE.is_file():
        pytest.skip(f"warehouse not built at {_WAREHOUSE}; run `make ingest` first")
    with tempfile.TemporaryDirectory() as cwd:
        return anyio.run(_walk, cwd)


@pytest.fixture(scope="module")
def wire_all_scope():
    if not _WAREHOUSE.is_file():
        pytest.skip(f"warehouse not built at {_WAREHOUSE}; run `make ingest` first")
    with tempfile.TemporaryDirectory() as cwd:
        return anyio.run(_walk_all_scope, cwd)


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
    # carrying DuckDB's own diagnostic, not as a refusal. Pinned here
    # because it is a decision, and decisions that look like oversights get
    # "fixed" by the next contributor.
    typo = wire["typo"]
    assert typo.isError is True
    assert typo.structuredContent is None
    assert "typo" in typo.content[0].text


def test_the_session_survives_an_execution_error(wire):
    categories = wire["after_error"].structuredContent["categories"]
    retail = next(c for c in categories if c["category"] == "invoice_lines")
    assert retail["row_count"] == FACT_ROWS
    # The steer fields arrive over the wire (D-31/D-32 as amended): the
    # mart is preferred and its columns ride along, the provenance
    # pointer and the capture watermark last.
    assert retail["typed_table"] == "mart_invoice_lines_typed"
    assert retail["typed_columns"][-2:] == ["fact_hash_id", "captured_at"]
    assert "not for analytics" in retail["query_hint"]


def test_discovery_carries_the_titles_and_the_annotations(wire):
    """HW-47 at the wire: tools/list carries each tool's title and its four
    hints through the pinned SDK (protocol 2025-11-25)."""
    for tool in wire["tools"]:
        assert tool.title, tool.name
        hints = tool.annotations
        assert (hints.readOnlyHint, hints.destructiveHint, hints.idempotentHint, hints.openWorldHint) == (
            True, False, True, False,
        ), tool.name


def test_silver_is_refused_by_default_and_served_under_the_opt_in(wire, wire_all_scope):
    """HR-8 at the wire (Amendment AB): the default scope answers a silver
    count with a refusal naming the table and the opt-in; the same spawn
    with MM_SERVE_SCOPE=all answers it with the rows."""
    refused = wire["silver_refused"].structuredContent["result"]
    assert refused["refused"] is True
    assert "'silver.silver_nyc_flights' is outside the gold schema" in refused["reason"]
    assert "MM_SERVE_SCOPE=all" in refused["reason"]
    served = wire_all_scope["silver"].structuredContent["result"]
    assert served["rows"] == [[166158]]
    # The opt-in process says so in its own instructions and its query title.
    assert "This server was started with MM_SERVE_SCOPE=all" in " ".join(wire_all_scope["instructions"].split())
    assert {t.name: t.title for t in wire_all_scope["tools"]}["query"] == "Query the served file"

