"""CI-surface end-to-end profile over a tiny tmp_path DuckDB.

Exercises DuckDBWarehouse and profile_table against a table with known
nulls and known duplicate rows (docs/spec/profiler.md §3). read_only=True
cannot open :memory:, so the table is file-backed in tmp_path: built
writable by plain duckdb.connect in test setup only, then profiled
strictly read-only through the warehouse class.
"""

import duckdb
import pytest

from metricmine.profiling.build import profile_table
from metricmine.profiling.canonical import canonical_bytes
from metricmine.warehouse.duckdb import DuckDBWarehouse


@pytest.fixture(scope="module")
def tiny_db(tmp_path_factory):
    db = tmp_path_factory.mktemp("wh") / "tiny.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create schema bronze")
    con.execute("create table bronze.t (a integer, b varchar, _airbyte_x varchar)")
    # 5 rows; source columns (a, b) hold one exact duplicate pair.
    con.execute(
        "insert into bronze.t values"
        " (1, 'x', 'r1'), (1, 'x', 'r2'), (2, NULL, 'r3'),"
        " (3, 'y', 'r4'), (NULL, 'y', 'r5')"
    )
    con.close()
    return db


@pytest.fixture(scope="module")
def artifact(tiny_db):
    with DuckDBWarehouse(tiny_db) as warehouse:
        return profile_table(warehouse, "bronze", "t")


def test_row_count_and_duplicate_rate(artifact):
    dataset = artifact["dataset"]
    assert dataset["row_count"] == 5
    # (5 rows - 4 distinct (a, b) rows) / 5; _airbyte_x excluded, else the
    # r1..r5 values would make every row unique.
    assert dataset["duplicate_row_rate"] == 0.2


def test_column_order_is_ordinal(artifact):
    names = [c["name"] for c in artifact["dataset"]["columns"]]
    assert names == ["a", "b", "_airbyte_x"]


def test_exact_column_stats(artifact):
    cols = {c["name"]: c for c in artifact["dataset"]["columns"]}
    a = cols["a"]
    assert a["null_count"] == 1
    assert a["null_rate"] == 0.2
    assert a["distinct_count"] == 3
    assert a["min"] == 1 and a["max"] == 3
    assert a["distinct_values"] == [1, 2, 3]
    assert "sample_values" not in a

    b = cols["b"]
    assert b["null_count"] == 1
    assert b["distinct_count"] == 2
    assert b["distinct_values"] == ["x", "y"]
    assert "min" not in b and "max" not in b
    assert b["is_airbyte_metadata"] is False

    airbyte = cols["_airbyte_x"]
    assert airbyte["is_airbyte_metadata"] is True
    assert airbyte["distinct_count"] == 5


def test_two_serializations_byte_identical(tiny_db, artifact):
    with DuckDBWarehouse(tiny_db) as warehouse:
        second = profile_table(warehouse, "bronze", "t")
    assert canonical_bytes(second) == canonical_bytes(artifact)


def test_warehouse_is_read_only(tiny_db):
    with DuckDBWarehouse(tiny_db) as warehouse:
        with pytest.raises(duckdb.Error):
            warehouse._con.execute("insert into bronze.t values (9, 'z', 'r9')")
