"""The recorded live proposals through validator and renderer, keyless (D-25).

Spec: docs/spec/agent-layer.md §5: the render path is tested against
recorded proposals in the existing pytest lane, every CI run, no key.
Each recorded proposal under tests/agents/fixtures/recorded/ is the
validated proposal object from one live eval run (the outbox's
proposal.json, copied under the fixture's label), so these tests hold
the offline path to what the live lane actually produced. Labels come
from config agents.eval.fixtures: a fourth fixture joins the parametrize
with no test edit once its recorded proposal lands.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from metricmine.agents import mapping_proposer, silver_proposer
from metricmine.agents.harness import load_agents_config
from metricmine.agents.render import (
    Provenance,
    render_cleanup,
    render_mapping,
    to_yaml,
)
from metricmine.agents.validate import validate_cleanup, validate_mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORDED = REPO_ROOT / "tests" / "agents" / "fixtures" / "recorded"

FIXTURES = load_agents_config(REPO_ROOT)["eval"]["fixtures"]
LABELS = [f["label"] for f in FIXTURES]
MAPPING_LABELS = [f["label"] for f in FIXTURES if f["proposer"] == "mapping"]

BINDINGS = {
    "silver": (
        validate_cleanup,
        render_cleanup,
        silver_proposer.NAME,
        silver_proposer.STANCE,
    ),
    "mapping": (
        validate_mapping,
        render_mapping,
        mapping_proposer.NAME,
        mapping_proposer.STANCE,
    ),
}


def _fixture(label: str) -> dict:
    return next(f for f in FIXTURES if f["label"] == label)


def _load(label: str) -> tuple[dict, dict, tuple]:
    fixture = _fixture(label)
    proposal = json.loads(
        (RECORDED / f"{label}.proposal.json").read_text(encoding="utf-8")
    )
    profile = json.loads(
        (REPO_ROOT / fixture["profile"]).read_text(encoding="utf-8")
    )
    return proposal, profile, BINDINGS[fixture["proposer"]]


def _provenance(name: str, stance: str) -> Provenance:
    # The frozen mapping schema constrains proposedBy, so the fixed
    # Provenance carries the real proposer name, never a placeholder.
    return Provenance(
        proposed_by=name,
        proposer_version="0.1.0",
        prompt_version="1.0.0",
        model_id="claude-sonnet-5",
        profile_hash="sha256:" + "0" * 64,
        proposed_at="2026-08-24",
        extras={"proposerStance": stance},
    )


@pytest.mark.parametrize("label", LABELS)
def test_recorded_proposal_validates_cleanly(label: str) -> None:
    proposal, profile, (validate, _, _, _) = _load(label)
    assert validate(proposal, profile) == []


@pytest.mark.parametrize("label", LABELS)
def test_recorded_render_twice_is_byte_identical(label: str) -> None:
    proposal, _, (_, render, name, stance) = _load(label)
    provenance = _provenance(name, stance)
    header = ["Recorded fixture.", "Review before approval (D-24)."]
    first = to_yaml(render(proposal, provenance, "1.2.0"), header)
    second = to_yaml(render(proposal, provenance, "1.2.0"), header)
    assert first == second


@pytest.mark.parametrize("label", MAPPING_LABELS)
def test_recorded_mapping_render_validates_against_frozen_schema(
    label: str,
) -> None:
    proposal, _, (_, render, name, stance) = _load(label)
    frozen = json.loads(
        (
            REPO_ROOT / "docs" / "spec" / "engine"
            / "mapping-contract.schema.json"
        ).read_text(encoding="utf-8")
    )
    document = render(proposal, _provenance(name, stance), "1.2.0")
    Draft202012Validator(frozen).validate(document)
