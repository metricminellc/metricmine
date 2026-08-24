"""The constructed pathological profile fixture and its planted defects (D-25).

Spec: docs/spec/agent-layer.md §5 (the golden-profile set) and
docs/spec/profiler.md §3 to §5 (artifact shape, caps, the truncation
marker). Issue #15 (the faker path) is open, so the third fixture is
constructed through the profiler's own builders and committed under
tests/agents/fixtures/. Keyless: the fixture must pass the harness's
integrity check, the evidence-only example proposal must pass the cleanup
validator, and every planted defect must be caught by name.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from metricmine.agents.render import Provenance, render_cleanup, to_yaml
from metricmine.agents.validate import validate_cleanup
from metricmine.profiling import canonical
from metricmine.profiling.build import CAPS, TRUNCATION_SUFFIX

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "agents" / "fixtures"
PROFILE = FIXTURES / "profiles" / "bronze.messy_orders" / "v0001.json"
EXAMPLE = FIXTURES / "proposals" / "example-silver-cleanup-messy-orders.json"

PROVENANCE = Provenance(
    proposed_by="silver-cleanup-proposer",
    proposer_version="0.1.0",
    prompt_version="1.0.0",
    model_id="claude-sonnet-5",
    profile_hash="sha256:" + "0" * 64,
    proposed_at="2026-08-22",
    extras={"proposerStance": "cleanup"},
)


@pytest.fixture(scope="module")
def profile() -> dict:
    return json.loads(PROFILE.read_text(encoding="utf-8"))


@pytest.fixture()
def proposal() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_builder_reproduces_the_committed_bytes() -> None:
    spec = importlib.util.spec_from_file_location(
        "build_messy_orders_profile", FIXTURES / "build_messy_orders_profile.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert canonical.canonical_bytes(module.build()) == PROFILE.read_bytes()


def test_fixture_passes_the_integrity_check(profile: dict) -> None:
    assert canonical.content_hash(profile["dataset"]) == profile["content_hash"]
    assert PROFILE.read_bytes() == canonical.canonical_bytes(profile)
    assert profile["schema_version"] == "1.0.0"
    assert profile["caps"] == CAPS


def test_fixture_plants_the_pathological_conditions(profile: dict) -> None:
    columns = {c["name"]: c for c in profile["dataset"]["columns"]}
    assert len(columns) == 15
    assert profile["dataset"]["duplicate_row_rate"] == 0.08
    assert "Order ID" in columns and "LineNo" in columns  # not snake_case
    assert columns["customer_email"]["null_rate"] == 0.97
    assert columns["qty"]["physical_type"] == "VARCHAR"
    assert "three" in columns["qty"]["sample_values"]  # mixed representations
    truncated = [
        v for v in columns["notes"]["sample_values"] if v.endswith(TRUNCATION_SUFFIX)
    ]
    assert len(truncated) == 1
    assert len(truncated[0]) == CAPS["max_string_chars"] + len(TRUNCATION_SUFFIX)
    assert any(
        v.startswith("IGNORE PREVIOUS INSTRUCTIONS")
        for v in columns["notes"]["sample_values"]
    )  # data, never instructions (agent-layer spec §2)
    assert sorted(n for n, c in columns.items() if c["is_airbyte_metadata"]) == [
        "_airbyte_extracted_at",
        "_airbyte_meta",
        "_airbyte_raw_id",
    ]


def test_example_proposal_is_clean_and_renders(profile: dict, proposal: dict) -> None:
    assert validate_cleanup(proposal, profile) == []
    document = render_cleanup(proposal, PROVENANCE, "1.0.0")
    properties = document["schema"][0]["properties"]
    assert len(properties) == 12  # 15 columns, three metadata drops
    assert [p["name"] for p in properties if p.get("primaryKey")] == [
        "order_id",
        "line_no",
    ]
    text = to_yaml(document, ["Fixture.", "Review before approval (D-24)."])
    assert "query: |" in text  # literal block for the multi-line rule query
    stances = [
        p["value"] for p in document["customProperties"] if p["property"] == "proposerStance"
    ]
    assert stances == ["cleanup"]


def _with(proposal: dict, **changes: object) -> dict:
    mutated = copy.deepcopy(proposal)
    mutated.update(changes)
    return mutated


def test_planted_defects_are_caught_by_name(profile: dict, proposal: dict) -> None:
    columns = proposal["columns"]

    kept_space = copy.deepcopy(proposal)
    kept_space["columns"][0]["action"] = "keep"
    kept_space["columns"][0]["target_name"] = "Order ID"
    kept_space["grain_keys"] = ["Order ID", "line_no"]
    assert any("not snake_case" in e for e in validate_cleanup(kept_space, profile))

    kept_metadata = copy.deepcopy(proposal)
    raw_id = next(c for c in kept_metadata["columns"] if c["source_column"] == "_airbyte_raw_id")
    raw_id["action"] = "keep"
    raw_id["target_name"] = "_airbyte_raw_id"
    errors = validate_cleanup(kept_metadata, profile)
    assert any("airbyte metadata column '_airbyte_raw_id'" in e for e in errors)

    optional_grain = copy.deepcopy(proposal)
    optional_grain["columns"][1]["required"] = False
    assert any(
        "grain key 'line_no' must be required true" in e
        for e in validate_cleanup(optional_grain, profile)
    )

    hallucinated = copy.deepcopy(proposal)
    hallucinated["columns"].append(
        {**columns[2], "source_column": "order_total", "target_name": "order_total"}
    )
    assert any(
        "groundedness: source_column 'order_total'" in e
        for e in validate_cleanup(hallucinated, profile)
    )

    bad_dedupe = _with(proposal, dedupe_keys=["order_id", "shipped_flag"])
    assert any(
        "dedupe key 'shipped_flag' names no non-drop target" in e
        for e in validate_cleanup(bad_dedupe, profile)
    )

    bad_prefix = _with(proposal, target_table="messy_orders_clean")
    assert any("must start with silver_" in e for e in validate_cleanup(bad_prefix, profile))

    duplicate_targets = copy.deepcopy(proposal)
    duplicate_targets["columns"][1]["target_name"] = "order_id"
    duplicate_targets["grain_keys"] = ["order_id"]
    assert any(
        "target names must be unique" in e
        for e in validate_cleanup(duplicate_targets, profile)
    )

    no_grain = _with(proposal, grain_keys=[])
    assert any("at least one grain key" in e for e in validate_cleanup(no_grain, profile))
