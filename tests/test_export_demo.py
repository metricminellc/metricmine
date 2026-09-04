"""Local-lane tests for the demo exporter against the built warehouse.

Marked `local`: they need the gitignored warehouse that `make ingest` and
`dbt build` produce, so CI deselects them with -m "not local". The census
is derived from the engine's configured categories (D-29 as amended at
the multi-source fan-in): three tables per category plus the seven shared
objects, one typed view per category; the retail fact's 44,721 rows are a
measurement of the committed sample, not a spec value. The export target
here is a temp path, never demo/demo.duckdb: the committed artifact is
built only by `make export-demo`.
"""

from pathlib import Path

import duckdb
import pytest

from metricmine.engine.emitters import StarEmission
from metricmine.engine.reader import load_inputs
from metricmine.export_demo import export, verify

_REPO = Path(__file__).resolve().parents[1]
_WAREHOUSE = _REPO / "warehouse" / "metricmine.duckdb"

FACT_ROWS = 44721
SHARED_TABLES = 7  # source, run, timeframe pairs plus the registry


def _categories() -> list[str]:
    inputs = load_inputs(_REPO)
    return [e.category_name for e in StarEmission(inputs.mappings, inputs.star).categories]


BASE_TABLES = SHARED_TABLES + 4 * len(_categories())  # dims, fact, mart per category
TYPED_VIEWS = [f"vw_{category}_typed" for category in _categories()]

pytestmark = pytest.mark.local


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    if not _WAREHOUSE.is_file():
        pytest.skip(f"warehouse not built at {_WAREHOUSE}; run `make ingest` first")
    # The stem is deliberately not `gold`: a dest named gold.duckdb
    # reproduces the F-25 catalog collision by construction.
    dest = tmp_path_factory.mktemp("demo") / "demo.duckdb"
    export(_WAREHOUSE, dest)
    return dest


def _census(dest: Path) -> dict[str, list[str]]:
    """Schema-qualified object names in the export, by table_type."""
    con = duckdb.connect(str(dest), read_only=True)
    try:
        rows = con.execute(
            "select table_schema, table_name, table_type"
            " from information_schema.tables order by table_schema, table_name"
        ).fetchall()
    finally:
        con.close()
    census: dict[str, list[str]] = {}
    for schema, name, table_type in rows:
        census.setdefault(table_type, []).append(f"{schema}.{name}")
    return census


def test_export_carries_gold_schema_only(exported):
    schemas = {
        qualified.split(".")[0]
        for names in _census(exported).values()
        for qualified in names
    }
    # No bronze, no silver, no main tables: the committed artifact carries
    # no raw data (D-03/D-15 posture).
    assert schemas == {"gold"}


def test_table_and_view_census(exported):
    census = _census(exported)
    assert len(census["BASE TABLE"]) == BASE_TABLES
    assert census["VIEW"] == [f"gold.{view}" for view in TYPED_VIEWS]


def test_verify_passes_end_to_end(exported):
    report = verify(_WAREHOUSE, exported)
    assert len(report["tables"]) == BASE_TABLES
    assert [v["view"] for v in report["views"]] == TYPED_VIEWS
    assert all(v["match"] for v in report["views"])
    fact_rows = {t["table"]: t["rows"] for t in report["tables"]}
    assert fact_rows["fact_invoice_lines_values"] == FACT_ROWS


def test_view_sql_is_reanchored(exported):
    con = duckdb.connect(str(exported), read_only=True)
    try:
        (sql,) = con.execute(
            "select sql from duckdb_views()"
            " where schema_name = 'gold' and view_name = ?",
            [TYPED_VIEWS[0]],
        ).fetchone()
    finally:
        con.close()
    # The source catalog qualifier fails verbatim in another catalog; the
    # exporter re-anchors it so the view resolves inside its own file.
    assert f"{_WAREHOUSE.stem}.gold." not in sql


def test_readonly_open_counts_and_refuses_writes(exported):
    con = duckdb.connect(str(exported), read_only=True)
    try:
        (count,) = con.execute(
            "select count(*) from gold.fact_invoice_lines_values"
        ).fetchone()
        assert count == FACT_ROWS
        with pytest.raises(duckdb.Error):
            con.execute(
                "insert into gold.context_registry select * from gold.context_registry"
            )
    finally:
        con.close()


def test_second_export_rebuilds_fresh(exported):
    export(_WAREHOUSE, exported)
    con = duckdb.connect(str(exported), read_only=True)
    try:
        (count,) = con.execute(
            "select count(*) from gold.fact_invoice_lines_values"
        ).fetchone()
    finally:
        con.close()
    # A rebuild over an existing dest starts fresh; an append would double.
    assert count == FACT_ROWS
