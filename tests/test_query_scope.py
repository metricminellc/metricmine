"""The scope gate: `query` reads gold by default (D-31 as amended by
Amendment AB, HR-8), opt-in to the whole served file by MM_SERVE_SCOPE.

CI-lane, keyless: a small fixture file with a gold schema, a silver
schema, and a table in the default schema stands in for a working
warehouse, and `GoldWarehouse.query` runs against it under the real
session hardening, so every case below is measured through the served
path. The matrix pins what the parse tree exposes at duckdb 1.4.3: the
base tables a statement names, with their schemas, in every SELECT form
(CTE, subquery, join, EXISTS, scalar subquery, UNION, LATERAL, FROM-first,
DESCRIBE and SUMMARIZE inside a subquery, three-part names, quoting and
case); the names a common table expression introduces, which are not
base tables; and the table functions that evaluate a string as a table or
a statement, which no base-table check sees (F-72) and the gate refuses
by name.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from metricmine.query import (
    SCOPE_ALL,
    SCOPE_DENIED_TABLE_FUNCTIONS,
    SCOPE_ENV_VAR,
    SCOPE_GOLD,
    GoldWarehouse,
    QueryRefused,
    resolve_scope,
    statement_tables,
)

SERIALIZED_SILVER = (
    '{"error":false,"statements":[{"node":{"type":"SELECT_NODE","modifiers":[],"cte_map":{"map":[]},'
    '"select_list":[{"class":"STAR","type":"STAR","alias":"","query_location":7,"relation_name":"",'
    '"exclude_list":[],"replace_list":[],"rename_list":[],"columns":false,"expr":null,"unpacked":false}],'
    '"from_table":{"type":"BASE_TABLE","alias":"","sample":null,"query_location":14,"schema_name":"silver",'
    '"table_name":"s","column_name_alias":[],"catalog_name":""},"where_clause":null,"group_expressions":[],'
    '"group_sets":[],"aggregate_handling":"STANDARD_HANDLING","having":null,"sample":null,"qualify":null}}]}'
)


def _served_file(path: Path) -> Path:
    """A served file with three schemas' worth of rows: gold (two rows),
    silver (three rows), and a table in the default schema (one row)."""
    con = duckdb.connect(str(path))
    try:
        con.execute("create schema gold")
        con.execute("create schema silver")
        con.execute("create table gold.mart_t as select * from (values (1), (2)) t(x)")
        con.execute("create table silver.s as select * from (values (1), (2), (3)) t(x)")
        con.execute("create table main_t as select * from (values (9)) t(x)")
    finally:
        con.close()
    return path


@pytest.fixture(scope="module")
def served(tmp_path_factory) -> Path:
    return _served_file(tmp_path_factory.mktemp("scope") / "scope.duckdb")


@pytest.fixture(scope="module")
def gold(served: Path):
    with GoldWarehouse(served) as warehouse:
        yield warehouse


@pytest.fixture(scope="module")
def everything(tmp_path_factory):
    # Its own file: within one process DuckDB shares the database instance
    # behind one path, and the first connection's locked configuration
    # refuses the second's hardening (measured at 1.4.3 while writing this).
    with GoldWarehouse(_served_file(tmp_path_factory.mktemp("scope-all") / "scope.duckdb"), scope=SCOPE_ALL) as warehouse:
        yield warehouse


PASSES_UNDER_GOLD = [
    ("gold", "select count(*) from gold.mart_t", [[2]]),
    ("gold-upper", "select count(*) from GOLD.mart_t", [[2]]),
    ("gold-quoted", 'select count(*) from "gold"."mart_t"', [[2]]),
    ("gold-three-part", "select count(*) from scope.gold.mart_t", [[2]]),
    ("from-first", "from gold.mart_t select count(*)", [[2]]),
    ("cte-over-gold", "with t as (select x from gold.mart_t) select count(*) from t", [[2]]),
    ("cte-named-like-silver", "with s as (select x from gold.mart_t) select count(*) from s", [[2]]),
    ("subquery-gold", "select count(*) from (select x from gold.mart_t) q", [[2]]),
    ("describe-gold", "select count(*) from (describe gold.mart_t)", [[1]]),
    ("summarize-gold", "select count(*) from (summarize gold.mart_t)", [[1]]),
    ("no-table", "select 1 as one", [[1]]),
    ("range", "select count(*) from range(3)", [[3]]),
    ("pragma-fn", "select count(*) from pragma_version()", [[1]]),
    ("show-tables", "select count(*) >= 1 as some from (show tables)", [[True]]),
    ("metadata-fn", "select count(*) >= 3 as some from duckdb_tables()", [[True]]),
    ("table-info-gold", "select count(*) from pragma_table_info('gold.mart_t')", [[1]]),
    ("pivot-in-list-gold", "select count(*) from (pivot gold.mart_t on x in (1, 2) using count(*))", [[1]]),
    ("recursive-cte", "with recursive r as (select 1 as n union all select n + 1 from r where n < 3) select count(*) from r", [[3]]),
    ("later-cte-reads-earlier", "with a as (select x from gold.mart_t), b as (select x from a) select count(*) from b", [[2]]),
]

REFUSED_UNDER_GOLD = [
    ("silver", "select count(*) from silver.s", "'silver.s' is outside the gold schema"),
    ("silver-upper", "select count(*) from SILVER.s", "'SILVER.s' is outside the gold schema"),
    ("silver-quoted", 'select count(*) from "silver"."s"', "'silver.s' is outside"),
    ("silver-three-part", "select count(*) from scope.silver.s", "'scope.silver.s' is outside"),
    ("bare-name", "select count(*) from main_t", "'main_t' names no schema; name a gold table as gold.main_t"),
    ("information-schema", "select count(*) from information_schema.tables", "'information_schema.tables' is outside"),
    ("cte-body-silver", "with t as (select x from silver.s) select count(*) from t", "'silver.s' is outside"),
    ("cte-shadows-gold", "with mart_t as (select x from silver.s) select count(*) from mart_t", "'silver.s' is outside"),
    ("subquery-silver", "select count(*) from (select x from silver.s) q", "'silver.s' is outside"),
    ("join-silver", "select count(*) from gold.mart_t g join silver.s s on g.x = s.x", "'silver.s' is outside"),
    ("exists-silver", "select 1 where exists (select 1 from silver.s)", "'silver.s' is outside"),
    ("scalar-subquery-silver", "select (select count(*) from silver.s) as n", "'silver.s' is outside"),
    ("union-silver", "select x from gold.mart_t union all select x from silver.s", "'silver.s' is outside"),
    ("lateral-silver", "select * from gold.mart_t g, lateral (select count(*) from silver.s s where s.x = g.x) l", "'silver.s' is outside"),
    ("describe-silver", "select count(*) from (describe silver.s)", "'silver.s' is outside"),
    ("summarize-silver", "select count(*) from (summarize silver.s)", "'silver.s' is outside"),
    ("from-first-silver", "from silver.s select count(*)", "'silver.s' is outside"),
    ("query_table", "select count(*) from query_table('silver.s')", "query_table() takes a table's name"),
    ("query_table-list", "select count(*) from query_table(['silver.s'])", "query_table() takes a table's name"),
    ("query-fn", "select count(*) from query('select * from silver.s')", "query() takes a table's name"),
    ("query_table-gold", "select count(*) from query_table('gold.mart_t')", "query_table() takes a table's name"),
    ("table-sample", "select * from duckdb_table_sample('silver.s')", "duckdb_table_sample() takes a table's name"),
    ("storage-info", "select stats from pragma_storage_info('silver.s')", "pragma_storage_info() takes a table's name"),
    ("cte-shadows-its-own-source", "with main_t as (select * from main_t) select count(*) from main_t", "'main_t' names no schema"),
    ("cte-shadows-a-silver-source", "with s as (select * from silver.s) select count(*) from s", "'silver.s' is outside"),
    ("pivot-in-list-silver", "select count(*) from (pivot silver.s on x in (1, 2) using count(*))", "'silver.s' is outside"),
    ("pivot-standard-silver", "select * from silver.s pivot (count(*) for x in (1, 2))", "'silver.s' is outside"),
    (
        "serialized-sql",
        "select * from json_execute_serialized_sql('" + SERIALIZED_SILVER.replace("'", "''") + "')",
        "json_execute_serialized_sql() takes a table's name",
    ),
]


@pytest.mark.parametrize("sql,rows", [(c[1], c[2]) for c in PASSES_UNDER_GOLD], ids=[c[0] for c in PASSES_UNDER_GOLD])
def test_gold_scope_passes_gold_and_table_functions_that_read_no_rows(gold, sql, rows):
    assert gold.query(sql)["rows"] == rows


@pytest.mark.parametrize("sql,reason", [(c[1], c[2]) for c in REFUSED_UNDER_GOLD], ids=[c[0] for c in REFUSED_UNDER_GOLD])
def test_gold_scope_refuses_every_other_reach_naming_it_and_the_opt_in(gold, sql, reason):
    with pytest.raises(QueryRefused) as refused:
        gold.query(sql)
    message = str(refused.value)
    assert message.startswith("scope: ")
    assert reason in message, message
    assert f"{SCOPE_ENV_VAR}={SCOPE_ALL}" in message


def test_the_matrix_covers_the_measured_case_count():
    """Nineteen passes and twenty-eight refusals, measured on October 19,
    2026 at duckdb 1.4.3 (the probe transcript); a case added or removed
    is a deliberate change to the spec's matrix."""
    assert len(PASSES_UNDER_GOLD) == 19
    assert len(REFUSED_UNDER_GOLD) == 28


