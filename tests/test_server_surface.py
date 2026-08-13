"""CI-lane tests for the MCP server's tool surface.

No warehouse and no subprocess: the app is imported in-process and its
tools listed. That works only because the warehouse opens lazily, which is
itself asserted below — an import that connected would make this lane
depend on a database CI does not build.

The tool listing is async. This project configures neither pytest-asyncio
nor the anyio pytest plugin, so the tests stay synchronous and drive the
coroutine with `anyio.run`; anyio is already present as an mcp dependency.
"""

from importlib.metadata import version as package_version

import anyio

from metricmine.server import app

SPEC_TOOLS = {
    "get_context",
    "get_schema",
    "list_fact_categories",
    "lookup_record",
    "query",
}


def _list_tools():
    async def collect():
        return await app.server.list_tools()

    return anyio.run(collect)


def test_registers_exactly_five_tools():
    assert len(_list_tools()) == 5


def test_tool_names_are_the_five_spec_names():
    assert {tool.name for tool in _list_tools()} == SPEC_TOOLS


def test_every_tool_declares_an_output_schema():
    # The regression gate on F-22's shape finding: a concrete typed return
    # produces an output schema, a bare `dict` produces none. A tool
    # annotated `-> dict` would lose structured output silently, so the
    # absence is asserted here rather than discovered by a client.
    missing = [tool.name for tool in _list_tools() if not tool.outputSchema]
    assert missing == []


def test_query_declares_both_result_branches():
    # The query tool returns QueryResult | QueryRefusal, which the SDK
    # renders as a `result` property with an anyOf over both shapes.
    schema = next(t for t in _list_tools() if t.name == "query").outputSchema
    branches = schema["properties"]["result"]["anyOf"]
    assert len(branches) == 2
    assert set(schema["$defs"]) == {"QueryResult", "QueryRefusal"}


def test_query_takes_sql_and_an_optional_row_cap():
    schema = next(t for t in _list_tools() if t.name == "query").inputSchema
    assert set(schema["properties"]) == {"sql", "row_cap"}
    assert schema["required"] == ["sql"]
    assert schema["properties"]["row_cap"]["default"] == 100


def test_server_is_named_for_the_spec():
    assert app.server.name == "metricmine-gold"


def test_server_reports_the_project_version():
    # Computed independently here, not from app._project_version(): that
    # helper falls back rather than raising, and comparing it to itself
    # would pass vacuously. This assertion exists to guard the reach into
    # the lowlevel server's version field, which is the only way to set it
    # on the 1.x SDK line.
    assert app.server._mcp_server.version == package_version("metricmine")


def test_importing_the_app_opens_no_database():
    # Importing this module must touch no filesystem: a client that never
    # calls a tool never opens a database, and this lane has no warehouse.
    assert app._warehouse is None
