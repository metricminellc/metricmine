"""The cleanup validator: groundedness to zero, completeness held.

Spec: docs/spec/agent-layer.md §3 (D-23 as amended by Amendment H). The
committed example proposal must be clean against the committed bronze
profile; every planted defect must be caught. Keyless.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from metricmine.agents.validate import validate_cleanup

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def example() -> dict:
    path = (
        REPO_ROOT
        / "docs"
        / "spec"
        / "agent-layer"
        / "example-silver-cleanup-proposal.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def profile() -> dict:
    path = REPO_ROOT / "profiles" / "bronze.online_retail_ii" / "v0001.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_example_is_clean(example: dict, profile: dict) -> None:
    assert validate_cleanup(example, profile) == []


def test_unknown_source_column_fails(example: dict, profile: dict) -> None:
    doc = copy.deepcopy(example)
    doc["columns"][0]["source_column"] = "no_such_column"
    errors = validate_cleanup(doc, profile)
    assert any(
        "groundedness" in e and "no_such_column" in e for e in errors
    )


def test_airbyte_column_not_dropped_fails(
    example: dict, profile: dict
) -> None:
    doc = copy.deepcopy(example)
    doc["columns"] = [
        c for c in doc["columns"] if c["source_column"] != "_airbyte_raw_id"
    ]
    errors = validate_cleanup(doc, profile)
    assert any("_airbyte_raw_id" in e and "drop" in e for e in errors)


def test_grain_key_with_required_false_fails(
    example: dict, profile: dict
) -> None:
    doc = copy.deepcopy(example)
    for column in doc["columns"]:
        if column["target_name"] == "invoice_id":
            column["required"] = False
    errors = validate_cleanup(doc, profile)
    assert any(
        "grain key" in e and "invoice_id" in e and "required" in e
        for e in errors
    )


def test_duplicate_target_names_fail(example: dict, profile: dict) -> None:
    doc = copy.deepcopy(example)
    for column in doc["columns"]:
        if column["target_name"] == "product_description":
            column["target_name"] = "country"
    errors = validate_cleanup(doc, profile)
    assert any("unique" in e for e in errors)


def test_dedupe_key_naming_unknown_target_fails(
    example: dict, profile: dict
) -> None:
    doc = copy.deepcopy(example)
    doc["dedupe_keys"] = doc["dedupe_keys"] + ["ghost_column"]
    errors = validate_cleanup(doc, profile)
    assert any(
        "dedupe key" in e and "ghost_column" in e for e in errors
    )
