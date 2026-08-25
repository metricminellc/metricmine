"""The describe validator: evidence-exact machine half, gated judgment
half (D-35, D-23 as amended).

Describe adopts an existing table AS IT IS, so the deterministic
validator holds the proposal's machine half to the profile exactly and
the judgment half to evidence support. Fixtures: the committed example
proposal and the committed silver profile, with one planted defect per
test. Keyless, no SDK, no network.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from metricmine.agents.validate import validate_describe

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def profile() -> dict:
    return json.loads(
        (
            REPO_ROOT / "profiles" / "silver.silver_invoice_lines" / "v0001.json"
        ).read_text(encoding="utf-8")
    )


@pytest.fixture()
def proposal() -> dict:
    return copy.deepcopy(
        json.loads(
            (
                REPO_ROOT
                / "docs"
                / "spec"
                / "agent-layer"
                / "example-describe-proposal.json"
            ).read_text(encoding="utf-8")
        )
    )


def test_committed_example_is_clean(proposal: dict, profile: dict) -> None:
    assert validate_describe(proposal, profile) == []


def test_amend_stance_is_refused_here(proposal: dict, profile: dict) -> None:
    proposal["stance"] = "amend"
    errors = validate_describe(proposal, profile)
    assert any("stance" in error for error in errors)


def test_changes_must_be_empty(proposal: dict, profile: dict) -> None:
    proposal["changes"] = [
        {
            "kind": "no_change",
            "column": "",
            "before": "",
            "after": "",
            "rationale": "planted",
        }
    ]
    errors = validate_describe(proposal, profile)
    assert any("empty changes list" in error for error in errors)


def test_target_table_must_match_the_profile(
    proposal: dict, profile: dict
) -> None:
    proposal["target_table"] = "silver_other"
    errors = validate_describe(proposal, profile)
    assert any("target_table" in error for error in errors)


def test_target_schema_must_match_the_profile(
    proposal: dict, profile: dict
) -> None:
    proposal["target_schema"] = "bronze"
    errors = validate_describe(proposal, profile)
    assert any("target_schema" in error for error in errors)


def test_proposed_version_must_be_semver(
    proposal: dict, profile: dict
) -> None:
    proposal["proposed_version"] = "one"
    errors = validate_describe(proposal, profile)
    assert any("semver" in error for error in errors)


def test_columns_enumerate_in_profile_order(
    proposal: dict, profile: dict
) -> None:
    proposal["columns"].append(proposal["columns"].pop(0))
    errors = validate_describe(proposal, profile)
    assert any("profile order" in error for error in errors)


def test_a_dropped_column_is_rejected(proposal: dict, profile: dict) -> None:
    proposal["columns"] = proposal["columns"][:-1]
    errors = validate_describe(proposal, profile)
    assert any("enumerate" in error for error in errors)


def test_physical_type_must_equal_the_profile(
    proposal: dict, profile: dict
) -> None:
    proposal["columns"][0]["physical_type"] = "TEXT"
    errors = validate_describe(proposal, profile)
    assert any("physical_type" in error for error in errors)


def test_required_must_equal_the_null_rate(
    proposal: dict, profile: dict
) -> None:
    target = next(
        column
        for column in proposal["columns"]
        if column["name"] == "product_description"
    )
    target["required"] = True
    errors = validate_describe(proposal, profile)
    assert any("required" in error and "null_rate" in error for error in errors)


def test_logical_type_follows_the_fixed_map(
    proposal: dict, profile: dict
) -> None:
    target = next(
        column
        for column in proposal["columns"]
        if column["physical_type"] == "VARCHAR"
    )
    target["logical_type"] = "number"
    errors = validate_describe(proposal, profile)
    assert any("logical_type" in error for error in errors)


def test_grain_keys_must_be_profiled_and_non_null(
    proposal: dict, profile: dict
) -> None:
    proposal["grain_keys"] = ["region"]
    errors = validate_describe(proposal, profile)
    assert any("grain key 'region'" in error for error in errors)
    proposal["grain_keys"] = ["product_description"]
    errors = validate_describe(proposal, profile)
    assert any("nonzero profiled null_rate" in error for error in errors)


def test_the_two_table_rules_are_required_exactly_once(
    proposal: dict, profile: dict
) -> None:
    rules = [
        rule
        for rule in proposal["quality_rules"]
        if rule["kind"] != "grain_unique"
    ]
    proposal["quality_rules"] = rules
    errors = validate_describe(proposal, profile)
    assert any("grain_unique" in error for error in errors)


def test_not_null_rule_needs_a_zero_null_rate(
    proposal: dict, profile: dict
) -> None:
    proposal["quality_rules"].append(
        {
            "kind": "not_null",
            "column": "product_description",
            "values": [],
            "rationale": "planted",
        }
    )
    errors = validate_describe(proposal, profile)
    assert any("not_null" in error for error in errors)


def test_non_negative_rule_needs_a_non_negative_min(
    proposal: dict, profile: dict
) -> None:
    proposal["quality_rules"].append(
        {
            "kind": "non_negative",
            "column": "quantity",
            "values": [],
            "rationale": "planted",
        }
    )
    errors = validate_describe(proposal, profile)
    assert any("non_negative" in error for error in errors)


def test_accepted_values_need_the_full_distinct_list(
    proposal: dict, profile: dict
) -> None:
    proposal["quality_rules"].append(
        {
            "kind": "accepted_values_subset",
            "column": "invoice_id",
            "values": ["489434"],
            "rationale": "planted",
        }
    )
    errors = validate_describe(proposal, profile)
    assert any("distinct_values" in error for error in errors)


def test_values_on_a_non_subset_rule_are_rejected(
    proposal: dict, profile: dict
) -> None:
    target = next(
        rule
        for rule in proposal["quality_rules"]
        if rule["kind"] == "non_negative"
    )
    target["values"] = ["0"]
    errors = validate_describe(proposal, profile)
    assert any("does not use them" in error for error in errors)
