"""The proposal schemas stay inside the structured-outputs subset (F-26).

Spec: docs/spec/agent-layer.md. Each proposer emits against its proposal
schema under docs/spec/agent-layer/ — a flat projection of the contract
shape — because the API's grammar compiler cannot compile the frozen
mapping-contract schema (F-26, D-21 Amendment F). These tests hold each
projection inside the documented subset (no composition keywords, typed
enums, closed objects with every property required), hold the paired
example valid against it, and ground both examples in the committed
profiles, so an example can never drift from the artifact it claims to
be grounded in.

Runs keyless in the CI pytest lane. No anthropic import here: the SDK
lands in the harness PR; these assertions are pure jsonschema.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = REPO_ROOT / "docs" / "spec" / "agent-layer"

PAIRS = {
    "gold-mapping": (
        "gold-mapping-proposal.schema.json",
        "example-gold-mapping-proposal.json",
    ),
    "silver-cleanup": (
        "silver-cleanup-proposal.schema.json",
        "example-silver-cleanup-proposal.json",
    ),
}

# The composition and constraint keywords the API's grammar compiler
# excludes (F-26): none may appear anywhere in a proposal schema.
FORBIDDEN_KEYWORDS = frozenset({
    "oneOf", "allOf", "anyOf", "if", "then", "else",
    "contains", "minContains", "maxContains", "pattern",
    "patternProperties", "propertyNames", "not",
})


def _load(name: str) -> dict:
    return json.loads((SPEC_DIR / name).read_text(encoding="utf-8"))


def _subschemas(node: object) -> Iterator[dict]:
    """Yield every dict node of a schema tree, skipping property names.

    The keys of a `properties` map are data (column names), not schema
    keywords, so the walk recurses into their values only.
    """
    if isinstance(node, dict):
        yield node
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                for subschema in value.values():
                    yield from _subschemas(subschema)
            else:
                yield from _subschemas(value)
    elif isinstance(node, list):
        for item in node:
            yield from _subschemas(item)


@pytest.fixture(scope="module", params=sorted(PAIRS), ids=sorted(PAIRS))
def pair(request: pytest.FixtureRequest) -> tuple[dict, dict]:
    schema_name, example_name = PAIRS[request.param]
    return _load(schema_name), _load(example_name)


def test_schema_is_valid_draft_2020_12(pair: tuple[dict, dict]) -> None:
    schema, _ = pair
    Draft202012Validator.check_schema(schema)


def test_no_forbidden_keywords(pair: tuple[dict, dict]) -> None:
    schema, _ = pair
    found = sorted(
        {
            key
            for node in _subschemas(schema)
            for key in node
            if key in FORBIDDEN_KEYWORDS
        }
    )
    assert not found, f"grammar-compiler-hostile keywords present: {found}"


def test_every_enum_is_typed_string(pair: tuple[dict, dict]) -> None:
    schema, _ = pair
    for node in _subschemas(schema):
        if "enum" in node:
            assert node.get("type") == "string", f"untyped enum node: {node}"


def test_objects_are_closed_and_fully_required(pair: tuple[dict, dict]) -> None:
    schema, _ = pair
    for node in _subschemas(schema):
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False, f"open object: {node}"
            assert set(node.get("required", [])) == set(node.get("properties", {})), (
                f"required must list every property key: {sorted(node['properties'])}"
            )


def test_example_validates(pair: tuple[dict, dict]) -> None:
    schema, example = pair
    Draft202012Validator(schema).validate(example)


def _profile_columns(relative: str) -> set[str]:
    profile = json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))
    return {column["name"] for column in profile["dataset"]["columns"]}


def test_mapping_example_grounded_in_silver_profile() -> None:
    example = _load("example-gold-mapping-proposal.json")
    columns = _profile_columns("profiles/silver.silver_invoice_lines/v0001.json")
    claimed = {field["name"] for field in example["fields"]}
    claimed.add(example["time_column"])
    for identifier in example["degenerate_identifiers"]:
        claimed.update(identifier["of"])
    ungrounded = sorted(claimed - columns)
    assert not ungrounded, f"columns absent from the silver profile: {ungrounded}"


def test_silver_example_grounded_in_bronze_profile() -> None:
    example = _load("example-silver-cleanup-proposal.json")
    columns = _profile_columns("profiles/bronze.online_retail_ii/v0001.json")
    claimed = {column["source_column"] for column in example["columns"]}
    ungrounded = sorted(claimed - columns)
    assert not ungrounded, f"columns absent from the bronze profile: {ungrounded}"
