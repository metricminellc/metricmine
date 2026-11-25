"""prepare: the governed feedback message, rendered by code (E1T; the
governed host plan, Sections 2.3 and 6).

A person asks for feedback about a served field. This module re-runs the
person's query through the serving module's own statement and scope
gates on the served file, counts the matching rows under a cap, stamps
the governing contract versions and the served file's identity, and
renders the five-part message. It returns the message and writes
nothing: no file, no network call, no issue. The person sends it.

What the server can check, it checks: the kind is one of six; the field
names a served category and, for every kind but missing_field, one of
its typed columns; the query is one literal SELECT under the server's
scope that names the category's own tables, returns rows and never an
aggregate (set operations included), calls no volatile function, and
counts the same rows in its canonical form as in the person's own text;
the count is measured on the served file. What the server cannot check,
it labels: the claim and the query are the caller's own text (design
rule 4; lesson 3: a count can carry a value, so the person reads the
message before sending it).

A refusal names the check that failed and its remedy, so a host can
repair the call rather than guess. The remedies are the one class of
directing text a result of this tool carries: the server's own code
about its own interface.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import duckdb

from metricmine.query import GoldWarehouse, QueryRefused, gate, scope_gate, statement_tables

from .layout import FENCE_CLOSE, FENCE_OPEN, KINDS, fold, split_field

COUNT_CAP = 1_000_000
CLAIM_CAP = 2_000
REGISTRY_COLUMNS = ("schema_key", "entity_group", "contract_name", "contract_version", "compiled_context")
CALLER_SUPPLIED = ("claim", "query")
# Keywords DuckDB parses as column references and binds as clock reads.
CLOCK_KEYWORDS = frozenset(
    {"current_date", "current_timestamp", "current_time", "localtime", "localtimestamp", "current_localtime", "current_localtimestamp"}
)


class FeedbackRefused(Exception):
    """A refused call: the check that failed, and what would pass it."""

    def __init__(self, reason: str, remedy: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.remedy = remedy


@dataclass
class Prepared:
    field: str
    kind: str
    claim: str
    query: str  # canonical, comments stripped, one line
    rows_matching: int
    contracts: dict[str, str]  # contract name -> version, in governing order
    served_file_sha256: str
    served_file_bytes: int
    registry_rows: int
    registry_md5: str
    server_version: str
    query_literals: list[str]

    def message(self) -> str:
        return render(self)


# ------------------------------------------------------------ measurements

_file_stamps: dict[tuple[str, int, int], tuple[str, int]] = {}


def served_file_stamp(path: Path) -> tuple[str, int]:
    """sha256 and size of the served file, computed over the file itself
    (never read from a manifest), cached per path, size, and mtime."""
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns)
    if key not in _file_stamps:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        _file_stamps[key] = (digest.hexdigest(), stat.st_size)
    return _file_stamps[key]


def registry_digest(con: duckdb.DuckDBPyConnection) -> tuple[int, str]:
    """The exporter's method (src/metricmine/export_demo.py): the ordered
    md5 over the registry's deterministic columns, never loaded_at."""
    rendered = ", ".join(f"coalesce(cast(\"{c}\" as varchar), '')" for c in REGISTRY_COLUMNS)
    count, digest = con.execute(
        "select count(*), md5(string_agg(line, chr(10) order by line))"
        f" from (select concat_ws(chr(31), {rendered}) as line from gold.context_registry)"
    ).fetchone()
    return int(count), str(digest)


def _parse_tree(con: duckdb.DuckDBPyConnection, sql: str) -> dict:
    serialized = json.loads(con.execute("select json_serialize_sql(?)", [sql]).fetchone()[0])
    if serialized.get("error"):
        raise FeedbackRefused(
            f"the query could not be parsed ({serialized.get('error_message')})",
            "write one SELECT that DuckDB parses",
        )
    return serialized


def canonical_sql(con: duckdb.DuckDBPyConnection, sql: str) -> str:
    """The query as DuckDB deserializes its own parse tree: one statement
    on one line, comments gone (a comment is outside the tree, measured
    September 17, 2026)."""
    serialized = con.execute("select json_serialize_sql(?)", [sql]).fetchone()[0]
    (text,) = con.execute("select json_deserialize_sql(?::json)", [serialized]).fetchone()
    return fold(str(text).strip().rstrip(";"))


