"""Local conservation check for the silver dedup (contract v1.1.0).

Marked `local`: needs the gitignored warehouse (`make ingest`, then
`dbt build`). Pins the capture-artifact arithmetic the contract's
limitations text and the model header assert: bronze rows = silver rows +
exact-duplicate excess + clock-drift collapses. The distinct_source query
uses trim(description), matching the model's collapse basis exactly. The
identity assert documents the arithmetic; the pinned tuple is the
regression gate (a new sample window changes it deliberately, with the
contract).
"""

from pathlib import Path

import duckdb
import pytest

_WAREHOUSE = Path(__file__).resolve().parents[1] / "warehouse" / "metricmine.duckdb"

pytestmark = pytest.mark.local


@pytest.fixture(scope="module")
def con():
    if not _WAREHOUSE.is_file():
        pytest.skip(f"warehouse not built at {_WAREHOUSE}; run `make ingest` first")
    c = duckdb.connect(str(_WAREHOUSE), read_only=True)
    yield c
    c.close()


def test_conservation_bronze_to_silver(con):
    (bronze,) = con.execute(
        "select count(*) from bronze.online_retail_ii"
    ).fetchone()
    (silver,) = con.execute(
        "select count(*) from silver.silver_invoice_lines"
    ).fetchone()
    (distinct_source,) = con.execute(
        "select count(*) from (select distinct invoice, stockcode, quantity,"
        " price, invoicedate, trim(description), customer_id, country"
        " from bronze.online_retail_ii)"
    ).fetchone()
    exact_dup_excess = bronze - distinct_source
    clock_drift_collapses = distinct_source - silver
    assert bronze == silver + exact_dup_excess + clock_drift_collapses
    assert (bronze, silver, exact_dup_excess, clock_drift_collapses) == (
        45228,
        44721,
        506,
        1,
    )
