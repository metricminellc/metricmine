"""Local smoke test for the bronze landing (docs/spec/ingestion.md §5).

Marked `local`: it inspects the gitignored working warehouse that only
`make ingest` produces, so CI deselects it with -m "not local". The test
never runs the pipeline itself — it asserts on the warehouse read-only,
matching acceptance criterion 3 (bronze is inspectable read-only).
"""

from pathlib import Path

import duckdb
import pytest

_WAREHOUSE = Path(__file__).resolve().parents[1] / "warehouse" / "metricmine.duckdb"

# The committed sample's row count: data rows in
# data/samples/online_retail_ii/online_retail_ii_2009-12.csv (header excluded).
EXPECTED_ROWS = 45228

pytestmark = pytest.mark.local


@pytest.fixture(scope="module")
def bronze():
    if not _WAREHOUSE.is_file():
        pytest.skip(f"warehouse not built at {_WAREHOUSE}; run `make ingest` first")
    con = duckdb.connect(str(_WAREHOUSE), read_only=True)
    yield con
    con.close()


def test_bronze_table_exists(bronze):
    tables = {
        row[0]
        for row in bronze.execute(
            "select table_name from information_schema.tables"
            " where table_schema = 'bronze'"
        ).fetchall()
    }
    assert "online_retail_ii" in tables


def test_row_count_matches_committed_sample(bronze):
    (count,) = bronze.execute(
        "select count(*) from bronze.online_retail_ii"
    ).fetchone()
    assert count == EXPECTED_ROWS


def test_airbyte_metadata_columns_present(bronze):
    columns = {
        row[0]
        for row in bronze.execute(
            "select column_name from information_schema.columns"
            " where table_schema = 'bronze' and table_name = 'online_retail_ii'"
        ).fetchall()
    }
    assert {"_airbyte_raw_id", "_airbyte_extracted_at"} <= columns