def aggregate_names(con: duckdb.DuckDBPyConnection) -> frozenset[str]:
    rows = con.execute("select distinct function_name from duckdb_functions() where function_type = 'aggregate'").fetchall()
    return frozenset(r[0].lower() for r in rows)


def volatile_names(con: duckdb.DuckDBPyConnection) -> frozenset[str]:
    """Functions DuckDB's own catalog marks as not consistent across calls
    (random, now, uuid, nextval and the like), plus the clock keywords."""
    rows = con.execute(
        "select distinct function_name from duckdb_functions() where stability is not null and stability <> 'CONSISTENT'"
    ).fetchall()
    return frozenset(r[0].lower() for r in rows) | CLOCK_KEYWORDS


def _select_nodes(node, found: list[dict]) -> None:
    """The outermost SELECT nodes of a statement, through set operations
    (UNION, EXCEPT, INTERSECT) but never into a subquery expression."""
    if not isinstance(node, dict):
        return
    kind = node.get("type")
    if kind == "SELECT_NODE":
        found.append(node)
    elif kind == "SET_OPERATION_NODE":
        for child in (node.get("left"), node.get("right"), *(node.get("children") or [])):
            _select_nodes(child, found)
    elif kind == "CTE_NODE":
        _select_nodes(node.get("child"), found)


def _top_level_aggregates(node, aggregates: frozenset[str], found: list[str]) -> None:
    """Aggregate function calls in an expression tree, not descending into
    subqueries (a subquery in the select list is its own statement)."""
    if isinstance(node, dict):
        if node.get("type") == "SUBQUERY":
            return
        if node.get("class") == "FUNCTION" and str(node.get("function_name", "")).lower() in aggregates:
            found.append(str(node["function_name"]).lower())
        for value in node.values():
            _top_level_aggregates(value, aggregates, found)
    elif isinstance(node, list):
        for value in node:
            _top_level_aggregates(value, aggregates, found)


def aggregate_reasons(con: duckdb.DuckDBPyConnection, sql: str) -> list[str]:
    """Why the query is not 'the rows in question': a GROUP BY or an
    aggregate call in an outermost SELECT, each side of a set operation
    included. Empty when it is rows."""
    serialized = _parse_tree(con, sql)
    reasons: list[str] = []
    aggregates = aggregate_names(con)
    for stmt in serialized.get("statements", []):
        selects: list[dict] = []
        _select_nodes(stmt.get("node", {}), selects)
        for node in selects:
            if node.get("group_expressions"):
                reasons.append("GROUP BY in an outermost SELECT")
            found: list[str] = []
            _top_level_aggregates(node.get("select_list", []), aggregates, found)
            if found:
                reasons.append("aggregate call(s) in an outermost select list: " + ", ".join(sorted(set(found))))
    return sorted(set(reasons))


def _function_and_ref_names(node, functions: list[str], refs: list[str]) -> None:
    if isinstance(node, dict):
        if node.get("class") == "FUNCTION" and node.get("function_name"):
            functions.append(str(node["function_name"]).lower())
        if node.get("class") == "COLUMN_REF":
            names = node.get("column_names") or []
            if len(names) == 1:
                refs.append(str(names[0]).lower())
        for value in node.values():
            _function_and_ref_names(value, functions, refs)
    elif isinstance(node, list):
        for value in node:
            _function_and_ref_names(value, functions, refs)


def volatile_calls(con: duckdb.DuckDBPyConnection, sql: str) -> list[str]:
    """The volatile functions and clock keywords a query calls, anywhere in
    its tree, so a count a producer re-runs can be the same count."""
    functions: list[str] = []
    refs: list[str] = []
    _function_and_ref_names(_parse_tree(con, sql).get("statements", []), functions, refs)
    names = volatile_names(con)
    return sorted({f for f in functions if f in names} | {r for r in refs if r in CLOCK_KEYWORDS})


_select_template: dict | None = None


def _render_expression(con: duckdb.DuckDBPyConnection, node: dict) -> str:
    """One expression node rendered back to SQL text by DuckDB's own
    deserializer, through a `SELECT <expression>` template."""
    global _select_template
    if _select_template is None:
        _select_template = json.loads(con.execute("select json_serialize_sql('select 1')").fetchone()[0])
    tree = copy.deepcopy(_select_template)
    tree["statements"][0]["node"]["select_list"] = [node]
    (text,) = con.execute("select json_deserialize_sql(?::json)", [json.dumps(tree)]).fetchone()
    text = str(text).strip()
    return text[len("SELECT ") :] if text.upper().startswith("SELECT ") else text


