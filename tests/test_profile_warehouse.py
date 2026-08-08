"""Local smoke tests for the profiler over the real warehouse.

Marked `local`: they need the gitignored warehouse that only `make ingest`
(bronze) and `dbt build` (silver) produce, so CI deselects them with
-m "not local". Read-only per D-11; profiles are built in memory and no
artifact is written here. The silver pass runs the same code over the
silver schema (docs/spec/profiler.md §8, the gold-phase scope amendment).
"""

from pathlib import Path

import pytest

from metricmine.profiling.build import profile_table
from metricmine.profiling.canonical import canonical_bytes
from metricmine.warehouse.duckdb import DuckDBWarehouse

_WAREHOUSE = Path(__file__).resolve().parents[1] / "warehouse" / "metricmine.duckdb"

# The committed sample's row count (see tests/test_land_sample.py).
EXPECTED_ROWS = 45228

# Pinned observed measurements of the committed sample (6-dp rounded per
# the spec's float rule), not spec values; regressions in the rate
# computations fail here.
CUSTOMER_ID_NULL_RATE = 0.29778
DUPLICATE_ROW_RATE = 0.011188

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


# --- Silver pass (profiler spec §8; the mapping contract's evidence sheet) ---

# Pinned observed measurements of silver at contract v1.1.0 over the
# committed sample: 45,228 bronze rows - 506 exact-duplicate captures - 1
# clock-drift collapse = 44,721 lines (the conservation arithmetic).
SILVER_EXPECTED_ROWS = 44721


@pytest.fixture(scope="module")
def silver_artifact():
    if not _WAREHOUSE.is_file():
        pytest.skip(f"warehouse not built at {_WAREHOUSE}; run `make ingest` first")
    with DuckDBWarehouse(_WAREHOUSE) as warehouse:
        if "silver_invoice_lines" not in warehouse.list_tables("silver"):
            pytest.skip("silver not built; run dbt build first")
        return profile_table(warehouse, "silver", "silver_invoice_lines")


def test_silver_row_count_matches_conservation(silver_artifact):
    assert silver_artifact["dataset"]["row_count"] == SILVER_EXPECTED_ROWS


def test_silver_grain_holds_zero_duplicate_rate(silver_artifact):
    # The silver grain is contract-enforced with zero violations, so the
    # duplicate-row rate over the full column set must be exactly 0.0.
    assert silver_artifact["dataset"]["duplicate_row_rate"] == 0.0


def test_silver_two_runs_byte_identical(silver_artifact):
    with DuckDBWarehouse(_WAREHOUSE) as warehouse:
        second = profile_table(warehouse, "silver", "silver_invoice_lines")
    assert canonical_bytes(second) == canonical_bytes(silver_artifact)


def test_silver_temporal_range_present(silver_artifact):
    # Bronze's invoicedate lands VARCHAR, so its profile carries no
    # min/max (spec §3). Silver casts it TIMESTAMP; the silver profile is
    # where full date-range evidence first appears.
    cols = {c["name"]: c for c in silver_artifact["dataset"]["columns"]}
    assert "min" in cols["invoiced_at"] and "max" in cols["invoiced_at"]


def test_silver_carries_no_airbyte_columns(silver_artifact):
    names = [c["name"] for c in silver_artifact["dataset"]["columns"]]
    assert not any(n.startswith("_airbyte_") for n in names)