def test_a_pivot_without_an_in_list_never_reaches_the_scope_gate(gold):
    """Measured at 1.4.3: DuckDB's parser desugars a PIVOT with no IN list
    into two statements, so the statement gate refuses it first; a PIVOT
    with an IN list is one statement whose source the scope gate reads
    (the two pivot cases in the matrix)."""
    with pytest.raises(QueryRefused, match="2 statements; exactly one required"):
        gold.query("select count(*) from (pivot gold.mart_t on x using count(*))")


def test_a_statement_the_parser_cannot_serialize_is_refused_not_passed():
    """The fail-closed branch: no lone gated SELECT measured at 1.4.3
    fails `json_serialize_sql`, so the branch is held with a stand-in
    connection that answers as the parser would on such a statement."""

    class Cursor:
        def fetchone(self):
            return ('{"error":true,"error_type":"not implemented","error_message":"stand-in"}',)

    class Connection:
        def execute(self, sql, params=None):
            return Cursor()

    with pytest.raises(QueryRefused, match="scope: the statement's tables could not be read from its parse tree"):
        statement_tables(Connection(), "select 1")


def test_all_scope_reaches_every_schema_in_the_served_file(everything):
    assert everything.query("select count(*) from silver.s")["rows"] == [[3]]
    assert everything.query("select count(*) from main_t")["rows"] == [[1]]
    assert everything.query("select count(*) from query_table('silver.s')")["rows"] == [[3]]
    assert everything.query("select count(*) from gold.mart_t")["rows"] == [[2]]


