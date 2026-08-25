"""The MCP server: a thin stdio adapter over the shared query module.

Spec: docs/spec/serving.md §7 (D-31, D-32 as amended). This module holds no
SQL, no connection logic, and no fallback paths of its own — every tool is
one delegation to `metricmine.query.GoldWarehouse`, which owns the read-only
posture and the statement gate (CLAUDE.md rule 18). Nothing here imports
duckdb; that is the adapter boundary, not an accident.

Two SDK mechanics this file depends on, both measured at the pinned mcp
1.29.0 (D-32 Amendment D, F-22):

- A concrete TypedDict return annotation is what produces an output schema
  and structured content. A bare `dict` annotation produces neither, so
  every tool below returns one of the query module's own shapes.
- `FastMCP` carries no `version` argument on the 1.x line; the lowlevel
  server underneath it does, and that is what `initialize` reports.

stdio discipline: this process never writes to stdout — stdout carries
JSON-RPC. There is no `print` in this package.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as package_version
from typing import TypedDict

from mcp.server.fastmcp import FastMCP

from metricmine.query import (
    ROW_CAP_DEFAULT,
    CategoryList,
    ContextResult,
    GoldWarehouse,
    LookupResult,
    QueryRefused,
    QueryResult,
    SchemaResult,
)

SERVER_NAME = "metricmine-gold"

INSTRUCTIONS = """\
Read-only access to the MetricMine gold layer: a unified event star of
content-addressed dimensions and category-parameterized facts.

Start with list_fact_categories: each category names its typed table
(gold.mart_<category>_typed, or gold.vw_<category>_typed where only the
view is emitted) with its columns. Ask analytical questions against that
typed table. The star tables (fact_*, dim_*) are the content-addressed
provenance layer: hash keys and canonical JSON payloads, joined by hash,
meant for lookup_record and audit, not for analytics. Values read through
the typed surface and the payloads are the canonical lowercased text
(D-18 as amended): case-insensitive by design, not a defect.

Five tools, all reads:
- list_fact_categories: the fact categories, their typed tables and
  columns, and row counts.
- get_schema: a schema key's contract, role, and declared field manifest.
- get_context: a schema key's full compiled context.
- query: one SELECT statement, row-capped, against the gold schema.
- lookup_record: every place a content key resolves, with its provenance.

The connection is read-only three layers deep: the database opens read-only,
external filesystem access is disabled and the configuration locked, and
query accepts exactly one statement that is literally a SELECT. Anything
else is refused with the reason named. Results are row-capped and say so:
a truncated result carries truncated=true. Unknown keys are a clean empty
answer with found=false, not an error.\
"""


class QueryRefusal(TypedDict):
    """A refused statement, returned as an answer rather than raised.

    The query module's contract is that refusals raise and the caller
    decides presentation; this is that presentation. It lives here, in the
    adapter, because the module has no opinion on how a refusal should look
    on the wire.
    """

    refused: bool
    reason: str


def _project_version() -> str:
    try:
        return package_version("metricmine")
    except PackageNotFoundError:  # pragma: no cover - installed in every lane
        # Import must never fail; an unknown version is a cosmetic loss.
        return "0.0.0"


server = FastMCP(name=SERVER_NAME, instructions=INSTRUCTIONS)
# FastMCP on the 1.x line takes no `version` argument, but the lowlevel
# server it wraps does, and that field is what a client reads back from
# initialize as serverInfo.version. Measured at 1.29.0; there is no public
# substitute on this line.
server._mcp_server.version = _project_version()

_warehouse: GoldWarehouse | None = None


def warehouse() -> GoldWarehouse:
    """The one shared connection, opened on first use.

    Constructed lazily so importing this module touches no filesystem: the
    CI surface test imports the app with no warehouse present, and a client
    that never calls a tool never opens a database.
    """
    global _warehouse
    if _warehouse is None:
        _warehouse = GoldWarehouse()
    return _warehouse


@server.tool()
def list_fact_categories() -> CategoryList:
    """List the gold fact categories with their table names and row counts."""
    return warehouse().list_fact_categories()


@server.tool()
def get_schema(schema_key: str) -> SchemaResult:
    """Look up a schema key's entity group, contract, role, and manifest.

    An unknown key returns found=false with the other fields null; that is a
    legitimate answer about content-addressed storage, not an error.
    """
    return warehouse().get_schema(schema_key)


@server.tool()
def get_context(schema_key: str) -> ContextResult:
    """Return a schema key's full compiled context and its contract citation."""
    return warehouse().get_context(schema_key)


@server.tool()
def query(sql: str, row_cap: int = ROW_CAP_DEFAULT) -> QueryResult | QueryRefusal:
    """Run one read-only SELECT against gold, row-capped.

    Accepts exactly one statement that parses as a SELECT and leads with
    select, with, or from. Anything else — DDL, DML, multiple statements,
    PRAGMA, SHOW, DESCRIBE, ATTACH, COPY — comes back as
    {"refused": true, "reason": ...} naming the check that failed, rather
    than as an error. Results are capped at row_cap rows (default 100,
    maximum 500) and set truncated=true when more rows existed.
    """
    try:
        return warehouse().query(sql, row_cap)
    except QueryRefused as exc:
        return {"refused": True, "reason": str(exc)}


@server.tool()
def lookup_record(content_key: str) -> LookupResult:
    """Find every place a content key resolves, labeled with where it was found.

    Searches the context registry, the fact tables' hash-id columns, each
    dimension's identity column, and derived identities inside dimension
    payloads. An unknown key returns found=false with no hits.
    """
    return warehouse().lookup_record(content_key)
