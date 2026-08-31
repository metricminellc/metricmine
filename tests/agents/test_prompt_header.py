"""Prompt front-matter contract (D-22): semver header read at runtime.

Spec: docs/spec/agent-layer.md §2 and prompts/README.md. Keyless.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from metricmine.agents.harness import PromptError, parse_prompt_front_matter

_FIXTURE = """---
version: 1.2.3
date: 2026-08-22
changelog: >
  1.2.3: fixture prompt.
---

You are the fixture proposer.
"""


def test_front_matter_parses(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(_FIXTURE, encoding="utf-8")
    meta, body = parse_prompt_front_matter(prompt)
    assert meta["version"] == "1.2.3"
    assert str(meta["date"]) == "2026-08-22"
    assert body.startswith("You are the fixture proposer.")


def test_missing_file_names_the_path(tmp_path: Path) -> None:
    missing = tmp_path / "gold_mapping.md"
    with pytest.raises(PromptError) as excinfo:
        parse_prompt_front_matter(missing)
    assert str(missing) in str(excinfo.value)


def test_missing_version_fails(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "---\ndate: 2026-08-22\n---\n\nBody.\n", encoding="utf-8"
    )
    with pytest.raises(PromptError) as excinfo:
        parse_prompt_front_matter(prompt)
    assert "version" in str(excinfo.value)


def test_no_front_matter_fails(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Just a body, no fences.\n", encoding="utf-8")
    with pytest.raises(PromptError):
        parse_prompt_front_matter(prompt)