def test_the_statement_gate_still_runs_first_under_every_scope(gold, everything):
    for warehouse in (gold, everything):
        with pytest.raises(QueryRefused, match="SELECT required"):
            warehouse.query("DELETE FROM gold.mart_t")
        with pytest.raises(QueryRefused, match="exactly one required"):
            warehouse.query("select 1; select 2")


def test_statement_tables_drops_cte_references_in_scope_and_lists_the_functions(gold):
    tables, functions = statement_tables(
        gold._con, "with t as (select x from gold.mart_t) select count(*) from t, range(2), query_table('silver.s')"
    )
    assert tables == [("", "gold", "mart_t")]
    assert functions == ["range", "query_table"]
    # A CTE's own name is out of scope inside its body unless it is
    # recursive, so the inner reference is a base table.
    tables, _ = statement_tables(gold._con, "with main_t as (select * from main_t) select count(*) from main_t")
    assert tables == [("", "", "main_t")]
    tables, _ = statement_tables(gold._con, "with recursive r as (select 1 as n union all select n + 1 from r where n < 3) select count(*) from r")
    assert tables == []


def test_the_denied_functions_are_the_measured_five():
    assert SCOPE_DENIED_TABLE_FUNCTIONS == {
        "query", "query_table", "json_execute_serialized_sql", "duckdb_table_sample", "pragma_storage_info",
    }


# ---------------------------------------------------------------- resolution, at startup


def test_scope_defaults_to_gold(monkeypatch):
    monkeypatch.delenv(SCOPE_ENV_VAR, raising=False)
    assert resolve_scope() == SCOPE_GOLD


def test_scope_reads_the_environment(monkeypatch):
    monkeypatch.setenv(SCOPE_ENV_VAR, SCOPE_ALL)
    assert resolve_scope() == SCOPE_ALL
    monkeypatch.setenv(SCOPE_ENV_VAR, SCOPE_GOLD)
    assert resolve_scope() == SCOPE_GOLD
    monkeypatch.setenv(SCOPE_ENV_VAR, "")
    assert resolve_scope() == SCOPE_GOLD


def test_an_explicit_scope_wins_over_the_environment(monkeypatch):
    monkeypatch.setenv(SCOPE_ENV_VAR, SCOPE_ALL)
    assert resolve_scope(SCOPE_GOLD) == SCOPE_GOLD


def test_an_unknown_scope_fails_closed_at_startup(served: Path, monkeypatch):
    monkeypatch.setenv(SCOPE_ENV_VAR, "silver")
    with pytest.raises(ValueError, match="MM_SERVE_SCOPE='silver' is not a scope; use 'gold'"):
        GoldWarehouse(served)
    with pytest.raises(ValueError, match="is not a scope"):
        GoldWarehouse(served, scope="everything")
