"""The amend validator: true claims, declared moves, the direction gate.

D-35 fixes the amend posture: the declared changes[] list is the only
channel through which the committed document moves. These tests hold the
validator to the three duties the stance addendum named: a false claim
is refused (a drop of a column the contract never declared, a wrong
`before`); an undeclared move is refused symmetrically (a silent drop, a
silent addition, a re-emitted type or required flag that drifted with no
declaring entry); and the D-08 direction gate (narrowing refused without
allow_relaxation, with the `relaxation:` prefix the harness fails closed
on). All constructed inputs, all keyless.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from metricmine.agents.validate import (
    classify_change,
    committed_rule_signatures,
    derive_bump,
    validate_amend,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def committed() -> dict:
    return yaml.safe_load(
        (REPO_ROOT / "contracts" / "silver_invoice_lines.odcs.yaml").read_text(
            encoding="utf-8"
        )
    )


@pytest.fixture(scope="module")
def profile() -> dict:
    return json.loads(
        (
            REPO_ROOT
            / "profiles"
            / "silver.silver_invoice_lines"
            / "v0001.json"
        ).read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def example() -> dict:
    return json.loads(
        (
            REPO_ROOT
            / "docs"
            / "spec"
            / "agent-layer"
            / "example-amend-proposal.json"
        ).read_text(encoding="utf-8")
    )


def _amended(example: dict, **overrides: object) -> dict:
    proposal = copy.deepcopy(example)
    proposal.update(overrides)
    return proposal


def test_the_committed_example_validates_clean(
    example: dict, profile: dict, committed: dict
) -> None:
    assert validate_amend(example, profile, committed) == []


def test_wrong_stance_is_refused(
    example: dict, profile: dict, committed: dict
) -> None:
    errors = validate_amend(
        _amended(example, stance="describe"), profile, committed
    )
    assert any("not amend" in e for e in errors)


def test_an_empty_change_set_is_refused(
    example: dict, profile: dict, committed: dict
) -> None:
    errors = validate_amend(
        _amended(example, changes=[]), profile, committed
    )
    assert any("at least one changes[] entry" in e for e in errors)


def test_a_no_change_only_set_is_refused(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["changes"] = [
        {
            "kind": "no_change",
            "column": "",
            "before": "",
            "after": "",
            "rationale": "nothing moved",
        }
    ]
    # Restore the re-emitted quantity description to the committed text
    # so the only difference IS the no_change entry.
    errors = validate_amend(proposal, profile, committed)
    assert any("nothing to amend" in e for e in errors)


def test_a_false_drop_claim_is_refused(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["changes"].append(
        {
            "kind": "drop_column",
            "column": "no_such_column",
            "before": "VARCHAR",
            "after": "",
            "rationale": "false claim",
        }
    )
    errors = validate_amend(proposal, profile, committed, allow_relaxation=True)
    assert any(
        "drop_column 'no_such_column' is a false claim" in e for e in errors
    )


def test_an_undeclared_drop_is_refused(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["columns"] = [
        c for c in proposal["columns"] if c["name"] != "country"
    ]
    errors = validate_amend(proposal, profile, committed)
    assert any(
        "'country' is missing from columns[] with no declared drop_column"
        in e
        for e in errors
    )


def test_an_undeclared_addition_is_refused(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["columns"].append(
        {
            "name": "sneaky",
            "logical_type": "string",
            "physical_type": "VARCHAR",
            "required": False,
            "description": "undeclared",
            "rationale": "undeclared",
        }
    )
    errors = validate_amend(proposal, profile, committed)
    assert any("undeclared addition" in e for e in errors)


def test_an_undeclared_retype_is_refused(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    for column in proposal["columns"]:
        if column["name"] == "quantity":
            column["physical_type"] = "BIGINT"
    errors = validate_amend(proposal, profile, committed)
    assert any(
        "no declared retype_column" in e and "'quantity'" in e
        for e in errors
    )


def test_an_undeclared_required_flip_is_refused(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    for column in proposal["columns"]:
        if column["name"] == "country":
            column["required"] = False
    errors = validate_amend(proposal, profile, committed)
    assert any(
        "no declared required_change" in e and "'country'" in e
        for e in errors
    )


def test_a_wrong_before_on_required_change_is_refused(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["changes"].append(
        {
            "kind": "required_change",
            "column": "country",
            "before": "false",
            "after": "true",
            "rationale": "wrong before: country is already required",
        }
    )
    errors = validate_amend(proposal, profile, committed)
    assert any(
        "required_change 'country' claims before 'false'" in e
        for e in errors
    )


def test_a_retype_must_follow_the_fresh_profile(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["changes"].append(
        {
            "kind": "retype_column",
            "column": "quantity",
            "before": "INTEGER",
            "after": "BIGINT",
            "rationale": "the profile still measures INTEGER",
        }
    )
    for column in proposal["columns"]:
        if column["name"] == "quantity":
            column["physical_type"] = "BIGINT"
    errors = validate_amend(proposal, profile, committed, allow_relaxation=True)
    assert any(
        "a retype follows the type the engine produced" in e for e in errors
    )


def test_an_added_column_must_enter_optional(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["changes"].append(
        {
            "kind": "add_column",
            "column": "line_note",
            "before": "",
            "after": "VARCHAR",
            "rationale": "operator intent adds a note column",
        }
    )
    proposal["columns"].append(
        {
            "name": "line_note",
            "logical_type": "string",
            "physical_type": "VARCHAR",
            "required": True,
            "description": "a note",
            "rationale": "intent",
        }
    )
    errors = validate_amend(proposal, profile, committed)
    assert any(
        "must enter required false" in e and "F-28" in e for e in errors
    )


def test_a_paired_follow_up_required_change_is_accepted_and_deferred(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["changes"].append(
        {
            "kind": "add_column",
            "column": "line_note",
            "before": "",
            "after": "VARCHAR",
            "rationale": "operator intent adds a note column",
        }
    )
    proposal["changes"].append(
        {
            "kind": "required_change",
            "column": "line_note",
            "before": "false",
            "after": "true",
            "rationale": "declared follow-up after the model lands (F-28)",
        }
    )
    proposal["columns"].append(
        {
            "name": "line_note",
            "logical_type": "string",
            "physical_type": "VARCHAR",
            "required": False,
            "description": "a note",
            "rationale": "intent",
        }
    )
    proposal["proposed_version"] = "1.2.0"
    assert validate_amend(proposal, profile, committed) == []


def test_a_description_change_matching_committed_text_is_refused(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    committed_desc = str(
        next(
            p
            for p in committed["schema"][0]["properties"]
            if p["name"] == "quantity"
        )["description"]
    ).strip()
    proposal["changes"][0]["after"] = committed_desc
    for column in proposal["columns"]:
        if column["name"] == "quantity":
            column["description"] = committed_desc
    errors = validate_amend(proposal, profile, committed)
    assert any("matches the committed text" in e for e in errors)


def test_narrowing_is_refused_without_the_flag(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["changes"].append(
        {
            "kind": "drop_column",
            "column": "product_description",
            "before": "VARCHAR",
            "after": "",
            "rationale": "operator intent drops the column",
        }
    )
    proposal["columns"] = [
        c for c in proposal["columns"] if c["name"] != "product_description"
    ]
    proposal["proposed_version"] = "2.0.0"
    errors = validate_amend(proposal, profile, committed)
    assert len(errors) == 1
    assert errors[0].startswith("relaxation:")
    assert "--allow-relaxation" in errors[0]
    assert "MAJOR" in errors[0]


def test_the_flag_admits_the_same_narrowing_set(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["changes"].append(
        {
            "kind": "drop_column",
            "column": "product_description",
            "before": "VARCHAR",
            "after": "",
            "rationale": "operator intent drops the column",
        }
    )
    proposal["columns"] = [
        c for c in proposal["columns"] if c["name"] != "product_description"
    ]
    proposal["proposed_version"] = "2.0.0"
    assert (
        validate_amend(proposal, profile, committed, allow_relaxation=True)
        == []
    )


def test_a_rule_change_outside_the_closed_list_is_refused(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["changes"].append(
        {
            "kind": "rule_change",
            "column": "",
            "before": "freshness_sla",
            "after": "",
            "rationale": "outside the closed list",
        }
    )
    errors = validate_amend(proposal, profile, committed, allow_relaxation=True)
    assert any("outside the closed rule list" in e for e in errors)


def test_an_added_rule_needs_its_quality_rules_definition(
    example: dict, profile: dict, committed: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["changes"].append(
        {
            "kind": "rule_change",
            "column": "",
            "before": "",
            "after": "not_null:country",
            "rationale": "country never null at the fresh profile",
        }
    )
    errors = validate_amend(proposal, profile, committed)
    assert any(
        "no quality_rules[] entry carries its definition" in e
        for e in errors
    )


def test_the_committed_rule_signatures_read_the_closed_list(
    committed: dict,
) -> None:
    assert committed_rule_signatures(committed) == {
        "row_count_positive",
        "grain_unique",
        "non_negative:unit_price",
    }


def test_direction_classification_is_the_addendum_table() -> None:
    def change(kind: str, before: str = "", after: str = "") -> dict:
        return {
            "kind": kind,
            "column": "c",
            "before": before,
            "after": after,
            "rationale": "",
        }

    assert classify_change(change("add_column")) == "widening"
    assert (
        classify_change(change("required_change", "false", "true"))
        == "widening"
    )
    assert (
        classify_change(change("rule_change", "", "not_null:c")) == "widening"
    )
    assert classify_change(change("description_change")) == "neutral"
    assert classify_change(change("no_change")) == "neutral"
    assert classify_change(change("drop_column")) == "narrowing"
    assert (
        classify_change(change("required_change", "true", "false"))
        == "narrowing"
    )
    assert (
        classify_change(change("rule_change", "not_null:c", ""))
        == "narrowing"
    )
    assert classify_change(change("retype_column")) == "narrowing"
    assert classify_change(change("grain_change")) == "narrowing"


def test_bump_derivation_takes_the_worst_direction() -> None:
    neutral = {
        "kind": "description_change",
        "column": "c",
        "before": "a",
        "after": "b",
        "rationale": "",
    }
    widening = {
        "kind": "add_column",
        "column": "d",
        "before": "",
        "after": "VARCHAR",
        "rationale": "",
    }
    narrowing = {
        "kind": "drop_column",
        "column": "e",
        "before": "VARCHAR",
        "after": "",
        "rationale": "",
    }
    assert derive_bump([neutral]) == "patch"
    assert derive_bump([neutral, widening]) == "minor"
    assert derive_bump([neutral, widening, narrowing]) == "major"


def test_a_wrong_proposed_version_is_reported(
    example: dict, profile: dict, committed: dict
) -> None:
    errors = validate_amend(
        _amended(example, proposed_version="2.0.0"), profile, committed
    )
    assert any("proposed_version" in e for e in errors)
