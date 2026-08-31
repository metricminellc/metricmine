"""Unit surface for the context compiler and registry emission (spec §4; D-30).

CI-lane, keyless: everything runs from the committed contracts; no
warehouse, no network, and no committed compiled-context artifact is
required (the artifact-pinning manifest assertion lives in
test_engine_emission.py and arrives with the v1.2.0 amendment).

Interface under test (pinned at the Sitting J runbook):
- ``metricmine.context.compile.build_compiled_context(repo_root)``: pure;
  the artifact content dict.
- ``metricmine.profiling.canonical.canonical_bytes`` /
  ``metricmine.profiling.writer.write_if_changed``: the shared artifact
  discipline the compiler reuses (the mirror is exact by construction).
- ``metricmine.engine.reader.load_compiled_context``: newest committed
  vNNNN, fail-closed on absence and on staleness.
- ``metricmine.engine.emitters.registry_sql / registry_declared``: VALUES
  literals carried from the artifact; deterministic quote doubling.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from metricmine.context.compile import build_compiled_context
from metricmine.engine.emitters import (
    Emission,
    context_json,
    registry_declared,
    registry_sql,
)
from metricmine.engine.reader import (
    EngineContractError,
    load_compiled_context,
    load_inputs,
)
from metricmine.profiling.canonical import canonical_bytes
from metricmine.profiling.writer import write_if_changed

REPO = Path(__file__).resolve().parents[1]


def _emission() -> Emission:
    inputs = load_inputs(REPO)
    return Emission(inputs.mapping, inputs.star)


def test_artifact_is_deterministic() -> None:
    """Two independent builds serialize byte-identically (D-30)."""
    first = canonical_bytes(build_compiled_context(REPO))
    second = canonical_bytes(build_compiled_context(REPO))
    assert first == second


def test_artifact_schema_keys_match_the_emitters() -> None:
    """One entry per schema key present in the star, in fixed group
    order, the same manifest_key literals the emitted models carry, so
    C3 passes by construction."""
    emission = _emission()
    artifact = build_compiled_context(REPO)
    assert [entry["schema_key"] for entry in artifact["entries"]] == [
        emission.source_col_key,
        emission.run_col_key,
        emission.timeframe_col_key,
        emission.dim_col_key,
        emission.fact_col_key,
    ]
    assert [entry["entity_group"] for entry in artifact["entries"]] == [
        "source",
        "run",
        "timeframe",
        emission.category["entityGroup"],
        emission.category["entityGroup"],
    ]


def test_artifact_entries_cite_the_mapping_contract() -> None:
    """Every row cites the governing MAPPING contract (its approval
    created the keys); the star contract governs the container and is
    cited in sources."""
    inputs = load_inputs(REPO)
    artifact = build_compiled_context(REPO)
    for entry in artifact["entries"]:
        assert entry["contract_name"] == inputs.mapping["id"]
        assert entry["contract_version"] == inputs.mapping["version"]
    sources = artifact["sources"]
    assert sources["gold_contract"]["version"] == inputs.star["version"]
    assert sources["mapping_contract"]["version"] == inputs.mapping["version"]
    assert sources["silver_contract"]["version"] == inputs.silver["version"]
    assert sources["mapping_contract"]["profileHash"], (
        "the mapping contract's profileHash must be carried, honestly"
    )


def test_artifact_manifests_match_the_emitters() -> None:
    emission = _emission()
    artifact = build_compiled_context(REPO)
    manifests = [e["compiled_context"]["manifest"] for e in artifact["entries"]]
    assert manifests == [
        emission.source_manifest,
        emission.run_manifest,
        emission.timeframe_manifest,
        emission.dim_manifest,
        emission.measure_manifest,
    ]


def test_write_if_changed_is_a_no_op_on_unchanged_bytes(tmp_path) -> None:
    """The profiles/ discipline, inherited verbatim: second identical
    write mints nothing; changed bytes mint the next immutable vNNNN."""
    data = canonical_bytes(build_compiled_context(REPO))
    assert write_if_changed(tmp_path, data, {"probe": 1}).name == "v0001.json"
    assert write_if_changed(tmp_path, data, {"probe": 2}) is None
    changed = data + b"\n"
    assert write_if_changed(tmp_path, changed, {"probe": 3}).name == "v0002.json"


def _mini_repo(tmp_path: Path, artifact: dict | None) -> Path:
    """A tmp repo_root whose config points at the REAL contracts (absolute
    paths survive the reader's join) and at a tmp compiled dir."""
    compiled = tmp_path / "compiled"
    compiled.mkdir()
    if artifact is not None:
        (compiled / "v0001.json").write_bytes(canonical_bytes(artifact))
        (compiled / "v0001.meta.json").write_text("{}\n", encoding="utf-8")
    config = tmp_path / "config"
    config.mkdir()
    real = REPO / "config" / "default.yaml"
    import yaml

    cfg = yaml.safe_load(real.read_text(encoding="utf-8"))
    for key in ("mapping_contract", "gold_contract", "silver_contract", "schema_path"):
        cfg["engine"][key] = str(REPO / cfg["engine"][key])
    cfg["context"]["output_dir"] = str(compiled)
    (config / "default.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return tmp_path


def test_missing_artifact_fails_closed(tmp_path) -> None:
    with pytest.raises(EngineContractError, match="make context"):
        load_compiled_context(_mini_repo(tmp_path, artifact=None))


def test_stale_artifact_fails_closed(tmp_path) -> None:
    """The staleness guard: the registry must never embed stale context."""
    artifact = build_compiled_context(REPO)
    artifact["sources"]["mapping_contract"]["version"] = "0.0.1"
    with pytest.raises(EngineContractError, match="stale"):
        load_compiled_context(_mini_repo(tmp_path, artifact))


def test_registry_sql_carries_the_artifact_verbatim() -> None:
    """Every schema key and every canonical compiled-context JSON text
    appears in the VALUES literals; the JSON round-trips."""
    emission = _emission()
    artifact = build_compiled_context(REPO)
    sql = registry_sql(emission, artifact)
    for entry in artifact["entries"]:
        assert f"'{entry['schema_key']}'" in sql
        text = context_json(entry["compiled_context"])
        assert json.loads(text) == entry["compiled_context"]
        assert text.replace("'", "''") in sql


def test_registry_sql_doubles_single_quotes() -> None:
    emission = _emission()
    compiled = {
        "entries": [
            {
                "schema_key": "k",
                "entity_group": "g",
                "contract_name": "c",
                "contract_version": "1.0.0",
                "compiled_context": {"note": "it's quoted"},
            }
        ]
    }
    sql = registry_sql(emission, compiled)
    assert "it''s quoted" in sql
    assert "it's quoted" not in sql.replace("it''s", "")


def test_registry_declared_is_the_activation_switch() -> None:
    """State-independent: the switch reads the object catalog, nothing
    else, so this test holds before AND after the v1.2.0 amendment."""
    with_registry = {"schema": [{"name": "context_registry"}]}
    without = {"schema": [{"name": "dim_source_values"}]}
    assert registry_declared(with_registry) is True
    assert registry_declared(without) is False


def test_category_entries_carry_the_typed_surface_pointer() -> None:
    """The registry pointer (D-31/D-32 as amended): the category-group
    entries name the typed surface the serving layer prefers; the
    star-global groups carry none."""
    artifact = build_compiled_context(REPO)
    by_role = {
        entry["compiled_context"]["role"]: entry["compiled_context"]
        for entry in artifact["entries"]
    }
    assert by_role["dimensions"]["typed_surface"] == "mart_invoice_lines_typed"
    assert by_role["measures"]["typed_surface"] == "mart_invoice_lines_typed"
    for role in ("source", "run", "timeframe"):
        assert "typed_surface" not in by_role[role]
