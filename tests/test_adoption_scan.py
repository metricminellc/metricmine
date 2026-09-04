"""The adoption scan: every state, the fixed orders, and the stable
plan hash (D-35).

A constructed miniature repository under tmp_path exercises the state
machine end to end without the project warehouse: a silver model walked
through adopt, unenforced, and in_sync; drift flavors for amend and
contract_ahead; the jurisdiction skips (engine-owned gold, foreign
gold, a view, an unknown layer); and the mapping contract listed as an
engine input, never a model. The plan hash is proven stable across
runs and across a mutate-and-revert cycle. Keyless, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest
import yaml

from metricmine.adoption import scan

DBT_PROJECT = {
    "name": "metricmine",
    "models": {
        "metricmine": {
            "silver": {"+materialized": "table", "+schema": "silver"},
            "gold": {"+materialized": "table", "+schema": "gold"},
        }
    },
}

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
                {"name": "line_count", "physicalType": "BIGINT", "required": True},
            ],
        }
    ],
}

MAPPING_CONTRACT = {
    "apiVersion": "v3.1.0",
    "kind": "DataContract",
    "id": "gold_daily_mapping",
    "version": "1.0.0",
    "schema": [
        {
            "name": "daily",
            "physicalType": "mapping",
            "sourceTable": "silver.silver_daily",
            "properties": [],
        }
    ],
}

PROFILE = {
    "schema_version": "1.0.0",
    "content_hash": "sha256:" + "0" * 64,
    "dataset": {
        "schema": "silver",
        "table": "silver_daily",
        "row_count": 3,
        "duplicate_row_rate": 0.0,
        "columns": [
            {"name": "country", "physical_type": "VARCHAR", "null_rate": 0.0},
            {"name": "sales_date", "physical_type": "DATE", "null_rate": 0.0},
            {"name": "line_count", "physical_type": "BIGINT", "null_rate": 0.0},
        ],
    },
}


def _write_yaml(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    _write_yaml(tmp_path / "transform" / "dbt_project.yml", DBT_PROJECT)
    _write_yaml(
        tmp_path / "config" / "default.yaml",
        {
            "profiling": {
                "warehouse_path": "warehouse/w.duckdb",
                "targets": [{"schema": "silver", "table": "silver_daily"}],
            }
        },
    )
    models = tmp_path / "transform" / "models"
    (models / "silver").mkdir(parents=True)
    (models / "silver" / "silver_daily.sql").write_text(
        "select 1", encoding="utf-8"
    )
    (models / "gold").mkdir()
    (models / "gold" / "fact_owned_values.sql").write_text(
        "select 1", encoding="utf-8"
    )
    (models / "gold" / "mart_foreign_revenue.sql").write_text(
        "select 1", encoding="utf-8"
    )
    (models / "gold" / "ownership-manifest.json").write_text(
        json.dumps(
            {"files": {"transform/models/gold/fact_owned_values.sql": "x"}}
        ),
        encoding="utf-8",
    )
    (models / "silver" / "vw_projection.sql").write_text(
        "{{ config(materialized='view') }} select 1", encoding="utf-8"
    )
    (models / "docs_layer").mkdir()
    (models / "docs_layer" / "note_model.sql").write_text(
        "select 1", encoding="utf-8"
    )
    _write_yaml(
        tmp_path / "contracts" / "gold_daily_mapping.odcs.yaml",
        MAPPING_CONTRACT,
    )
    (tmp_path / "warehouse").mkdir()
    connection = duckdb.connect(str(tmp_path / "warehouse" / "w.duckdb"))
    connection.execute("create schema silver")
    connection.execute("create schema gold")
    connection.execute("create schema bronze")
    connection.execute(
        "create table silver.silver_daily as select country, sales_date,"
        " cast(line_count as bigint) as line_count from (values"
        " ('uk', date '2026-01-01', 1), ('de', date '2026-01-01', 2),"
        " ('uk', date '2026-01-02', 3))"
        " t(country, sales_date, line_count)"
    )
    connection.execute("create table gold.fact_owned_values as select 1 a")
    connection.execute(
        "create table gold.mart_foreign_revenue as select 1 a"
    )
    connection.close()
    return tmp_path


def _states(repo_root: Path) -> dict[str, str]:
    return {
        model["name"]: model["state"]
        for model in scan.inventory(repo_root)["models"]
    }


def test_the_jurisdiction_and_layer_skips(repo: Path) -> None:
    states = _states(repo)
    assert states["fact_owned_values"] == "skip_engine_owned"
    assert states["mart_foreign_revenue"] == "skip_foreign_gold"
    assert states["vw_projection"] == "skip_view"
    assert states["note_model"] == "skip_unknown_layer"


def test_foreign_gold_is_reported_never_queued(repo: Path) -> None:
    inv = scan.inventory(repo)
    foreign = next(
        model
        for model in inv["models"]
        if model["name"] == "mart_foreign_revenue"
    )
    assert "never adopted" in foreign["reason"]
    assert "rule 12" in foreign["reason"]
    body = scan.render_md(repo, inv, "testhead")
    queue_section = body.split("## The queue")[1].split("## Skipped")[0]
    assert "mart_foreign_revenue" not in queue_section


def test_a_silver_model_walks_the_adoption_states(repo: Path) -> None:
    assert _states(repo)["silver_daily"] == "needs_profile"
    profile_dir = repo / "profiles" / "silver.silver_daily"
    profile_dir.mkdir(parents=True)
    _write_yaml(profile_dir / "v0001.json", PROFILE)
    (profile_dir / "v0001.json").write_text(
        json.dumps(PROFILE), encoding="utf-8"
    )
    assert _states(repo)["silver_daily"] == "adopt"
    _write_yaml(repo / "contracts" / "silver_daily.odcs.yaml", CONTRACT)
    assert _states(repo)["silver_daily"] == "unenforced"
    _write_yaml(
        repo / "transform" / "models" / "silver" / "silver_daily.yml",
        {
            "version": 2,
            "models": [
                {
                    "name": "silver_daily",
                    "config": {
                        "contract": {"enforced": True},
                        "meta": {
                            "datacontract_cli": {
                                "contract_id": "silver_daily"
                            }
                        },
                    },
                }
            ],
        },
    )
    assert _states(repo)["silver_daily"] == "in_sync"


def _adopted(repo: Path) -> Path:
    profile_dir = repo / "profiles" / "silver.silver_daily"
    profile_dir.mkdir(parents=True)
    (profile_dir / "v0001.json").write_text(
        json.dumps(PROFILE), encoding="utf-8"
    )
    _write_yaml(repo / "contracts" / "silver_daily.odcs.yaml", CONTRACT)
    return repo / "contracts" / "silver_daily.odcs.yaml"


def test_contract_ahead_outranks_amend(repo: Path) -> None:
    contract_path = _adopted(repo)
    document = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    document["schema"][0]["properties"].append(
        {"name": "avg_price", "physicalType": "DECIMAL(38,6)", "required": True}
    )
    _write_yaml(contract_path, document)
    inv = scan.inventory(repo)
    model = next(m for m in inv["models"] if m["name"] == "silver_daily")
    assert model["state"] == "contract_ahead"
    assert "avg_price" in model["reason"]
    assert "model change pending" in model["next_command"]


def test_type_drift_reads_amend(repo: Path) -> None:
    contract_path = _adopted(repo)
    document = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    document["schema"][0]["properties"][2]["physicalType"] = "INTEGER"
    _write_yaml(contract_path, document)
    inv = scan.inventory(repo)
    model = next(m for m in inv["models"] if m["name"] == "silver_daily")
    assert model["state"] == "amend"
    assert "line_count" in model["reason"]
    assert "propose-amend" in model["next_command"]


def test_missing_relation_reads_needs_build(repo: Path) -> None:
    (
        repo / "transform" / "models" / "silver" / "silver_unbuilt.sql"
    ).write_text("select 1", encoding="utf-8")
    states = _states(repo)
    assert states["silver_unbuilt"] == "needs_build"


def test_mapping_contracts_are_engine_inputs_never_models(repo: Path) -> None:
    inv = scan.inventory(repo)
    assert [entry["id"] for entry in inv["mapping_contracts"]] == [
        "gold_daily_mapping"
    ]
    assert "gold_daily_mapping" not in {
        model["name"] for model in inv["models"]
    }
    body = scan.render_md(repo, inv, "testhead")
    assert "Engine inputs, not models" in body
    assert "no physical table ever carries this name" in body


def test_views_report_no_row_count(repo: Path) -> None:
    connection = duckdb.connect(str(repo / "warehouse" / "w.duckdb"))
    connection.execute(
        "create view silver.vw_projection as select * from"
        " silver.silver_daily"
    )
    connection.close()
    inv = scan.inventory(repo)
    view = next(m for m in inv["models"] if m["name"] == "vw_projection")
    assert view["relation"]["type"] == "view"
    assert view["relation"]["row_count"] is None


def test_plan_hash_is_stable_and_returns_after_revert(repo: Path) -> None:
    contract_path = _adopted(repo)
    baseline = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    body_one = scan.render_md(repo, scan.inventory(repo), "fixedhead")
    body_two = scan.render_md(repo, scan.inventory(repo), "fixedhead")
    assert body_one == body_two
    original_hash = scan._sha256_text(body_one)
    mutated = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    mutated["schema"][0]["properties"][0]["physicalType"] = "TEXT"
    _write_yaml(contract_path, mutated)
    drifted = scan._sha256_text(
        scan.render_md(repo, scan.inventory(repo), "fixedhead")
    )
    assert drifted != original_hash
    _write_yaml(contract_path, baseline)
    reverted = scan._sha256_text(
        scan.render_md(repo, scan.inventory(repo), "fixedhead")
    )
    assert reverted == original_hash


def test_run_writes_the_plan_pair_with_the_hash(repo: Path) -> None:
    _adopted(repo)
    assert scan.run(repo) == 0
    runs = sorted((repo / "proposals" / "scan").iterdir())
    assert len(runs) == 1
    plan = json.loads((runs[0] / "plan.json").read_text(encoding="utf-8"))
    body = (runs[0] / "plan.md").read_text(encoding="utf-8")
    assert plan["plan_hash"] in body
    assert plan["counts"]["unenforced"] == 1
    assert plan["counts"]["skip_foreign_gold"] == 1
    assert "generated_at" in plan
    assert plan["generated_at"] not in body


@pytest.mark.local
def test_the_committed_repository_scans_clean() -> None:
    # The repo at head: every mapped silver model in sync, every
    # engine-owned gold model skipped (the marts and views included), an
    # empty queue, and every mapping contract listed as an engine input.
    # Counts derive from the engine's configured categories (D-29 as
    # amended at the multi-source fan-in). Local: needs the built
    # warehouse.
    from metricmine.engine.emitters import StarEmission
    from metricmine.engine.reader import load_inputs

    repo_root = Path(__file__).resolve().parents[1]
    inputs = load_inputs(repo_root)
    star = StarEmission(inputs.mappings, inputs.star)
    categories = [e.category_name for e in star.categories]
    silver_models = sorted(e.source_model for e in star.categories)
    inv = scan.inventory(repo_root)
    states = {model["name"]: model["state"] for model in inv["models"]}
    engine_owned = sorted(
        name for name, state in states.items() if state == "skip_engine_owned"
    )
    # Per category: values and columns dims, the fact, the mart, the view;
    # once: the three shared pairs and the registry.
    assert len(engine_owned) == 7 + 5 * len(categories)
    for category in categories:
        assert f"mart_{category}_typed" in engine_owned
        assert f"vw_{category}_typed" in engine_owned
    for model in silver_models:
        assert states[model] == "in_sync", (model, states[model])
    assert len(states) == len(engine_owned) + len(
        [name for name in states if name not in engine_owned]
    )
    queued = [
        model for model in inv["models"] if model["state"] in scan.QUEUE_ORDER
    ]
    assert queued == []
    assert sorted(entry["id"] for entry in inv["mapping_contracts"]) == sorted(
        e.mapping["id"] for e in star.categories
    )
