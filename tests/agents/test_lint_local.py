"""The rendered mapping example through the real datacontract lint.

Spec: docs/spec/agent-layer.md §3 gate 4. Marked local: it shells out to
the isolated datacontract tool (CLAUDE.md rule 1 toolchain), which CI's
keyless pytest lane deselects.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from metricmine.agents.render import (
    Provenance,
    render_cleanup,
    render_mapping,
    to_yaml,
)

pytestmark = pytest.mark.local

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_rendered_mapping_example_lints_clean(tmp_path: Path) -> None:
    example = json.loads(
        (
            REPO_ROOT / "docs" / "spec" / "agent-layer"
            / "example-gold-mapping-proposal.json"
        ).read_text(encoding="utf-8")
    )
    provenance = Provenance(
        proposed_by="gold-mapping-proposer",
        proposer_version="0.1.0",
        prompt_version="1.0.0",
        model_id="claude-sonnet-5",
        profile_hash="sha256:" + "0" * 64,
        proposed_at="2026-08-22",
    )
    document = render_mapping(example, provenance, "1.2.0")
    draft = tmp_path / "draft.odcs.yaml"
    draft.write_text(
        to_yaml(document, ["Lint fixture.", "Review before approval (D-24)."]),
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["datacontract", "lint", str(draft)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_rendered_silver_tmp_draft_lints_clean(tmp_path: Path) -> None:
    # The harness lints the temp file before the rename, so the tool must
    # accept a path ending .odcs.yaml.tmp, and the draft carries the
    # proposerStance extra (D-22 Amendment I); measured true at 1.0.12.
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
        extras={"proposerStance": "cleanup"},
    )
    document = render_cleanup(example, provenance, "1.2.0")
    draft = tmp_path / "draft.odcs.yaml.tmp"
    draft.write_text(
        to_yaml(document, ["Lint fixture.", "Review before approval (D-24)."]),
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["datacontract", "lint", str(draft)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
