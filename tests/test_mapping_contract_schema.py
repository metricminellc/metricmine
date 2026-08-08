"""The mapping-contract JSON Schema holds its example (engine spec §2).

Spec: docs/spec/engine.md. The schema is the machine-readable half of the
mapping contract shape, frozen at the engine-spec PR because Phase 6's
gold mapping proposer emits structured output against this exact schema
(D-21); a change here is a spec amendment in its own PR.

Runs keyless in the CI pytest lane. jsonschema is a dev dependency pinned
in pyproject.toml (already resolved in uv.lock as a transitive of the
locked toolchain; the explicit pin makes the test's dependency honest).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "docs" / "spec" / "engine" / "mapping-contract.schema.json"
EXAMPLE_PATH = (
    REPO_ROOT / "docs" / "spec" / "engine" / "example-mapping-contract.odcs.yaml"
)


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def example() -> dict:
    return yaml.safe_load(EXAMPLE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def validator(schema: dict) -> Draft202012Validator:
    return Draft202012Validator(schema)


def test_schema_is_valid_draft_2020_12(schema: dict) -> None:
    # Meta-validation: the schema itself conforms to its declared draft.
    Draft202012Validator.check_schema(schema)


def test_example_validates(validator: Draft202012Validator, example: dict) -> None:
    validator.validate(example)


def _refused(validator: Draft202012Validator, doc: dict) -> bool:
    try:
        validator.validate(doc)
    except ValidationError:
        return True
    return False


def test_category_name_may_not_shadow_an_emitted_model(
    validator: Draft202012Validator, example: dict
) -> None:
    # The load-bearing naming rule (F-12 collision evidence): category
    # names must never look like dbt model names.
    for bad in ("dim_invoice_lines_values", "fact_x", "vw_x_typed",
                "silver_invoice_lines", "context_registry"):
        doc = copy.deepcopy(example)
        doc["schema"][0]["name"] = bad
        assert _refused(validator, doc), f"schema accepted forbidden name {bad!r}"


def test_quality_rules_are_rejected(
    validator: Draft202012Validator, example: dict
) -> None:
    # Gate 3 skips unmatched objects before rule translation (F-12), so a
    # quality rule on a mapping contract is a dead letter; the schema
    # rejects it outright, on the object and on every field.
    doc = copy.deepcopy(example)
    doc["schema"][0]["quality"] = [{"type": "sql", "query": "SELECT 1"}]
    assert _refused(validator, doc)
    doc = copy.deepcopy(example)
    doc["schema"][0]["properties"][0]["quality"] = [{"type": "sql"}]
    assert _refused(validator, doc)


def test_transaction_grain_requires_degenerate_identifiers(
    validator: Draft202012Validator, example: dict
) -> None:
    doc = copy.deepcopy(example)
    doc["schema"][0]["grain"] = {"type": "transaction", "degenerateIdentifiers": []}
    assert _refused(validator, doc)
    doc["schema"][0]["grain"] = {"type": "transaction"}
    assert _refused(validator, doc)


def test_exactly_one_time_field(
    validator: Draft202012Validator, example: dict
) -> None:
    doc = copy.deepcopy(example)
    for field in doc["schema"][0]["properties"]:
        if field["mappingRole"] == "time":
            field["mappingRole"] = "dimension"
    assert _refused(validator, doc), "zero time fields must be refused"
    doc = copy.deepcopy(example)
    doc["schema"][0]["properties"][0]["mappingRole"] = "time"
    assert _refused(validator, doc), "two time fields must be refused"


def test_provenance_is_required(
    validator: Draft202012Validator, example: dict
) -> None:
    doc = copy.deepcopy(example)
    doc["customProperties"] = [
        p for p in doc["customProperties"] if p["property"] != "profileHash"
    ]
    assert _refused(validator, doc), "missing profileHash must be refused"
    doc = copy.deepcopy(example)
    for p in doc["customProperties"]:
        if p["property"] == "profileHash":
            p["value"] = "not-a-hash"
    assert _refused(validator, doc), "malformed profileHash must be refused"
    # Duplicate provenance keys are refused whether the duplicate is
    # well-formed (maxContains) or garbage-valued (the item-level if/then).
    doc = copy.deepcopy(example)
    doc["customProperties"].append({"property": "proposedBy", "value": "human"})
    assert _refused(validator, doc), "duplicate valid proposedBy must be refused"
    doc = copy.deepcopy(example)
    doc["customProperties"].append({"property": "proposedBy", "value": "garbage"})
    assert _refused(validator, doc), "garbage-valued proposedBy must be refused"


def test_one_category_per_contract(
    validator: Draft202012Validator, example: dict
) -> None:
    doc = copy.deepcopy(example)
    doc["schema"].append(copy.deepcopy(doc["schema"][0]))
    assert _refused(validator, doc)
