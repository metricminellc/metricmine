"""The mapping validator: groundedness to zero, completeness held.

Spec: docs/spec/agent-layer.md §3 (D-23 as amended by Amendment H). The
committed example proposal must be clean against the committed silver
profile; every planted defect must be caught. Keyless.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from metricmine.agents.validate import validate_mapping

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def example() -> dict:
    path = (
        REPO_ROOT
        / "docs"
        / "spec"
        / "agent-layer"
        / "example-gold-mapping-proposal.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def profile() -> dict:
    path = REPO_ROOT / "profiles" / "silver.silver_invoice_lines" / "v0001.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_example_is_clean(example: dict, profile: dict) -> None:
    assert validate_mapping(example, profile) == []


def test_planted_column_fails_groundedness(
    example: dict, profile: dict
) -> None:
    doc = copy.deepcopy(example)
    doc["fields"].append(
        {
            "name": "region",
            "logical_type": "string",
            "physical_type": "VARCHAR",
            "required": False,
            "mapping_role": "dimension",
            "description": "A hallucinated column.",
        }
    )
    errors = validate_mapping(doc, profile)
    assert any("groundedness" in e and "region" in e for e in errors)


def test_two_time_roles_fail(example: dict, profile: dict) -> None:
    doc = copy.deepcopy(example)
    doc["fields"][0]["mapping_role"] = "time"
    errors = validate_mapping(doc, profile)
    assert any("exactly one field" in e for e in errors)


def test_transaction_without_identifier_fails(
    example: dict, profile: dict
) -> None:
    doc = copy.deepcopy(example)
    doc["degenerate_identifiers"] = []
    errors = validate_mapping(doc, profile)
    assert any("at least one degenerate identifier" in e for e in errors)


def test_aggregated_with_identifiers_fails(
    example: dict, profile: dict
) -> None:
    doc = copy.deepcopy(example)
    doc["grain_type"] = "aggregated"
    doc["aggregations"] = [{"field": "quantity", "function": "sum"}]
    errors = validate_mapping(doc, profile)
    assert any("no degenerate identifiers" in e for e in errors)


def test_reserved_category_name_fails(example: dict, profile: dict) -> None:
    doc = copy.deepcopy(example)
    doc["category_name"] = "fact_invoice_lines"
    errors = validate_mapping(doc, profile)
    assert any("reserved" in e for e in errors)


def test_reserved_mart_prefix_fails(example: dict, profile: dict) -> None:
    """mart_ joined the reserved model-name space with D-36's emitted
    mart; the proposal validator mirrors the frozen schema's rejection."""
    doc = copy.deepcopy(example)
    doc["category_name"] = "mart_invoice_lines"
    errors = validate_mapping(doc, profile)
    assert any("reserved" in e for e in errors)


def test_wrong_source_table_fails(example: dict, profile: dict) -> None:
    doc = copy.deepcopy(example)
    doc["source_table"] = "silver.some_other_table"
    errors = validate_mapping(doc, profile)
    assert any("source_table" in e for e in errors)
