"""CI-lane tests for the serving module: gate, cap clamp, db resolution.

No warehouse: everything here is pure. The matrix below is the probed
refusal set from the pre-L prep session (duckdb 1.4.3, August 13, 2026),
parametrized verbatim — same inputs, same expected verdicts. It is the
regression gate on docs/spec/serving.md §3, and the reason the leading-
keyword check exists: PRAGMA reads, SHOW, DESCRIBE, and SUMMARIZE are all
SELECT-typed by the parser, so they appear here as refusals that the type
check alone would have let through.
"""

from pathlib import Path

import pytest

from metricmine.query import (
    DEMO_DB,
    ENV_VAR,
    ROW_CAP_DEFAULT,
    ROW_CAP_MAX,
    GoldWarehouse,
    QueryRefused,
    clamp_row_cap,
    first_keyword,
    gate,
    resolve_db_path,
)

# (label, sql, should_pass) — the 29 probed cases.
CASES = [
    ("plain select", "SELECT 1", True),
    ("cte", "WITH x AS (SELECT 1 AS a) SELECT * FROM x", True),
    ("from-first", "FROM gold.context_registry LIMIT 1", True),
    ("comment then select", "-- note\nSELECT 1", True),
    ("block comment", "/* hi */ SELECT 1", True),
    ("attach", "ATTACH '/tmp/side.duckdb' AS side", False),
    ("copy", "COPY gold.context_registry TO '/tmp/x.csv'", False),
    ("pragma read", "PRAGMA database_list", False),
    ("pragma config", "PRAGMA memory_limit='1GB'", False),
    ("show", "SHOW TABLES", False),
    ("describe", "DESCRIBE gold.context_registry", False),
    ("summarize", "SUMMARIZE SELECT 1", False),
    ("explain", "EXPLAIN SELECT 1", False),
    ("install", "INSTALL httpfs", False),
    ("load", "LOAD httpfs", False),
    ("export", "EXPORT DATABASE '/tmp/x'", False),
    ("set", "SET enable_external_access=true", False),
    ("call", "CALL pragma_database_list()", False),
    ("insert", "INSERT INTO gold.context_registry VALUES (1)", False),
    ("update", "UPDATE gold.context_registry SET schema_key='x'", False),
    ("delete", "DELETE FROM gold.context_registry", False),
    ("create", "CREATE TABLE t (a INT)", False),
    ("drop", "DROP TABLE gold.context_registry", False),
    ("multi", "SELECT 1; SELECT 2", False),
    ("select-then-dml", "SELECT 1; DELETE FROM gold.context_registry", False),
    ("values", "VALUES (1, 2)", False),
    ("paren select", "(SELECT 1)", False),
    ("empty", "", False),
    ("garbage", "SELEKT 1", False),
]


@pytest.mark.parametrize(
    ("sql", "should_pass"),
    [(sql, ok) for _label, sql, ok in CASES],
    ids=[label for label, _sql, _ok in CASES],
)
def test_gate_matrix(sql, should_pass):
    if should_pass:
        gate(sql)
    else:
        with pytest.raises(QueryRefused):
            gate(sql)


def test_matrix_covers_the_probed_case_count():
    # The probe ran 29 cases and all 29 behaved as annotated; a case
    # silently dropped from this list would weaken the gate's evidence.
    assert len(CASES) == 29


# --- refusals name the check that failed (spec §3: "the message states
# which check failed") ---


def test_refusal_names_statement_count():
    with pytest.raises(QueryRefused, match="2 statements; exactly one required"):
        gate("SELECT 1; SELECT 2")


def test_refusal_names_statement_type():
    with pytest.raises(QueryRefused, match="statement type DELETE; SELECT required"):
        gate("DELETE FROM gold.context_registry")


def test_refusal_names_leading_keyword():
    with pytest.raises(QueryRefused, match="leading keyword 'pragma'"):
        gate("PRAGMA database_list")


def test_refusal_names_parse_error():
    with pytest.raises(QueryRefused, match="parse error"):
        gate("SELEKT 1")


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        ("SELECT 1", "select"),
        ("-- note\nSELECT 1", "select"),
        ("/* hi */ WITH x AS (SELECT 1) SELECT * FROM x", "with"),
        ("  \n FROM t", "from"),
        ("", ""),
        ("(SELECT 1)", ""),
    ],
)
def test_first_keyword_skips_comments(sql, expected):
    assert first_keyword(sql) == expected


# --- row caps (spec §4) ---


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        (0, 1),
        (-5, 1),
        (1, 1),
        (99, 99),
        (ROW_CAP_DEFAULT, 100),
        (ROW_CAP_MAX, 500),
        (501, 500),
        (10_000, 500),
    ],
)
def test_clamp_row_cap(requested, expected):
    assert clamp_row_cap(requested) == expected


# --- database resolution (spec §5) ---


def test_env_var_wins_over_the_demo_default(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "/somewhere/else.duckdb")
    assert resolve_db_path() == Path("/somewhere/else.duckdb")


def test_unset_env_falls_back_to_the_committed_demo_artifact(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert resolve_db_path() == DEMO_DB
    assert DEMO_DB.name == "gold.duckdb"
    assert DEMO_DB.parent.name == "demo"


def test_explicit_path_wins_over_the_env_var(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "/somewhere/else.duckdb")
    assert resolve_db_path("/explicit/here.duckdb") == Path("/explicit/here.duckdb")


def test_missing_database_fails_closed_naming_both_paths(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    missing = tmp_path / "missing.duckdb"
    with pytest.raises(FileNotFoundError) as excinfo:
        GoldWarehouse(missing)
    message = str(excinfo.value)
    assert str(missing) in message
    assert str(DEMO_DB) in message
    assert "make export-demo" in message


def test_fail_closed_message_reports_the_env_var_value(tmp_path, monkeypatch):
    missing = tmp_path / "pointed-nowhere.duckdb"
    monkeypatch.setenv(ENV_VAR, str(missing))
    with pytest.raises(FileNotFoundError, match=ENV_VAR):
        GoldWarehouse()
