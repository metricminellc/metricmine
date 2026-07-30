"""Local smoke test for the profiler over the real warehouse.

Marked `local`: it needs the gitignored warehouse that only `make ingest`
produces, so CI deselects it with -m "not local". Read-only per D-11; the
profile is built in memory and no artifact is written here.
"""

from pathlib import Path

import pytest

from metricmine.profiling.build import profile_table
from metricmine.profiling.canonical import canonical_bytes
from metricmine.warehouse.duckdb import DuckDBWarehouse

_WAREHOUSE = Path(__file__).resolve().parents[1] / "warehouse" / "metricmine.duckdb"

# The committed sample's row count (see tests/test_land_sample.py).
EXPECTED_ROWS = 45228

# TODO: pin after the first real `make profile` run mints v0001. These are
# observed measurements of the committed sample, not spec values; None
# skips the assertion until they are pinned.
CUSTOMER_ID_NULL_RATE = None
DUPLICATE_ROW_RATE = None

pytestmark = pytest.mark.local


@pytest.fixture(scope="module")
def artifact():
    if not _WAREHOUSE.is_file():
        pytest.skip(f"warehouse not built at {_WAREHOUSE}; run `make ingest` first")
    with DuckDBWarehouse(_WAREHOUSE) as warehouse:
        return profile_table(warehouse, "bronze", "online_retail_ii")


def test_row_count_matches_committed_sample(artifact):
    assert artifact["dataset"]["row_count"] == EXPECTED_ROWS


def test_two_runs_byte_identical(artifact):
    with DuckDBWarehouse(_WAREHOUSE) as warehouse:
        second = profile_table(warehouse, "bronze", "online_retail_ii")
    assert canonical_bytes(second) == canonical_bytes(artifact)


def test_airbyte_columns_flagged(artifact):
    cols = {c["name"]: c for c in artifact["dataset"]["columns"]}
    assert cols["_airbyte_raw_id"]["is_airbyte_metadata"] is True
    assert cols["invoice"]["is_airbyte_metadata"] is False


def test_pinned_measurements(artifact):
    cols = {c["name"]: c for c in artifact["dataset"]["columns"]}
    if CUSTOMER_ID_NULL_RATE is not None:
        assert cols["customer_id"]["null_rate"] == CUSTOMER_ID_NULL_RATE
    if DUPLICATE_ROW_RATE is not None:
        assert artifact["dataset"]["duplicate_row_rate"] == DUPLICATE_ROW_RATE
