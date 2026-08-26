"""The amend render: patch semantics over the committed document (D-35).

The stance addendum's probe measured why patch semantics exist: a
regenerate-style render of a one-column amendment rewrote six of nine
carried descriptions and destroyed committed examples. These tests hold
apply_changes and render_amend to the remedy: the diff IS the declared
change set. Deterministic, keyless, against the real committed contract.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from metricmine.agents.render import (
    Provenance,
    amends_contract_stamp,
    apply_changes,
    canonical_contract_bytes,
    render_amend,
    to_yaml,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = REPO_ROOT / "contracts" / "silver_invoice_lines.odcs.yaml"


@pytest.fixture(scope="module")
def committed_bytes() -> bytes:
    return CONTRACT.read_bytes()


@pytest.fixture(scope="module")
def committed(committed_bytes: bytes) -> dict:
    return yaml.safe_load(committed_bytes.decode("utf-8"))


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


@pytest.fixture(scope="module")
def provenance(committed: dict, committed_bytes: bytes) -> Provenance:
    return Provenance(
        proposed_by="silver-cleanup-proposer",
        proposer_version="0.1.0",
        prompt_version="1.0.0",
        model_id="claude-sonnet-5",
        profile_hash="sha256:" + "e" * 64,
        proposed_at="2026-08-25",
        extras={
            "proposerStance": "amend",
            "amendsContract": amends_contract_stamp(
                committed, committed_bytes
            ),
        },
    )


def _property(document: dict, name: str) -> dict:
    return next(
        p for p in document["schema"][0]["properties"] if p["name"] == name
    )


def test_the_patch_moves_only_the_declared_change(
    committed: dict, example: dict
) -> None:
    patched = apply_changes(committed, example)
    assert (
        _property(patched, "quantity")["description"]
        == example["changes"][0]["after"]
    )
    for name in (
        "invoice_id",
        "is_cancellation",
        "stock_code",
        "product_description",
        "invoiced_at",
        "unit_price",
        "customer_id",
        "country",
    ):
        assert _property(patched, name) == _property(committed, name)
    assert patched["description"] == committed["description"]
    assert (
        patched["schema"][0]["quality"] == committed["schema"][0]["quality"]
    )
    assert (
        _property(patched, "invoice_id")["examples"]
        == _property(committed, "invoice_id")["examples"]
    )


def test_the_committed_document_is_never_mutated(
    committed: dict, example: dict
) -> None:
    snapshot = copy.deepcopy(committed)
    apply_changes(committed, example)
    assert committed == snapshot


def test_render_amend_bumps_by_the_derived_class(
    committed: dict, example: dict, provenance: Provenance
) -> None:
    document = render_amend(committed, example, provenance, "9.9.9")
    assert document["version"] == "1.1.1"
    assert document["status"] == "draft"


def test_provenance_is_restamped_and_decisions_carried(
    committed: dict, example: dict, provenance: Provenance
) -> None:
    document = render_amend(committed, example, provenance, "ignored")
    entries = {
        entry["property"]: entry["value"]
        for entry in document["customProperties"]
    }
    assert entries["proposedBy"] == "silver-cleanup-proposer"
    assert entries["proposerStance"] == "amend"
    assert entries["amendsContract"].startswith(
        "silver_invoice_lines@1.1.0#sha256:"
    )
    assert entries["decisionCancellations"] == "retained-and-flagged"
    assert (
        entries["decisionNegativeNoncancellationQuantities"]
        == "zero-price-adjustment-lines-documented"
    )
    ordered = [entry["property"] for entry in document["customProperties"]]
    assert ordered[:8] == [
        "proposedBy",
        "proposerVersion",
        "promptVersion",
        "modelId",
        "profileHash",
        "proposedAt",
        "proposerStance",
        "amendsContract",
    ]


def test_an_added_column_appends_optional_and_defers_the_follow_up(
    committed: dict, example: dict, provenance: Provenance
) -> None:
    proposal = copy.deepcopy(example)
    proposal["changes"].append(
        {
            "kind": "add_column",
            "column": "line_note",
            "before": "",
            "after": "VARCHAR",
            "rationale": "intent adds a note column",
        }
    )
    proposal["changes"].append(
        {
            "kind": "required_change",
            "column": "line_note",
            "before": "false",
            "after": "true",
            "rationale": "declared follow-up (F-28)",
        }
    )
    proposal["columns"].append(
        {
            "name": "line_note",
            "logical_type": "string",
            "physical_type": "VARCHAR",
            "required": False,
            "description": "a reviewer-facing note",
            "rationale": "intent",
        }
    )
    document = apply_changes(committed, proposal)
    added = document["schema"][0]["properties"][-1]
    assert added["name"] == "line_note"
    assert added["required"] is False


def test_a_drop_removes_exactly_that_column(
    committed: dict, example: dict
) -> None:
    proposal = copy.deepcopy(example)
    proposal["changes"] = [
        {
            "kind": "drop_column",
            "column": "product_description",
            "before": "VARCHAR",
            "after": "",
            "rationale": "operator intent",
        }
    ]
    proposal["columns"] = [
        c for c in proposal["columns"] if c["name"] != "product_description"
    ]
    document = apply_changes(committed, proposal)
    names = [p["name"] for p in document["schema"][0]["properties"]]
    assert "product_description" not in names
    assert len(names) == len(committed["schema"][0]["properties"]) - 1


def test_a_rule_change_adds_through_the_stable_prose_renderer(
    committed: dict, example: dict
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
    proposal["quality_rules"].append(
        {
            "kind": "not_null",
            "column": "country",
            "values": [],
            "rationale": "null_rate 0.0",
        }
    )
    document = apply_changes(committed, proposal)
    country = _property(document, "country")
    assert country["quality"][0]["description"] == "country is never null"
    assert country["quality"][0]["severity"] == "error"


def test_rendering_twice_produces_identical_bytes(
    committed: dict, example: dict, provenance: Provenance
) -> None:
    header = ["Draft proposed for the render determinism test."]
    first = to_yaml(render_amend(committed, example, provenance, "x"), header)
    second = to_yaml(
        render_amend(committed, example, provenance, "x"), header
    )
    assert first == second


def test_canonical_bytes_are_the_committed_file_bytes(
    committed_bytes: bytes,
) -> None:
    import hashlib

    expected = "sha256:" + hashlib.sha256(committed_bytes).hexdigest()
    assert canonical_contract_bytes(committed_bytes) == expected


def test_the_stamp_and_the_staleness_recheck_share_one_digest(
    committed_bytes: bytes, committed: dict
) -> None:
    """Amendment I's canonical bytes and the harness raw-byte staleness
    hash are the SAME definition; the Session Q carry-forward pinned."""
    from metricmine.agents.harness import GovernedInput, recheck_inputs

    digest = canonical_contract_bytes(committed_bytes)
    stamp = amends_contract_stamp(committed, committed_bytes)
    assert stamp == f"silver_invoice_lines@1.1.0#{digest}"
    bound = GovernedInput(
        kind="committed_contract",
        path=str(CONTRACT),
        content_hash=digest,
        schema_version="1.1.0",
    )
    assert recheck_inputs([bound]) == []
