"""The describe renderer mirrors the committed table-contract shape
(D-35, F-27).

The render target is the committed hand-written contract
contracts/silver_invoice_lines.odcs.yaml: same top-level key order, same
schema-object key order, grain as primaryKey positions plus the
error-severity enforcing rule, and STABLE rule prose (sync names
generated test files from rule descriptions, so evidence sentences stay
out of them). Keyless, no SDK, no network.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from metricmine.agents.render import (
    Provenance,
    ROW_COUNT_RULE_DESCRIPTION,
    grain_rule_description,
    non_negative_rule_description,
    render_describe,
    to_yaml,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def proposal() -> dict:
    return json.loads(
        (
            REPO_ROOT
            / "docs"
            / "spec"
            / "agent-layer"
            / "example-describe-proposal.json"
        ).read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def provenance() -> Provenance:
    return Provenance(
        proposed_by="silver-cleanup-proposer",
        proposer_version="0.1.0",
        prompt_version="1.0.0",
        model_id="test-model",
        profile_hash="sha256:" + "0" * 64,
        proposed_at="2026-08-25",
        extras={"proposerStance": "describe"},
    )


@pytest.fixture(scope="module")
def rendered(proposal: dict, provenance: Provenance) -> dict:
    return render_describe(copy.deepcopy(proposal), provenance, "1.0.0")


@pytest.fixture(scope="module")
def committed() -> dict:
    return yaml.safe_load(
        (REPO_ROOT / "contracts" / "silver_invoice_lines.odcs.yaml").read_text(
            encoding="utf-8"
        )
    )


def test_key_orders_mirror_the_committed_contract(
    rendered: dict, committed: dict
) -> None:
    assert list(rendered) == list(committed)
    assert list(rendered["schema"][0]) == list(committed["schema"][0])


def test_draft_status_and_version_come_from_the_harness(
    rendered: dict,
) -> None:
    assert rendered["status"] == "draft"
    assert rendered["version"] == "1.0.0"


def test_grain_renders_as_primary_key_positions(rendered: dict) -> None:
    keyed = {
        prop["name"]: prop["primaryKeyPosition"]
        for prop in rendered["schema"][0]["properties"]
        if prop.get("primaryKey")
    }
    assert keyed == {
        "invoice_id": 1,
        "stock_code": 2,
        "quantity": 3,
        "unit_price": 4,
    }


def test_rule_descriptions_are_stable_prose(rendered: dict) -> None:
    table_rules = rendered["schema"][0]["quality"]
    assert table_rules[0]["description"] == ROW_COUNT_RULE_DESCRIPTION
    assert table_rules[1]["description"] == grain_rule_description(
        ["invoice_id", "stock_code", "quantity", "unit_price"]
    )
    unit_price = next(
        prop
        for prop in rendered["schema"][0]["properties"]
        if prop["name"] == "unit_price"
    )
    assert unit_price["quality"][0][
        "description"
    ] == non_negative_rule_description("unit_price")
    for rule in table_rules + unit_price["quality"]:
        assert rule["severity"] == "error"
        assert "v0001" not in str(rule["description"])


def test_provenance_orders_appendix_b_then_stance_then_decisions(
    rendered: dict, proposal: dict
) -> None:
    keys = [entry["property"] for entry in rendered["customProperties"]]
    assert keys[:7] == [
        "proposedBy",
        "proposerVersion",
        "promptVersion",
        "modelId",
        "profileHash",
        "proposedAt",
        "proposerStance",
    ]
    assert keys[7:-1] == [entry["key"] for entry in proposal["decisions"]]
    assert keys[-1] == "grain"


def test_rendering_twice_is_byte_identical(
    proposal: dict, provenance: Provenance
) -> None:
    header = ["one", "two"]
    first = to_yaml(
        render_describe(copy.deepcopy(proposal), provenance, "1.0.0"), header
    )
    second = to_yaml(
        render_describe(copy.deepcopy(proposal), provenance, "1.0.0"), header
    )
    assert first == second


def test_round_trip_through_yaml_preserves_the_grain_query(
    proposal: dict, provenance: Provenance
) -> None:
    text = to_yaml(
        render_describe(copy.deepcopy(proposal), provenance, "1.0.0"), ["h"]
    )
    parsed = yaml.safe_load(text)
    query = parsed["schema"][0]["quality"][1]["query"]
    assert query.startswith("SELECT COUNT(*) FROM (")
    assert "silver.silver_invoice_lines" in query
