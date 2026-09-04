"""CI-surface tests for the profiling config block.

Network-free and warehouse-free: they pin the shape of
config/default.yaml's profiling block after the silver-pass scope
amendment (docs/spec/profiler.md §8), a list of targets, one artifact
directory per table, without opening any warehouse. The end-to-end
profile runs stay local (`make profile` + the local-marked smoke tests).
"""

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _profiling_cfg() -> dict:
    return yaml.safe_load((_REPO_ROOT / "config" / "default.yaml").read_text())[
        "profiling"
    ]


def test_config_profiling_block_shape():
    cfg = _profiling_cfg()
    assert cfg["warehouse_path"] == "warehouse/metricmine.duckdb"
    assert cfg["output_dir"] == "profiles"
    assert isinstance(cfg["targets"], list)


def test_config_profiling_targets():
    targets = [(t["schema"], t["table"]) for t in _profiling_cfg()["targets"]]
    # Bronze first (the original pass), then the silver pass the gold
    # phase added; the silver profile is the mapping contract's
    # profileHash source and the Phase 6 proposer's sole context (D-23).
    # Since the multi-source fan-in (D-41) every ingested source and every
    # mapped silver table is a target; the retail pair anchors the list.
    assert targets[0] == ("bronze", "online_retail_ii")
    assert ("silver", "silver_invoice_lines") in targets
    assert len(set(targets)) == len(targets)
    schemas = [schema for schema, _ in targets]
    assert schemas == sorted(schemas, key=lambda s: {"bronze": 0, "silver": 1}[s]), (
        "bronze targets precede silver targets"
    )


def test_no_airbyte_target():
    # The profiler skips _airbyte_* tables (spec §8); the config must
    # never list one.
    assert not any(
        t["table"].startswith("_airbyte_") for t in _profiling_cfg()["targets"]
    )


def test_only_selector_restricts_to_configured_targets():
    """`--only SCHEMA.TABLE` mints the named targets in config order and
    refuses a name outside the list (F-45: a full run after a re-landing
    re-mints every artifact, so one source lands, one artifact mints)."""
    import pytest

    from metricmine.profiling.run import select_targets

    targets = [
        {"schema": "bronze", "table": "a"},
        {"schema": "bronze", "table": "b"},
        {"schema": "silver", "table": "silver_a"},
    ]
    assert select_targets(targets, []) == targets
    assert select_targets(targets, ["silver.silver_a", "bronze.a"]) == [
        {"schema": "bronze", "table": "a"},
        {"schema": "silver", "table": "silver_a"},
    ]
    with pytest.raises(ValueError, match="not in config"):
        select_targets(targets, ["bronze.zzz"])
