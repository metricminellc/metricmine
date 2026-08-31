"""The three D-35 readiness hooks, exercised beyond today's single use.

Spec: docs/spec/agent-layer.md (D-35; Amendments H and I). Stance is a
config-resolved string (HOOK 1); the user turn is an ordered list of
delimited governed inputs whose hashes are all re-checked (HOOK 2);
provenance extras append after the six Appendix B keys (HOOK 3). A later
stance is a config block plus a prompt plus a validator, never a harness
rewrite; these tests hold the seams open. Keyless.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from metricmine.agents import mapping_proposer, silver_proposer
from metricmine.agents.harness import (
    GovernedInput,
    build_user_content,
    recheck_inputs,
)
from metricmine.agents.render import (
    Provenance,
    grain_rule_description,
    next_version,
    render_cleanup,
)
from metricmine.profiling import canonical

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_specs_carry_their_stance() -> None:
    assert silver_proposer.build_spec(REPO_ROOT).stance == "cleanup"
    assert mapping_proposer.build_spec(REPO_ROOT).stance == "propose"


def test_context_builder_orders_and_delimits_inputs() -> None:
    content = build_user_content(
        [("profile_artifact", "PROFILE"), ("committed_contract", "CONTRACT")]
    )
    assert content == (
        "<profile_artifact>\nPROFILE\n</profile_artifact>\n"
        "<committed_contract>\nCONTRACT\n</committed_contract>"
    )
    assert content.index("profile_artifact") < content.index(
        "committed_contract"
    )


def _fake_profile(path: Path) -> str:
    dataset = {"schema": "silver", "table": "t", "columns": []}
    artifact = {
        "schema_version": "1.0.0",
        "content_hash": canonical.content_hash(dataset),
        "dataset": dataset,
    }
    path.write_text(json.dumps(artifact), encoding="utf-8")
    return artifact["content_hash"]


def test_staleness_rechecks_every_input(tmp_path: Path) -> None:
    profile_path = tmp_path / "v0001.json"
    profile_hash = _fake_profile(profile_path)
    contract_path = tmp_path / "committed.odcs.yaml"
    contract_path.write_text("version: 1.0.0\n", encoding="utf-8")
    contract_hash = (
        "sha256:" + hashlib.sha256(contract_path.read_bytes()).hexdigest()
    )
    inputs = [
        GovernedInput(
            "profile_artifact", str(profile_path), profile_hash, "1.0.0"
        ),
        GovernedInput(
            "committed_contract", str(contract_path), contract_hash, ""
        ),
    ]
    assert recheck_inputs(inputs) == []
    # The SECOND input moves; the re-check must catch it.
    contract_path.write_text("version: 1.1.0\n", encoding="utf-8")
    errors = recheck_inputs(inputs)
    assert len(errors) == 1
    assert "committed_contract" in errors[0]


def test_extras_append_after_the_six_provenance_keys() -> None:
    example = json.loads(
        (
            REPO_ROOT / "docs" / "spec" / "agent-layer"
            / "example-silver-cleanup-proposal.json"
        ).read_text(encoding="utf-8")
    )
    provenance = Provenance(
        proposed_by="silver-cleanup-proposer",
        proposer_version="0.1.0",
        prompt_version="1.0.0",
        model_id="claude-sonnet-5",
        profile_hash="sha256:" + "0" * 64,
        proposed_at="2026-08-22",
        extras={
            "proposerStance": "amend",
            "amendsContract": "silver_invoice_lines@1.1.0#sha256:abc",
        },
    )
    rendered = render_cleanup(example, provenance, "1.2.0")
    keys = [entry["property"] for entry in rendered["customProperties"]]
    assert keys[6] == "proposerStance"
    assert keys[7] == "amendsContract"
    assert all(key.startswith("decision") for key in keys[8:])


def test_next_version_bumps() -> None:
    assert next_version("1.1.0", "minor") == "1.2.0"
    assert next_version("1.1.0", "major") == "2.0.0"
    assert next_version("1.1.0", "patch") == "1.1.1"


def test_rule_descriptions_never_carry_rationale_text() -> None:
    # F-27's naming nit: sync names generated test files from rule
    # descriptions, so they are stable prose fixed in the renderer.
    example = json.loads(
        (
            REPO_ROOT / "docs" / "spec" / "agent-layer"
            / "example-silver-cleanup-proposal.json"
        ).read_text(encoding="utf-8")
    )
    provenance = Provenance(
        proposed_by="silver-cleanup-proposer",
        proposer_version="0.1.0",
        prompt_version="1.0.0",
        model_id="claude-sonnet-5",
        profile_hash="sha256:" + "0" * 64,
        proposed_at="2026-08-22",
    )
    rendered = render_cleanup(example, provenance, "1.2.0")
    rules = rendered["schema"][0]["quality"]
    rationales = [c["rationale"] for c in example["columns"]] + [
        d["rationale"] for d in example["decisions"]
    ]
    for rule in rules:
        for rationale in rationales:
            assert rationale not in rule["description"]
    assert rules[1]["description"] == grain_rule_description(
        example["grain_keys"]
    )
