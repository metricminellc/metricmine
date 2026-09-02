"""The contracts/ provenance gate: rule 16 as a CI test.

Governing text: CLAUDE.md rule 16, docs/spec/engine.md Section 9, D-22 with
Amendment I, D-34 (the model allow-list). The Phase 8 hook evaluation named
a CI test over contracts/ as the right mechanism for this rule; Arc 4 lands
it. Every committed contract carries honest provenance customProperties:

- Every contract: proposedBy and a dated proposedAt.
- Agent-proposed (proposedBy is not "human"): proposerVersion,
  promptVersion, an allow-listed modelId, a well-formed profileHash, and a
  proposerStance; the amend stance also carries amendsContract as
  <name>@<version>#sha256:<hash> (Amendment I).
- Hand-written (proposedBy: human): no stance and no agent-only keys, and
  either a well-formed profileHash (profile-derived, the mapping contract)
  or a provenanceNote stating why none exists (pattern-derived, the star:
  absence-with-rationale is honest provenance, a fabricated hash never is).

The validator is a plain function so the negative fixtures below prove the
gate discriminates; the committed contracts are asserted clean one file at
a time so a red run names the offending contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

CONTRACTS_DIR = Path(__file__).resolve().parents[1] / "contracts"
CONTRACT_PATHS = sorted(CONTRACTS_DIR.glob("*.odcs.yaml"))

# D-34: membership changes only by register amendment, and that amendment
# edits this list in the same pull request.
MODEL_ALLOW_LIST = {"claude-sonnet-5", "claude-opus-5", "claude-fable-5"}

STANCES = {"cleanup", "describe", "amend", "propose"}
AGENT_ONLY_KEYS = ("proposerVersion", "promptVersion", "modelId", "proposerStance")

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
AMENDS = re.compile(r"^[a-z0-9_]+@\d+\.\d+\.\d+#sha256:[0-9a-f]{64}$")


def custom_properties(doc: dict) -> dict[str, str]:
    props = {}
    for entry in doc.get("customProperties") or []:
        if isinstance(entry, dict) and "property" in entry:
            props[str(entry["property"])] = str(entry.get("value", ""))
    return props


def provenance_errors(doc: dict) -> list[str]:
    """Every rule-16 violation in one pass; empty means honest provenance."""
    errors: list[str] = []
    props = custom_properties(doc)
    if not props:
        return ["customProperties missing or empty (rule 16)"]

    proposed_by = props.get("proposedBy", "")
    if not proposed_by:
        errors.append("proposedBy missing (rule 16)")
    proposed_at = props.get("proposedAt", "")
    if not DATE.match(proposed_at):
        errors.append(f"proposedAt missing or not a date: {proposed_at!r}")

    profile_hash = props.get("profileHash")
    if profile_hash is not None and not SHA256.match(profile_hash):
        errors.append(f"profileHash malformed: {profile_hash!r} (never fabricate)")

    if proposed_by == "human":
        for key in AGENT_ONLY_KEYS:
            if key in props:
                errors.append(f"{key} on a hand-written contract (rule 16: no stance, no agent keys)")
        if profile_hash is None and not props.get("provenanceNote", "").strip():
            errors.append(
                "hand-written contract with neither profileHash nor provenanceNote "
                "(engine spec section 9: absence needs its rationale)"
            )
    elif proposed_by:
        for key in ("proposerVersion", "promptVersion", "modelId", "profileHash", "proposerStance"):
            if key not in props:
                errors.append(f"{key} missing on an agent-proposed contract (rule 16)")
        for key in ("proposerVersion", "promptVersion"):
            if key in props and not SEMVER.match(props[key]):
                errors.append(f"{key} not semver: {props[key]!r}")
        model = props.get("modelId")
        if model is not None and model not in MODEL_ALLOW_LIST:
            errors.append(f"modelId {model!r} outside the D-34 allow-list")
        stance = props.get("proposerStance")
        if stance is not None and stance not in STANCES:
            errors.append(f"proposerStance {stance!r} is not a D-35 stance")
        if stance == "amend":
            amends = props.get("amendsContract", "")
            if not AMENDS.match(amends):
                errors.append(
                    f"amend stance without a well-formed amendsContract: {amends!r} (Amendment I)"
                )
    return errors


# ---------------------------------------------------------------------------
# The committed contracts are clean, named one at a time.
# ---------------------------------------------------------------------------

def test_contracts_exist() -> None:
    assert CONTRACT_PATHS, f"no contracts found under {CONTRACTS_DIR}"


@pytest.mark.parametrize("path", CONTRACT_PATHS, ids=lambda p: p.name)
def test_committed_contract_provenance(path: Path) -> None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert provenance_errors(doc) == []


# ---------------------------------------------------------------------------
# The gate discriminates: each fixture violates exactly one clause.
# ---------------------------------------------------------------------------

def _human_doc(**overrides) -> dict:
    props = {
        "proposedBy": "human",
        "proposedAt": "2026-08-09",
        "provenanceNote": "pattern-derived; no profileHash exists",
    }
    props.update(overrides)
    return {
        "customProperties": [
            {"property": k, "value": v} for k, v in props.items() if v is not None
        ]
    }


def _agent_doc(**overrides) -> dict:
    props = {
        "proposedBy": "silver-cleanup-proposer",
        "proposerVersion": "0.1.0",
        "promptVersion": "1.0.0",
        "modelId": "claude-sonnet-5",
        "profileHash": "sha256:" + "e" * 64,
        "proposedAt": "2026-08-26",
        "proposerStance": "cleanup",
    }
    props.update(overrides)
    return {
        "customProperties": [
            {"property": k, "value": v} for k, v in props.items() if v is not None
        ]
    }


def test_missing_custom_properties_fails() -> None:
    assert provenance_errors({}) == ["customProperties missing or empty (rule 16)"]


def test_missing_proposed_by_fails() -> None:
    doc = _human_doc()
    doc["customProperties"] = [p for p in doc["customProperties"] if p["property"] != "proposedBy"]
    assert any("proposedBy missing" in e for e in provenance_errors(doc))


def test_undated_proposed_at_fails() -> None:
    assert any("proposedAt" in e for e in provenance_errors(_human_doc(proposedAt="August 9")))


def test_fabricated_hash_fails_everywhere() -> None:
    assert any("malformed" in e for e in provenance_errors(_human_doc(profileHash="sha256:short")))
    assert any("malformed" in e for e in provenance_errors(_agent_doc(profileHash="deadbeef")))


def test_human_with_stance_fails() -> None:
    assert any(
        "hand-written" in e for e in provenance_errors(_human_doc(proposerStance="amend"))
    )


def test_human_without_hash_or_note_fails() -> None:
    assert any(
        "neither profileHash nor provenanceNote" in e
        for e in provenance_errors(_human_doc(provenanceNote=None))
    )


def test_human_with_hash_needs_no_note() -> None:
    doc = _human_doc(provenanceNote=None, profileHash="sha256:" + "a" * 64)
    assert provenance_errors(doc) == []


def test_agent_missing_key_fails() -> None:
    assert any("modelId missing" in e for e in provenance_errors(_agent_doc(modelId=None)))


def test_agent_model_outside_allow_list_fails() -> None:
    assert any(
        "allow-list" in e for e in provenance_errors(_agent_doc(modelId="claude-haiku-5"))
    )


def test_agent_unknown_stance_fails() -> None:
    assert any("D-35" in e for e in provenance_errors(_agent_doc(proposerStance="rewrite")))


def test_amend_requires_amends_contract() -> None:
    assert any(
        "amendsContract" in e for e in provenance_errors(_agent_doc(proposerStance="amend"))
    )
    clean = _agent_doc(
        proposerStance="amend",
        amendsContract="silver_invoice_lines@1.1.0#sha256:" + "c" * 64,
    )
    assert provenance_errors(clean) == []
