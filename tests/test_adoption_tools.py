"""The deterministic adoption tools: verify-grain, enforce-properties,
and the relation_kinds protocol method (D-35, D-16 Amendment J, F-10,
F-27).

Everything here runs keyless against constructed fixtures under
tmp_path: a small DuckDB warehouse for the grain measurement and the
kinds mapping, and a sync-shaped properties file for the enforcement
helper. No model call, no network, no repo warehouse.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
import yaml

from metricmine.adoption import enforce_properties, verify_grain
from metricmine.warehouse.duckdb import DuckDBWarehouse

CONTRACT = {
    "apiVersion": "v3.1.0",
    "kind": "DataContract",
    "id": "silver_daily",
    "version": "1.0.0",
    "schema": [
        {
            "name": "silver_daily",
            "physicalType": "table",
            "properties": [
                {"name": "country", "physicalType": "VARCHAR", "required": True},
                {"name": "sales_date", "physicalType": "DATE", "required": True},
                {"name": "note", "physicalType": "VARCHAR", "required": False},
            ],
        }
    ],
}

SYNC_SHAPED_PROPERTIES = {
    "version": 2,
    "models": [
        {
            "name": "silver_daily",
            "description": "sync-created",
            "config": {
                "meta": {"datacontract_cli": {"contract_id": "silver_daily"}}
            },
            "columns": [
                {"name": "country", "data_type": "VARCHAR"},
                {"name": "sales_date", "data_type": "DATE"},
                {"name": "note", "data_type": "VARCHAR"},
            ],
        }
    ],
}


@pytest.fixture()
def repo_root(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "default.yaml").write_text(
        yaml.safe_dump(
            {"profiling": {"warehouse_path": "warehouse/w.duckdb"}}
        ),
        encoding="utf-8",
    )
    (tmp_path / "warehouse").mkdir()
    connection = duckdb.connect(str(tmp_path / "warehouse" / "w.duckdb"))
    connection.execute("create schema silver")
    connection.execute(
        "create table silver.silver_daily as select * from (values"
        " ('uk', date '2026-01-01', 1), ('uk', date '2026-01-02', 2),"
        " ('de', date '2026-01-01', 3)) t(country, sales_date, line_count)"
    )
    connection.execute(
        "create view silver.vw_daily as select * from silver.silver_daily"
    )
    connection.close()
    return tmp_path


def test_verify_grain_passes_on_the_unique_tuple(
    repo_root: Path, capsys: pytest.CaptureFixture
) -> None:
    code = verify_grain.run(
        repo_root, "silver_daily", ["country", "sales_date"]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "duplicate rows over ['country', 'sales_date']: 0" in out
    assert "duplicate rows over ['country']: 1" in out
    assert "verify-grain: PASS" in out


def test_verify_grain_fails_on_a_non_identifying_key(
    repo_root: Path, capsys: pytest.CaptureFixture
) -> None:
    code = verify_grain.run(repo_root, "silver_daily", ["country"])
    out = capsys.readouterr().out
    assert code == 1
    assert "verify-grain: FAIL (1 duplicate row(s)" in out


def test_verify_grain_names_a_missing_table_and_key(
    repo_root: Path, capsys: pytest.CaptureFixture
) -> None:
    assert verify_grain.run(repo_root, "silver_ghost", ["country"]) == 1
    assert "no relation silver.silver_ghost" in capsys.readouterr().err
    assert verify_grain.run(repo_root, "silver_daily", ["region"]) == 1
    assert "not columns of silver.silver_daily" in capsys.readouterr().err


def test_relation_kinds_tells_views_from_tables(repo_root: Path) -> None:
    with DuckDBWarehouse(repo_root / "warehouse" / "w.duckdb") as warehouse:
        kinds = warehouse.relation_kinds("silver")
    assert kinds == {"silver_daily": "table", "vw_daily": "view"}


@pytest.fixture()
def adoption_tree(repo_root: Path) -> Path:
    (repo_root / "contracts").mkdir()
    (repo_root / "contracts" / "silver_daily.odcs.yaml").write_text(
        yaml.safe_dump(CONTRACT, sort_keys=False), encoding="utf-8"
    )
    silver_dir = repo_root / "transform" / "models" / "silver"
    silver_dir.mkdir(parents=True)
    (silver_dir / "silver_daily.yml").write_text(
        yaml.safe_dump(SYNC_SHAPED_PROPERTIES, sort_keys=False),
        encoding="utf-8",
    )
    return repo_root


def test_enforce_properties_writes_only_the_two_keys(
    adoption_tree: Path, capsys: pytest.CaptureFixture
) -> None:
    code = enforce_properties.run(adoption_tree, "silver_daily")
    out = capsys.readouterr().out
    assert code == 0
    assert "config.contract.enforced: true" in out
    assert "columns.country.constraints: not_null" in out
    document = yaml.safe_load(
        (
            adoption_tree
            / "transform"
            / "models"
            / "silver"
            / "silver_daily.yml"
        ).read_text(encoding="utf-8")
    )
    model = document["models"][0]
    assert model["config"]["contract"]["enforced"] is True
    assert model["config"]["meta"]["datacontract_cli"]["contract_id"] == (
        "silver_daily"
    )
    constrained = {
        column["name"]
        for column in model["columns"]
        if {"type": "not_null"} in column.get("constraints", [])
    }
    assert constrained == {"country", "sales_date"}


def test_enforce_properties_is_idempotent(
    adoption_tree: Path, capsys: pytest.CaptureFixture
) -> None:
    assert enforce_properties.run(adoption_tree, "silver_daily") == 0
    path = (
        adoption_tree / "transform" / "models" / "silver" / "silver_daily.yml"
    )
    first = path.read_bytes()
    capsys.readouterr()
    assert enforce_properties.run(adoption_tree, "silver_daily") == 0
    assert "no changes" in capsys.readouterr().out
    assert path.read_bytes() == first


def test_enforce_properties_requires_the_synced_file(
    repo_root: Path, capsys: pytest.CaptureFixture
) -> None:
    (repo_root / "contracts").mkdir()
    (repo_root / "contracts" / "silver_daily.odcs.yaml").write_text(
        yaml.safe_dump(CONTRACT, sort_keys=False), encoding="utf-8"
    )
    assert enforce_properties.run(repo_root, "silver_daily") == 1
    assert "datacontract dbt sync" in capsys.readouterr().err


def test_enforce_properties_requires_the_approved_contract(
    repo_root: Path, capsys: pytest.CaptureFixture
) -> None:
    assert enforce_properties.run(repo_root, "silver_daily") == 1
    assert "no approved contract" in capsys.readouterr().err


def test_enforce_properties_names_a_missing_required_column(
    adoption_tree: Path, capsys: pytest.CaptureFixture
) -> None:
    path = (
        adoption_tree / "transform" / "models" / "silver" / "silver_daily.yml"
    )
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["models"][0]["columns"] = document["models"][0]["columns"][1:]
    path.write_text(
        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
    )
    assert enforce_properties.run(adoption_tree, "silver_daily") == 1
    assert "country" in capsys.readouterr().err
