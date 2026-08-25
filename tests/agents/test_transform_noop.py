"""The strip-first order for transform_schema, pinned (F-26, Amendment F).

Measured at anthropic 1.0.0: transform_schema is an exact identity on a
proposal schema stripped of $schema and $id, and NOT an identity on the
unstripped file (it relocates the two keys into the top-level
description text). The harness strips first; this test pins the order so
an SDK upgrade that changes the transform reddens CI. Keyless: the
transform is pure local code, no client, no network.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import anthropic
import pytest

from metricmine.agents.harness import load_proposal_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = REPO_ROOT / "docs" / "spec" / "agent-layer"

SCHEMAS = [
    "gold-mapping-proposal.schema.json",
    "silver-cleanup-proposal.schema.json",
    "table-contract-proposal.schema.json",
]


@pytest.mark.parametrize("name", SCHEMAS)
def test_transform_is_identity_on_stripped_schema(name: str) -> None:
    raw = json.loads((SPEC_DIR / name).read_text(encoding="utf-8"))
    stripped = {k: v for k, v in raw.items() if k not in ("$schema", "$id")}
    assert anthropic.transform_schema(copy.deepcopy(stripped)) == stripped


@pytest.mark.parametrize("name", SCHEMAS)
def test_transform_is_not_identity_unstripped(name: str) -> None:
    raw = json.loads((SPEC_DIR / name).read_text(encoding="utf-8"))
    transformed = anthropic.transform_schema(copy.deepcopy(raw))
    assert transformed != raw
    # The header keys are relocated into the description text.
    assert transformed.get("description") != raw.get("description")


@pytest.mark.parametrize("name", SCHEMAS)
def test_harness_loader_strips_first(name: str) -> None:
    local_schema, wire_schema = load_proposal_schema(SPEC_DIR / name)
    assert "$schema" not in local_schema and "$id" not in local_schema
    assert wire_schema == local_schema
