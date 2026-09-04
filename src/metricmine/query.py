"""The shared gold query module: one read-only surface for every consumer.

Spec: docs/spec/serving.md §§2-6 (D-31). All gold access flows through
`GoldWarehouse`; the MCP server and the hosted demo import it and neither
reimplements it (CLAUDE.md rule 18). Read-only runs three layers deep: a
`read_only=True` connection, a hardened session, and a statement gate that
accepts exactly one literal SELECT. Every method here is a SELECT: no DDL
and no DML anywhere in this module, which is the same posture as the D-11
protocol in `metricmine.warehouse.duckdb`.

Results are JSON-shaped (TypedDicts of JSON-native values), so the server
and the demo serialize them without translation.

The gate's semantics were probed against duckdb 1.4.3 on August 13, 2026;
the 29-case matrix that pins them lives in tests/test_query_gate.py.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any, TypedDict

import duckdb

ENV_VAR = "MM_SERVE_DB"
# The committed demo artifact (D-03) resolves from this module's own
# location, never the process CWD: the server is launched by a desktop
# client whose working directory is not the repo root (spec §5).
DEMO_DB = Path(__file__).resolve().parents[2] / "demo" / "demo.duckdb"

GOLD_SCHEMA = "gold"
REGISTRY_TABLE = "context_registry"
FACT_TABLE_PATTERN = "fact_%_values"
DIM_TABLE_PATTERN = "dim_%_values"

ROW_CAP_DEFAULT = 100
ROW_CAP_MAX = 500
ROW_CAP_MIN = 1
# `lookup_record` is a provenance tool, not a bulk reader: each hit reports
# its true match_count but returns at most this many rows.
LOOKUP_ROW_CAP = 100

_COMMENT = re.compile(r"(?s)\s*(?:--[^\n]*\n\s*|/\*.*?\*/\s*)*")
_ALLOWED_HEADS = ("select", "with", "from")


class QueryRefused(Exception):
    """A statement the serving gate refuses; the message names the check."""


class FactCategory(TypedDict):
    category: str
    fact_table: str
    row_count: int
    typed_table: str | None
    typed_columns: list[str]
    query_hint: str


class CategoryList(TypedDict):
    categories: list[FactCategory]


class SchemaResult(TypedDict):
    found: bool
    schema_key: str
    entity_group: str | None
    contract_name: str | None
    contract_version: str | None
    role: str | None
    manifest: list[str] | None


class ContextResult(TypedDict):
    found: bool
    schema_key: str
    contract_name: str | None
    contract_version: str | None
    compiled_context: dict[str, Any] | None


class QueryResult(TypedDict):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    row_cap: int


class LookupHit(TypedDict):
    table: str
    column: str
    match_count: int
    rows: list[dict[str, Any]]


class LookupResult(TypedDict):
    content_key: str
    found: bool
    hits: list[LookupHit]


def _ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _jsonable(value: Any) -> Any:
    """Render a DuckDB value JSON-native at the result boundary.

    Decimals become strings rather than floats: an exact price must not
    lose precision on the way to a client.
    """
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    return str(value)


def first_keyword(sql: str) -> str:
    """The first meaningful keyword, skipping line and block comments."""
    rest = _COMMENT.match(sql).end()
    m = re.match(r"[A-Za-z_]+", sql[rest:])
    return m.group(0).lower() if m else ""


def gate(sql: str) -> None:
    """Raise QueryRefused unless sql is exactly one literal SELECT.

    Three checks, in order (spec §3, layer 3). The leading-keyword check is
    what makes "SELECT only" literal: DuckDB rewrites PRAGMA reads, SHOW,
    DESCRIBE, and SUMMARIZE into SELECT-typed reads, so the type check alone
    would pass them.
    """
    try:
        statements = duckdb.extract_statements(sql)
    except duckdb.Error as exc:
        raise QueryRefused(f"parse error ({type(exc).__name__}): {exc}") from exc
    if len(statements) != 1:
        raise QueryRefused(f"{len(statements)} statements; exactly one required")
    if statements[0].type != duckdb.StatementType.SELECT:
        raise QueryRefused(
            f"statement type {statements[0].type.name}; SELECT required"
        )
    head = first_keyword(sql)
    if head not in _ALLOWED_HEADS:
        raise QueryRefused(
            f"leading keyword {head or '(none)'!r}; select/with/from required"
        )


def clamp_row_cap(row_cap: int) -> int:
    """Clamp a requested cap into [1, 500] (spec §4)."""
    return max(ROW_CAP_MIN, min(int(row_cap), ROW_CAP_MAX))


def resolve_db_path(path: str | Path | None = None) -> Path:
    """Explicit argument, then MM_SERVE_DB, then demo/demo.duckdb (spec §5)."""
    if path is not None:
        return Path(path)
    env = os.environ.get(ENV_VAR)
    if env:
        return Path(env)
    return DEMO_DB


class GoldWarehouse:
    """The read-only gold surface: five lookups over one hardened connection."""

    def __init__(self, path: str | Path | None = None) -> None:
        resolved = resolve_db_path(path)
        if not resolved.is_file():
            raise FileNotFoundError(
                f"no gold database at {resolved} "
                f"({ENV_VAR}={os.environ.get(ENV_VAR) or 'unset'}, "
                f"default {DEMO_DB}). Build the committed artifact with "
                f"`make export-demo`, or point {ENV_VAR} at a built warehouse."
            )
        self.path = resolved
        # Layer 1: the connection itself refuses DDL and DML on the data.
        self._con = duckdb.connect(str(resolved), read_only=True)
        # Layer 2: session hardening, before any client statement. Order
        # matters and was probed at 1.4.3: lock_configuration seals every
        # option including the timezone, so the D-11 determinism setting has
        # to be applied before the seal, never after.
        self._con.execute("SET enable_external_access = false")
        self._con.execute("SET timezone = 'UTC'")
        self._con.execute("SET lock_configuration = true")

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> GoldWarehouse:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------ helpers

    def _rel(self, table: str) -> str:
        return f"{_ident(GOLD_SCHEMA)}.{_ident(table)}"

    def _tables(self, pattern: str) -> list[str]:
        rows = self._con.execute(
            "select table_name from information_schema.tables"
            " where table_schema = ? and table_name like ? order by table_name",
            [GOLD_SCHEMA, pattern],
        ).fetchall()
        return [row[0] for row in rows]

    def _columns(self, table: str) -> list[str]:
        rows = self._con.execute(
            "select column_name from information_schema.columns"
            " where table_schema = ? and table_name = ? order by ordinal_position",
            [GOLD_SCHEMA, table],
        ).fetchall()
        return [row[0] for row in rows]

    def _registry_row(self, schema_key: str) -> tuple[str, str, str, dict] | None:
        row = self._con.execute(
            "select entity_group, contract_name, contract_version, compiled_context"
            f" from {self._rel(REGISTRY_TABLE)} where schema_key = ?",
            [schema_key],
        ).fetchone()
        if row is None:
            return None
        return row[0], row[1], row[2], json.loads(row[3])

    # -------------------------------------------------------------- tools

    def list_fact_categories(self) -> CategoryList:
        """Categories from the physical fact tables (spec §2), each naming
        its typed surface (D-31/D-32 as amended): the materialized mart
        when it exists, else the projection view, else none. The star
        tables stay the provenance layer; the hint says so in words an
        agent acts on.
        """
        categories: list[FactCategory] = []
        for table in self._tables(FACT_TABLE_PATTERN):
            (count,) = self._con.execute(
                f"select count(*) from {self._rel(table)}"
            ).fetchone()
            category = table[len("fact_") : -len("_values")]
            # The LIKE pattern is an exact name here: no wildcard.
            typed_table = next(
                (
                    candidate
                    for candidate in (
                        f"mart_{category}_typed",
                        f"vw_{category}_typed",
                    )
                    if self._tables(candidate)
                ),
                None,
            )
            typed_columns = self._columns(typed_table) if typed_table else []
            if typed_table:
                query_hint = (
                    f"Ask questions against gold.{typed_table} (typed"
                    f" columns, one row per {category} event)."
                    f" gold.{table} and the dim_* tables are the"
                    " content-addressed provenance layer: hash keys and"
                    " canonical JSON payloads, joined by hash, meant for"
                    " lookup_record and audit, not for analytics."
                )
            else:
                query_hint = (
                    f"Query gold.{table}; no typed surface is emitted for"
                    " this category."
                )
            categories.append(
                {
                    "category": category,
                    "fact_table": table,
                    "row_count": int(count),
                    "typed_table": typed_table,
                    "typed_columns": typed_columns,
                    "query_hint": query_hint,
                }
            )
        return {"categories": categories}

    def get_schema(self, schema_key: str) -> SchemaResult:
        """The registry's declaration for a schema key: contract, role, manifest."""
        row = self._registry_row(schema_key)
        if row is None:
            return {
                "found": False,
                "schema_key": schema_key,
                "entity_group": None,
                "contract_name": None,
                "contract_version": None,
                "role": None,
                "manifest": None,
            }
        entity_group, contract_name, contract_version, context = row
        return {
            "found": True,
            "schema_key": schema_key,
            "entity_group": entity_group,
            "contract_name": contract_name,
            "contract_version": contract_version,
            "role": context.get("role"),
            "manifest": context.get("manifest"),
        }

    def get_context(self, schema_key: str) -> ContextResult:
        """The full compiled context for a schema key, plus its citation."""
        row = self._registry_row(schema_key)
        if row is None:
            return {
                "found": False,
                "schema_key": schema_key,
                "contract_name": None,
                "contract_version": None,
                "compiled_context": None,
            }
        _entity_group, contract_name, contract_version, context = row
        return {
            "found": True,
            "schema_key": schema_key,
            "contract_name": contract_name,
            "contract_version": contract_version,
            "compiled_context": context,
        }

    def query(self, sql: str, row_cap: int = ROW_CAP_DEFAULT) -> QueryResult:
        """Gate, run, cap. The cap+1 fetch is what makes `truncated` honest.

        Refusals raise QueryRefused naming the failed check; presentation is
        the caller's business.
        """
        gate(sql)
        cap = clamp_row_cap(row_cap)
        cur = self._con.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = cur.fetchmany(cap + 1)
        return {
            "columns": columns,
            "rows": [[_jsonable(v) for v in row] for row in rows[:cap]],
            "row_count": min(len(rows), cap),
            "truncated": len(rows) > cap,
            "row_cap": cap,
        }

    def lookup_record(self, content_key: str) -> LookupResult:
        """Every place a content key resolves, labeled with where it was found.

        The search surface is discovered from information_schema at call
        time rather than hard-coded: a new category adds its fact and
        dimension tables to the star, and this finds them without an edit.
        """
        hits: list[LookupHit] = []
        self._collect(hits, REGISTRY_TABLE, "schema_key", content_key)
        for table in self._tables(FACT_TABLE_PATTERN):
            for column in self._hash_columns(table):
                self._collect(hits, table, column, content_key)
        dim_tables = self._tables(DIM_TABLE_PATTERN)
        for table in dim_tables:
            column = self._identity_column(table)
            if column is not None:
                self._collect(hits, table, column, content_key)
        # Derived identities live inside the dimension payloads, so they are
        # reachable only through the JSON, never as a column of their own.
        # The registry names each category's identifiers (D-19: the address
        # of meaning), so a new category's identity is searchable without
        # an edit here; before the multi-source fan-in this path was the
        # one committed name, line_identity.
        identity_paths = self._derived_identity_paths()
        for table in dim_tables:
            payload = self._payload_column(table)
            category = table[len("dim_") : -len("_values")]
            for name in identity_paths.get(category, []):
                if payload is not None:
                    self._collect(
                        hits, table, payload, content_key, json_path=f"$.{name}"
                    )
        return {"content_key": content_key, "found": bool(hits), "hits": hits}

    def _derived_identity_paths(self) -> dict[str, list[str]]:
        """Derived identifier names per category, from the registry's
        dimensions entries; an empty dict when the registry is absent."""
        if not self._tables(REGISTRY_TABLE):
            return {}
        paths: dict[str, list[str]] = {}
        rows = self._con.execute(
            f"select compiled_context from {self._rel(REGISTRY_TABLE)}"
        ).fetchall()
        for (raw,) in rows:
            try:
                compiled = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if compiled.get("role") != "dimensions":
                continue
            category = compiled.get("category")
            names = sorted(compiled.get("derived_identifiers", {}))
            if category and names:
                paths[category] = names
        return paths

    # --------------------------------------------- lookup search surface

    def _hash_columns(self, table: str) -> list[str]:
        return [c for c in self._columns(table) if c.endswith("_hash_id")]

    def _identity_column(self, table: str) -> str | None:
        # The identity is the hash id that is not a columns-manifest hash;
        # its prefix follows the role, not the table name (the category
        # dimension keys on dim_hash_id, not invoice_lines_hash_id).
        for column in self._columns(table):
            if column.endswith("_hash_id") and not column.endswith("_col_hash_id"):
                return column
        return None

    def _payload_column(self, table: str) -> str | None:
        for column in self._columns(table):
            if column.endswith("_values"):
                return column
        return None

    def _collect(
        self,
        hits: list[LookupHit],
        table: str,
        column: str,
        content_key: str,
        json_path: str | None = None,
    ) -> None:
        rel = self._rel(table)
        if json_path is None:
            expr = _ident(column)
            label = column
        else:
            # json_path is a module constant, never caller input.
            expr = f"json_extract_string({_ident(column)}, '{json_path}')"
            label = f"{column}.{json_path}"
        (count,) = self._con.execute(
            f"select count(*) from {rel} where {expr} = ?", [content_key]
        ).fetchone()
        if not count:
            return
        cur = self._con.execute(
            f"select * from {rel} where {expr} = ? limit {LOOKUP_ROW_CAP}",
            [content_key],
        )
        columns = [d[0] for d in cur.description]
        hits.append(
            {
                "table": table,
                "column": label,
                "match_count": int(count),
                "rows": [
                    {c: _jsonable(v) for c, v in zip(columns, row, strict=True)}
                    for row in cur.fetchall()
                ],
            }
        )