def _constants(con: duckdb.DuckDBPyConnection, node, found: list[str]) -> None:
    if isinstance(node, dict):
        if node.get("class") == "CAST" and isinstance(node.get("child"), dict) and node["child"].get("class") == "CONSTANT":
            found.append(_render_expression(con, node))
            return
        if node.get("class") == "CONSTANT":
            found.append(_render_expression(con, node))
            return
        for value in node.values():
            _constants(con, value, found)
    elif isinstance(node, list):
        for value in node:
            _constants(con, value, found)


def query_literals(con: duckdb.DuckDBPyConnection, sql: str) -> list[str]:
    """Every constant in the query's parse tree, rendered as SQL text by
    DuckDB's own deserializer (a decimal keeps its scale, a string its
    quotes, a typed literal its CAST), listed by code so the person's
    reading of the message is directed at the values it carries. A
    comment is outside the tree and is stripped by canonical_sql. A value
    can still ride in a subquery, an alias, or the claim; the person's
    reading is the control."""
    found: list[str] = []
    _constants(con, _parse_tree(con, sql).get("statements", []), found)
    return found


def contracts_from_entries(entries: dict) -> dict[str, str]:
    """contract name -> version, in governing order (mapping, silver,
    star), from a category's registry entries' governing_contracts; the
    first statement of a name wins. Shared by prepare and verify."""
    versions: dict[str, str] = {}
    for ctx in entries.values():
        governing = ((ctx.get("compiled_context") or {}).get("expert_context") or {}).get("governing_contracts") or {}
        for value in governing.values():
            name, _, ver = str(value).rpartition(" ")
            if name and ver:
                versions.setdefault(name, ver.lstrip("v"))
        if ctx.get("contract_name"):
            versions.setdefault(str(ctx["contract_name"]), str(ctx["contract_version"]))
    return versions


def category_entries(wh: GoldWarehouse, category: str) -> dict:
    cats = {c["category"]: c for c in wh.list_fact_categories()["categories"]}
    if category not in cats:
        return {}
    return {role: wh.get_context(key) for role, key in cats[category]["context_keys"].items()}


def category_contracts(wh: GoldWarehouse, category: str) -> dict[str, str]:
    categories = {c["category"]: c for c in wh.list_fact_categories()["categories"]}
    if category not in categories:
        raise FeedbackRefused(
            f"no served category named {category!r}",
            "name a category list_fact_categories lists: " + ", ".join(sorted(categories)),
        )
    versions = contracts_from_entries(category_entries(wh, category))
    if not versions:
        raise FeedbackRefused(
            f"category {category!r} has no registry entry to stamp",
            "serve a file whose context_registry carries the category",
        )
    return versions


def typed_columns(wh: GoldWarehouse, category: str) -> list[str]:
    categories = {c["category"]: c for c in wh.list_fact_categories()["categories"]}
    return list(categories.get(category, {}).get("typed_columns") or [])


def category_tables(category: str) -> frozenset[str]:
    """The gold relations that carry a category's rows: its typed surface
    and its star tables."""
    return frozenset(
        {f"mart_{category}_typed", f"vw_{category}_typed", f"fact_{category}_values", f"dim_{category}_values", f"dim_{category}_columns"}
    )


def _first_line(exc: BaseException) -> str:
    return fold(str(exc).splitlines()[0]) if str(exc).strip() else type(exc).__name__


