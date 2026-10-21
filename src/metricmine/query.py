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
the 29-case matrix that pins them lives in tests/test_query_gate.py. The
scope gate behind it (D-31 as amended by Amendment AB, HR-8) reads gold
by default and opens every schema in the served file only through
MM_SERVE_SCOPE=all; its matrix lives in tests/test_query_scope.py.
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

from metricmine.tasks import command

ENV_VAR = "MM_SERVE_DB"
# What `query` may read (D-31 as amended by Amendment AB, HR-8): `gold`,
# the default, refuses a statement that names a base table outside the
# gold schema; `all` is the explicit opt-in for the modeler's read path
# against a working warehouse (S36), where every schema in the served
# file is reachable, read-only. Any other value fails closed at startup.
SCOPE_ENV_VAR = "MM_SERVE_SCOPE"
SCOPE_GOLD = "gold"
SCOPE_ALL = "all"
SCOPES = (SCOPE_GOLD, SCOPE_ALL)
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
    subject: str
    context_keys: dict[str, str]


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


def resolve_scope(scope: str | None = None) -> str:
    """Explicit argument, then MM_SERVE_SCOPE, then gold (Amendment AB).
    A value outside the two known ones fails closed, naming both."""
    value = scope if scope is not None else (os.environ.get(SCOPE_ENV_VAR) or SCOPE_GOLD)
    if value not in SCOPES:
        raise ValueError(
            f"{SCOPE_ENV_VAR}={value!r} is not a scope; use {SCOPE_GOLD!r} (the default: query reads"
            f" the gold schema) or {SCOPE_ALL!r} (every schema in the served file, read-only)"
        )
    return value


# Table functions that take a string or a name and return a table's rows
# or values, so a scope gate on base tables alone would not close them
# (F-72, measured at duckdb 1.4.3 under the hardened session:
# `query_table('silver.silver_flights')`, `query('select ...')`, and
# `json_execute_serialized_sql(...)` each returned the silver table's
# count; `duckdb_table_sample` takes a table name the same way; and
# `pragma_storage_info('silver.x')` returns per-segment statistics whose
# text carries a column's minimum and maximum). Refused by name under the
# gold scope; every other table function stays reachable as before, under
# the three layers, and exposes engine metadata (names, types, sizes),
# never rows or values outside gold.
SCOPE_DENIED_TABLE_FUNCTIONS = frozenset(
    {"query", "query_table", "json_execute_serialized_sql", "duckdb_table_sample", "pragma_storage_info"}
)


def _is_recursive_cte(query: Any) -> bool:
    node = query.get("node") if isinstance(query, dict) else None
    return isinstance(node, dict) and node.get("type") == "RECURSIVE_CTE_NODE"


def _walk_tables(
    node: Any,
    scope: frozenset[str],
    tables: list[tuple[str, str, str]],
    functions: list[str],
) -> None:
    """Walk the parse tree with the common table expressions in scope.

    A CTE name is in scope for the statement body that declares it and
    for the CTEs declared after it, and inside its own body only when it
    is recursive. A schema-less name outside its scope is a base table
    (measured at 1.4.3: `with main_t as (select * from main_t) ...` binds
    the inner name to the catalog table, so a flat exclusion by name would
    pass it)."""
    if isinstance(node, dict):
        if node.get("type") == "BASE_TABLE":
            schema = str(node.get("schema_name", ""))
            table = str(node.get("table_name", ""))
            if not (schema == "" and table.lower() in scope):
                tables.append((str(node.get("catalog_name", "")), schema, table))
        if node.get("type") == "TABLE_FUNCTION":
            function = node.get("function")
            if isinstance(function, dict) and function.get("function_name") is not None:
                functions.append(str(function["function_name"]).lower())
        inner = scope
        cte_map = node.get("cte_map")
        if isinstance(cte_map, dict) and cte_map.get("map"):
            declared = set(scope)
            for entry in cte_map["map"]:
                if not isinstance(entry, dict) or entry.get("key") is None:
                    continue
                key = str(entry["key"]).lower()
                query = (entry.get("value") or {}).get("query")
                body_scope = frozenset(declared | ({key} if _is_recursive_cte(query) else set()))
                _walk_tables(query, body_scope, tables, functions)
                declared.add(key)
            inner = frozenset(declared)
        for key, value in node.items():
            if key == "cte_map":
                continue
            _walk_tables(value, inner, tables, functions)
    elif isinstance(node, list):
        for value in node:
            _walk_tables(value, scope, tables, functions)


def statement_tables(
    con: duckdb.DuckDBPyConnection, sql: str
) -> tuple[list[tuple[str, str, str]], list[str]]:
    """The base tables a gated SELECT names, as (catalog, schema, table),
    and the table functions it calls, read from DuckDB's own parse tree
    (`json_serialize_sql`) under the served session. A reference to a
    common table expression in scope is not a base table. Raises
    QueryRefused when the parser cannot serialize the statement, so the
    scope gate fails closed rather than open (no lone gated SELECT
    measured at duckdb 1.4.3 does; PIVOT without an IN list desugars into
    two statements, which the statement gate refuses first, and PIVOT with
    one is a PIVOT node whose source is a base table the walk sees)."""
    serialized = json.loads(con.execute("select json_serialize_sql(?)", [sql]).fetchone()[0])
    if serialized.get("error"):
        raise QueryRefused(
            "scope: the statement's tables could not be read from its parse tree"
            f" ({serialized.get('error_type')}: {serialized.get('error_message')})"
        )
    tables: list[tuple[str, str, str]] = []
    functions: list[str] = []
    _walk_tables(serialized, frozenset(), tables, functions)
    return tables, functions


