"""Unit surface for the context compiler and registry emission (spec §4; D-30).

CI-lane, keyless: everything runs from the committed contracts; no
warehouse, no network, and no committed compiled-context artifact is
required (the artifact-pinning manifest assertion lives in
test_engine_emission.py and arrives with the v1.2.0 amendment).

Interface under test (pinned at the Sitting J runbook; widened at the
multi-source fan-in, D-41, to any number of mapping contracts):
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
    StarEmission,
    context_json,
    registry_declared,
    registry_sql,
)
from metricmine.engine.reader import (
    EngineContractError,
    load_compiled_context,
    load_inputs,
    mapping_contract_paths,
)
from metricmine.profiling.canonical import canonical_bytes
from metricmine.profiling.writer import write_if_changed

REPO = Path(__file__).resolve().parents[1]

SHARED_GROUPS = ("source", "run", "timeframe")


def _star() -> StarEmission:
    inputs = load_inputs(REPO)
    return StarEmission(inputs.mappings, inputs.star)


def test_artifact_is_deterministic() -> None:
    """Two independent builds serialize byte-identically (D-30)."""
    first = canonical_bytes(build_compiled_context(REPO))
    second = canonical_bytes(build_compiled_context(REPO))
    assert first == second


def test_artifact_schema_keys_match_the_emitters() -> None:
    """One entry per schema key present in the star: the three shared
    groups first, then each category's dimensions and measures keys in
    category order, the same manifest_key literals the emitted models
    carry, so C3 passes by construction."""
    star = _star()
    artifact = build_compiled_context(REPO)
    expected_keys = [star.source_col_key, star.run_col_key, star.timeframe_col_key]
    expected_groups = list(SHARED_GROUPS)
    for emission in star.categories:
        expected_keys.extend([emission.dim_col_key, emission.fact_col_key])
        expected_groups.extend([emission.category["entityGroup"]] * 2)
    assert [entry["schema_key"] for entry in artifact["entries"]] == expected_keys
    assert [entry["entity_group"] for entry in artifact["entries"]] == expected_groups
    assert len(set(expected_keys)) == len(expected_keys), (
        "schema keys are the registry's primary key; a shared key appears once"
    )


def test_artifact_entries_cite_their_governing_contract() -> None:
    """Category rows cite the MAPPING contract whose approval created the
    keys; shared rows cite the star contract, which governs the
    container; every contract sits in sources, in category order."""
    inputs = load_inputs(REPO)
    star = _star()
    artifact = build_compiled_context(REPO)
    by_key = {entry["schema_key"]: entry for entry in artifact["entries"]}
    for key in (star.source_col_key, star.run_col_key, star.timeframe_col_key):
        assert by_key[key]["contract_name"] == inputs.star["id"]
        assert by_key[key]["contract_version"] == inputs.star["version"]
    for emission in star.categories:
        for key in (emission.dim_col_key, emission.fact_col_key):
            assert by_key[key]["contract_name"] == emission.mapping["id"]
            assert by_key[key]["contract_version"] == emission.mapping["version"]
    sources = artifact["sources"]
    assert sources["gold_contract"]["version"] == inputs.star["version"]
    assert [m["id"] for m in sources["mapping_contracts"]] == [
        emission.mapping["id"] for emission in star.categories
    ]
    assert len(sources["silver_contracts"]) == len(star.categories)
    for cited in sources["mapping_contracts"]:
        assert cited["profileHash"], (
            "each mapping contract's profileHash must be carried, honestly"
        )


def test_artifact_manifests_match_the_emitters() -> None:
    star = _star()
    artifact = build_compiled_context(REPO)
    manifests = [e["compiled_context"]["manifest"] for e in artifact["entries"]]
    expected = [star.source_manifest, star.run_manifest, star.timeframe_manifest]
    for emission in star.categories:
        expected.extend([emission.dim_manifest, emission.measure_manifest])
    assert manifests == expected


def test_timeframe_entry_is_the_conformed_calendar() -> None:
    """One timeframe row for the whole star (D-17 Amendment R): the fixed
    grain plus period_start manifest, and every category's declared time
    column and grain listed under it."""
    star = _star()
    artifact = build_compiled_context(REPO)
    timeframe = next(
        e["compiled_context"]
        for e in artifact["entries"]
        if e["compiled_context"]["role"] == "timeframe"
    )
    assert timeframe["manifest"] == ["grain", "period_start"]
    assert sorted(timeframe["fields"]) == ["grain", "period_start"]
    assert sorted(timeframe["categories"]) == [
        emission.category_name for emission in star.categories
    ]
    for emission in star.categories:
        listed = timeframe["categories"][emission.category_name]
        assert listed["time_column"] == emission.time_column
        assert listed["time_grain"] == emission.time_grain


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
    cfg["engine"]["mapping_contracts"] = [
        str(REPO / path) for path in mapping_contract_paths(cfg["engine"])
    ]
    cfg["engine"].pop("mapping_contract", None)
    for key in ("gold_contract", "schema_path"):
        cfg["engine"][key] = str(REPO / cfg["engine"][key])
    cfg["context"]["output_dir"] = str(compiled)
    (config / "default.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    # The reader resolves each silver contract under <repo>/contracts by
    # convention, so the mini repo carries the real ones.
    (tmp_path / "contracts").symlink_to(REPO / "contracts")
    return tmp_path


def test_missing_artifact_fails_closed(tmp_path) -> None:
    with pytest.raises(EngineContractError, match="make context"):
        load_compiled_context(_mini_repo(tmp_path, artifact=None))


def test_stale_artifact_fails_closed(tmp_path) -> None:
    """The staleness guard: the registry must never embed stale context."""
    artifact = build_compiled_context(REPO)
    artifact["sources"]["mapping_contracts"][0]["version"] = "0.0.1"
    with pytest.raises(EngineContractError, match="stale"):
        load_compiled_context(_mini_repo(tmp_path, artifact))


def test_current_artifact_loads(tmp_path) -> None:
    """The guard passes a freshly built artifact: the projection it
    compares (id plus version per contract) ignores the profileHash the
    artifact also carries."""
    artifact = build_compiled_context(REPO)
    version, loaded = load_compiled_context(_mini_repo(tmp_path, artifact))
    assert version == "v0001"
    assert loaded["entries"] == artifact["entries"]


def test_registry_sql_carries_the_artifact_verbatim() -> None:
    """Every schema key and every canonical compiled-context JSON text
    appears in the VALUES literals; the JSON round-trips."""
    star = _star()
    artifact = build_compiled_context(REPO)
    sql = registry_sql(star, artifact)
    for entry in artifact["entries"]:
        assert f"'{entry['schema_key']}'" in sql
        text = context_json(entry["compiled_context"])
        assert json.loads(text) == entry["compiled_context"]
        assert text.replace("'", "''") in sql


def test_registry_sql_doubles_single_quotes() -> None:
    star = _star()
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
    sql = registry_sql(star, compiled)
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
    """The registry pointer (D-31/D-32 as amended): every category's
    entries name the typed surface the serving layer prefers; the
    star-global groups carry none."""
    star = _star()
    artifact = build_compiled_context(REPO)
    for entry in artifact["entries"]:
        compiled = entry["compiled_context"]
        if compiled["role"] in ("dimensions", "measures"):
            assert compiled["typed_surface"] == f"mart_{compiled['category']}_typed"
        else:
            assert compiled["role"] in SHARED_GROUPS
            assert "typed_surface" not in compiled
    categories = {
        e["compiled_context"]["category"]
        for e in artifact["entries"]
        if e["compiled_context"]["role"] == "dimensions"
    }
    assert categories == {emission.category_name for emission in star.categories}
