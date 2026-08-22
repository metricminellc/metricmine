"""The deterministic renderer against the committed contracts (F-26).

Spec: docs/spec/agent-layer.md §1 (serialization boundary) and
docs/spec/engine.md §2. The mapping example must render to a document
the FROZEN schema accepts with first-class elements equal to the
committed mapping v1.1.0; the cleanup render mirrors the committed
silver contract's shape. Keyless.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from metricmine.agents.render import (
    Provenance,
    next_version,
    render_cleanup,
    render_mapping,
    to_yaml,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = REPO_ROOT / "docs" / "spec" / "agent-layer"

PROVENANCE = Provenance(
    proposed_by="gold-mapping-proposer",
    proposer_version="0.1.0",
    prompt_version="1.0.0",
    model_id="claude-sonnet-5",
    profile_hash="sha256:" + "0" * 64,
    proposed_at="2026-08-22",
)

_HEADER = ["Draft for tests.", "Review before approval (D-24)."]


@pytest.fixture(scope="module")
def mapping_example() -> dict:
    path = SPEC_DIR / "example-gold-mapping-proposal.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cleanup_example() -> dict:
    path = SPEC_DIR / "example-silver-cleanup-proposal.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def committed_mapping() -> dict:
    path = REPO_ROOT / "contracts" / "gold_invoice_lines_mapping.odcs.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_mapping_render_validates_against_frozen_schema(
    mapping_example: dict,
) -> None:
    frozen = json.loads(
        (
            REPO_ROOT / "docs" / "spec" / "engine"
            / "mapping-contract.schema.json"
        ).read_text(encoding="utf-8")
    )
    document = render_mapping(mapping_example, PROVENANCE, "1.2.0")
    Draft202012Validator(frozen).validate(document)


def test_mapping_first_class_elements_equal_committed(
    mapping_example: dict, committed_mapping: dict
) -> None:
    rendered = render_mapping(mapping_example, PROVENANCE, "1.2.0")
    ours = rendered["schema"][0]
    theirs = committed_mapping["schema"][0]
    for key in ("name", "entityGroup", "sourceTable", "timeColumn",
                "timeGrain", "grain"):
        assert ours[key] == theirs[key], key
    tuple_keys = (
        "name", "logicalType", "physicalType", "required", "mappingRole"
    )
    ours_tuples = [
        tuple(p[k] for k in tuple_keys) for p in ours["properties"]
    ]
    theirs_tuples = [
        tuple(p[k] for k in tuple_keys) for p in theirs["properties"]
    ]
    assert ours_tuples == theirs_tuples


def test_version_rule(committed_mapping: dict) -> None:
    assert committed_mapping["version"] == "1.1.0"
    assert next_version(committed_mapping["version"], "minor") == "1.2.0"
    assert next_version(None, "minor") == "1.0.0"


def test_status_is_draft(mapping_example: dict) -> None:
    rendered = render_mapping(mapping_example, PROVENANCE, "1.2.0")
    assert rendered["status"] == "draft"


def test_provenance_keys_in_appendix_b_order(mapping_example: dict) -> None:
    rendered = render_mapping(mapping_example, PROVENANCE, "1.2.0")
    keys = [entry["property"] for entry in rendered["customProperties"]]
    assert keys[:6] == [
        "proposedBy",
        "proposerVersion",
        "promptVersion",
        "modelId",
        "profileHash",
        "proposedAt",
    ]


def test_rendering_twice_is_byte_identical(
    mapping_example: dict, cleanup_example: dict
) -> None:
    for render, example in (
        (render_mapping, mapping_example),
        (render_cleanup, cleanup_example),
    ):
        first = to_yaml(render(example, PROVENANCE, "1.2.0"), _HEADER)
        second = to_yaml(render(example, PROVENANCE, "1.2.0"), _HEADER)
        assert first == second


def test_cleanup_render_shape(cleanup_example: dict) -> None:
    rendered = render_cleanup(cleanup_example, PROVENANCE, "1.2.0")
    table = rendered["schema"][0]
    properties = table["properties"]
    assert len(properties) == 9
    assert not any(p["name"].startswith("_airbyte") for p in properties)
    positions = {
        p["name"]: p["primaryKeyPosition"]
        for p in properties
        if p.get("primaryKey")
    }
    assert positions == {
        "invoice_id": 1,
        "stock_code": 2,
        "quantity": 3,
        "unit_price": 4,
    }
    rules = table["quality"]
    assert len(rules) == 2
    assert all(rule["severity"] == "error" for rule in rules)
    decision_keys = [
        e["property"]
        for e in rendered["customProperties"]
        if e["property"].startswith("decision")
    ]
    assert len(decision_keys) == 6