def scope_gate(con: duckdb.DuckDBPyConnection, sql: str, scope: str) -> None:
    """Amendment AB (HR-8): under the default scope, refuse a statement
    that names a base table outside the gold schema, or calls a table
    function that takes a table's name or a statement as a string, naming
    what was refused and the opt-in. A schema-less name is refused too:
    nothing in the served file is served without its schema, and the
    refusal says how to name it. Under `all` everything the three layers
    allow passes."""
    if scope == SCOPE_ALL:
        return
    tables, functions = statement_tables(con, sql)
    for function in functions:
        if function in SCOPE_DENIED_TABLE_FUNCTIONS:
            raise QueryRefused(
                f"scope: the table function {function}() takes a table's name or a statement as a"
                f" string and is refused under the gold scope; name a gold table ({GOLD_SCHEMA}.<table>)"
                f" directly, or start the server with {SCOPE_ENV_VAR}={SCOPE_ALL}"
            )
    for catalog, schema, table in tables:
        if schema.lower() == GOLD_SCHEMA:
            continue
        named = ".".join(part for part in (catalog, schema, table) if part)
        if schema == "":
            raise QueryRefused(
                f"scope: {named!r} names no schema; name a gold table as {GOLD_SCHEMA}.{table}"
                f" (this server serves the gold schema; {SCOPE_ENV_VAR}={SCOPE_ALL} at startup"
                " reads every schema in the served file)"
            )
        raise QueryRefused(
            f"scope: {named!r} is outside the gold schema this server serves; name a gold"
            f" table ({GOLD_SCHEMA}.<table>), or start the server with {SCOPE_ENV_VAR}={SCOPE_ALL}"
            " to read every schema in the served file"
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

    def __init__(self, path: str | Path | None = None, scope: str | None = None) -> None:
        # The scope resolves before the connection opens, so a bad value
        # fails at startup and never after a client's first statement.
        self.scope = resolve_scope(scope)
        resolved = resolve_db_path(path)
        if not resolved.is_file():
            raise FileNotFoundError(
                f"no gold database at {resolved} "
                f"({ENV_VAR}={os.environ.get(ENV_VAR) or 'unset'}, "
                f"default {DEMO_DB}). Restore the release asset with "
                f"`{command('demo-fetch')}` or build it with `{command('demo')}`, "
                f"or point {ENV_VAR} at a built warehouse."
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
        registry = self._category_registry()
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
                    " String columns there carry canonical lowercase text:"
                    " write literals in lowercase (origin_airport = 'jfk')."
                    " get_context on the keys in context_keys returns what"
                    " the columns are (data) and, kept apart by name, what"
                    " the people who approved the contracts wrote about"
                    " them (expert_context): units, vintages, nulls, joins."
                )
            else:
                query_hint = (
                    f"Query gold.{table}; no typed surface is emitted for"
                    " this category."
                )
            entries = registry.get(category, {})
            dimensions = entries.get("dimensions", {})
            categories.append(
                {
                    "category": category,
                    "fact_table": table,
                    "row_count": int(count),
                    "typed_table": typed_table,
                    "typed_columns": typed_columns,
                    "query_hint": query_hint,
                    "subject": dimensions.get("subject", ""),
                    "context_keys": {
                        role: entry["schema_key"] for role, entry in entries.items()
                    },
                }
            )
        return {"categories": categories}

    def _category_registry(self) -> dict[str, dict[str, dict[str, str]]]:
        """category -> role -> {schema_key, subject} from the registry's
        category entries (Amendment W to D-31): the subject is the
        authored expert context's opening line, so a category listing
        says what each category IS in the words of the people who
        approved its contracts, and names the keys get_context resolves.
        An absent registry reads as empty."""
        if not self._tables(REGISTRY_TABLE):
            return {}
        out: dict[str, dict[str, dict[str, str]]] = {}
        rows = self._con.execute(
            f"select schema_key, compiled_context from {self._rel(REGISTRY_TABLE)}"
        ).fetchall()
        for schema_key, raw in rows:
            try:
                compiled = json.loads(raw)
            except (TypeError, ValueError):
                continue
            category = compiled.get("category")
            role = compiled.get("role")
            if not category or role not in ("dimensions", "measures"):
                continue
            expert = compiled.get("expert_context") or {}
            out.setdefault(category, {})[role] = {
                "schema_key": schema_key,
                "subject": str(expert.get("subject", "")),
            }
        return out

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
        """Gate, scope, run, cap. The cap+1 fetch is what makes `truncated`
        honest.

        Refusals raise QueryRefused naming the failed check; presentation is
        the caller's business. The scope gate (Amendment AB) runs after
        the statement gate, so it only ever reads a lone SELECT.
        """
        gate(sql)
        scope_gate(self._con, sql, self.scope)
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
            # Compiled schema 2.0.0 keeps the typed declarations under
            # data; the pre-fan-in artifact carried the key at the top.
            data = compiled.get("data") or compiled
            names = sorted(data.get("derived_identifiers", {}))
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