def _count(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    (count,) = con.execute(
        f"select count(*) from (select 1 as mm_one from (\n{sql}\n) as mm_rows limit {COUNT_CAP + 1}) as mm_count"
    ).fetchone()
    return int(count)


# ------------------------------------------------------------------ prepare


def prepare(wh: GoldWarehouse, field: str, kind: str, claim: str, query: str, server_version: str) -> Prepared:
    """Validate, measure, and stamp. Raises FeedbackRefused with the check
    that failed and its remedy; never writes."""
    if kind not in KINDS:
        raise FeedbackRefused(f"kind {kind!r} is outside the six", "use one of: " + ", ".join(KINDS))
    try:
        category, column = split_field(str(field).strip())
    except ValueError as exc:
        raise FeedbackRefused(str(exc), "write the field as <category>.<column>, lowercase") from exc
    contracts = category_contracts(wh, category)
    columns = typed_columns(wh, category)
    if kind == "missing_field":
        if column in columns:
            raise FeedbackRefused(
                f"missing_field names a column that exists: {column!r}",
                "for an existing column use meaning_unclear, meaning_wrong, unexpected_values, rule_wanted, or i_depend_on_this",
            )
    elif column not in columns:
        raise FeedbackRefused(
            f"{column!r} is not a typed column of {category}",
            "name one of: " + ", ".join(columns) + "; for a column that does not exist use missing_field",
        )
    folded = fold(str(claim))
    if not folded:
        raise FeedbackRefused("claim is empty", "say in a sentence what is wrong or wanted")
    if "@" in folded:
        raise FeedbackRefused(
            "claim carries an @ sign",
            "remove it; a feedback message is data and never addresses an account or a workflow",
        )
    if len(folded) > CLAIM_CAP:
        raise FeedbackRefused(f"claim is {len(folded)} characters, over {CLAIM_CAP}", "shorten the claim to at most 2000 characters")
    con = wh._con  # the hardened session the gates run on
    try:
        gate(query)
        scope_gate(con, query, wh.scope)
    except QueryRefused as exc:
        raise FeedbackRefused(f"query refused: {exc}", "write one SELECT over the served schema, as the query tool accepts") from exc
    tables, _ = statement_tables(con, query)
    named = {t[2].lower() for t in tables}
    if not named & category_tables(category):
        raise FeedbackRefused(
            f"the query names none of {category}'s tables",
            f"read the rows from gold.mart_{category}_typed (or the category's star tables), joins allowed",
        )
    reasons = aggregate_reasons(con, query)
    if reasons:
        raise FeedbackRefused(
            "the query is not the rows in question: " + "; ".join(reasons),
            "return the rows themselves, with no GROUP BY and no aggregate in an outermost SELECT; the server counts them",
        )
    volatile = volatile_calls(con, query)
    if volatile:
        raise FeedbackRefused(
            "the query calls a function whose result changes between runs: " + ", ".join(volatile),
            "write a deterministic query, so the producer's re-run counts the same rows",
        )
    canonical = canonical_sql(con, query)
    literals = query_literals(con, query)
    try:
        count = _count(con, canonical)
        original = _count(con, query.strip().rstrip(";"))
    except duckdb.Error as exc:
        raise FeedbackRefused(
            f"the query failed to run: {type(exc).__name__}: {_first_line(exc)}", "fix the query so it runs on the served file"
        ) from exc
    if count != original:
        raise FeedbackRefused(
            f"the query's canonical form counts {count} rows and its own text {original}",
            "write the query in a form DuckDB reads back the same way; the message carries the canonical form",
        )
    if count > COUNT_CAP:
        raise FeedbackRefused(f"the query matches more than {COUNT_CAP} rows", "narrow the query to the rows in question")
    sha, size = served_file_stamp(Path(wh.path))
    rows, md5 = registry_digest(con)
    return Prepared(
        field=f"{category}.{column}",
        kind=kind,
        claim=folded,
        query=canonical,
        rows_matching=count,
        contracts=contracts,
        served_file_sha256=sha,
        served_file_bytes=int(size),
        registry_rows=rows,
        registry_md5=md5,
        server_version=server_version,
        query_literals=literals,
    )


def render(p: Prepared) -> str:
    """The five parts first, in the layout's order, then the stamp and the
    labels as extra parts a strict reader reports and ignores."""
    versions = ", ".join(f"{name} {ver}" for name, ver in p.contracts.items())
    literals = ", ".join(p.query_literals) if p.query_literals else "none"
    lines = [
        FENCE_OPEN,
        f"field: {p.field}",
        f"kind: {p.kind}",
        f"claim: {p.claim}",
        f"query: {p.query}",
        f"rows matching: {p.rows_matching} at {versions}",
        f"served file: sha256 {p.served_file_sha256} ({p.served_file_bytes} bytes); "
        f"registry {p.registry_rows} rows md5 {p.registry_md5}; server {p.server_version}",
        f"query literals: {literals}",
        "caller supplied: claim and query, carried as given and checked only by the read-only gate",
        FENCE_CLOSE,
    ]
    return "\n".join(lines) + "\n"
