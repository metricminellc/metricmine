"""The CLI surface, keyless (D-24, D-34).

Spec: docs/spec/agent-layer.md §4. --help must work with no key; an
unlisted model must refuse before any network call.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _keyless_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("MM_PROPOSER_MODEL", None)
    return env


def test_help_exits_zero_keyless() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "metricmine.agents", "--help"],
        capture_output=True,
        env=_keyless_env(),
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0


def test_bogus_model_exits_one_without_a_network_call() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "metricmine.agents",
            "propose",
            "mapping",
            "--model",
            "bogus",
        ],
        capture_output=True,
        text=True,
        env=_keyless_env(),
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 1
    assert "allow-list" in proc.stderr


def test_keyless_propose_refuses_and_writes_nothing() -> None:
    # The subprocess resolves the real repo root, where a gitignored
    # proposals/ outbox may already exist: snapshot it and assert the
    # refusal changes nothing, which also covers the fresh-clone case
    # where the folder must not appear at all.
    outbox = REPO_ROOT / "proposals"

    def snapshot() -> tuple[bool, list[str]]:
        if not outbox.exists():
            return False, []
        return True, sorted(str(p) for p in outbox.rglob("*"))

    before = snapshot()
    proc = subprocess.run(
        [sys.executable, "-m", "metricmine.agents", "propose", "mapping"],
        capture_output=True,
        text=True,
        env=_keyless_env(),
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 1
    assert "ANTHROPIC_API_KEY is not set" in proc.stderr
    assert snapshot() == before
