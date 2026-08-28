"""The Makefile's proposer and replay targets, statically, keyless (D-24).

Spec: docs/spec/agent-layer.md §4 and CLAUDE.md rule 17: `make demo` must
always run with no API key, and the regenerate path chains the proposers
live. This module parses the Makefile rather than running it, so the
guarantee that the replay chain never invokes a proposer is a CI
assertion rather than prose. Adding a target that breaks the chain fails
here before it can fail on a machine without a key.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MAKEFILE = REPO_ROOT / "Makefile"

_TARGET = re.compile(r"^([A-Za-z0-9_./$()-]+):(?!=)\s*(.*)$")
_PROPOSER_MARKERS = ("metricmine.agents", "propose", "ANTHROPIC")


def _parse() -> dict[str, tuple[list[str], list[str]]]:
    """target -> (prerequisites, recipe lines), comments and variables skipped."""
    targets: dict[str, tuple[list[str], list[str]]] = {}
    current: str | None = None
    for raw in MAKEFILE.read_text(encoding="utf-8").splitlines():
        if raw.startswith("\t"):
            if current is not None:
                targets[current][1].append(raw.strip())
            continue
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(".PHONY"):
            continue
        match = _TARGET.match(line)
        if match and "=" not in line.split(":")[0]:
            current = match.group(1)
            targets[current] = (match.group(2).split(), [])
        else:
            current = None
    return targets


def _chain(targets: dict, name: str, seen: set[str] | None = None) -> list[str]:
    """Every recipe line reachable from a target through its prerequisites
    and through `$(MAKE) <target>` recipe lines."""
    seen = seen or set()
    if name in seen or name not in targets:
        return []
    seen.add(name)
    prerequisites, recipe = targets[name]
    lines = list(recipe)
    for prerequisite in prerequisites:
        lines += _chain(targets, prerequisite, seen)
    for line in recipe:
        for sub in re.findall(r"\$\(MAKE\)\s+([A-Za-z0-9_-]+)", line):
            lines += _chain(targets, sub, seen)
    return lines


def test_propose_targets_run_one_proposer_each() -> None:
    targets = _parse()
    for name, proposer in (("propose-silver", "silver"), ("propose-mapping", "mapping")):
        prerequisites, recipe = targets[name]
        assert prerequisites == []
        assert len(recipe) == 1
        assert recipe[0].startswith(
            f"uv run python -m metricmine.agents propose {proposer}"
        )
        assert "$(MODEL_FLAG)" in recipe[0]  # the D-34 per-run override


def test_regenerate_chains_the_proposers_in_pipeline_order() -> None:
    targets = _parse()
    prerequisites, recipe = targets["regenerate"]
    assert prerequisites == ["propose-silver", "propose-mapping"]
    assert recipe == []


def test_demo_is_the_keyless_replay_and_never_invokes_a_proposer() -> None:
    targets = _parse()
    prerequisites, recipe = targets["demo"]
    assert prerequisites == ["ingest"]
    assert any("dbt build" in line and "--target local" in line for line in recipe)
    assert any("$(MAKE) export-demo" in line for line in recipe)
    for line in _chain(targets, "demo"):
        for marker in _PROPOSER_MARKERS:
            assert marker not in line, f"demo chain invokes a proposer: {line!r}"


def test_eval_agents_is_the_live_lane() -> None:
    targets = _parse()
    prerequisites, recipe = targets["eval-agents"]
    assert prerequisites == []
    assert len(recipe) == 1
    assert recipe[0].startswith("uv run python -m metricmine.agents eval")
    assert "$(MODEL_FLAG)" in recipe[0]  # the D-34 per-run override


def test_dbt_lines_follow_the_repo_root_invocation_convention() -> None:
    targets = _parse()
    for line in _chain(targets, "demo"):
        if "uv run dbt" in line:
            assert "--project-dir transform" in line
            assert "--profiles-dir transform" in line


def test_propose_describe_carries_table_model_and_oracle_flags() -> None:
    targets = _parse()
    prerequisites, recipe = targets["propose-describe"]
    assert prerequisites == []
    assert len(recipe) == 1
    assert recipe[0].startswith(
        "uv run python -m metricmine.agents propose describe"
    )
    assert '--table "$(TABLE)"' in recipe[0]
    assert "$(MODEL_FLAG)" in recipe[0]  # the D-34 per-run override
    assert "$(ORACLE_FLAG)" in recipe[0]  # the D-25 agreement study


def test_adoption_tools_are_deterministic_module_calls() -> None:
    # The adoption tools are code, never agents (D-10 Amendment G): their
    # recipes call the adoption package and never a proposer or the key.
    targets = _parse()
    for name, subcommand in (
        ("verify-grain", "verify-grain"),
        ("enforce-properties", "enforce-properties"),
    ):
        prerequisites, recipe = targets[name]
        assert prerequisites == []
        assert len(recipe) == 1
        assert recipe[0].startswith(
            f"uv run python -m metricmine.adoption {subcommand}"
        )
        for marker in ("metricmine.agents", "ANTHROPIC"):
            assert marker not in recipe[0], f"{name} reaches a proposer: {recipe[0]!r}"


def test_propose_amend_carries_table_intent_model_and_relax_flags() -> None:
    """propose-amend is one proposer invocation carrying TABLE, the
    verbatim INTENT, the D-34 model override, and the explicit
    relaxation flag (D-35): the narrowing gate is a human decision
    expressed as a make variable, never a default."""
    targets = _parse()
    prerequisites, recipe = targets["propose-amend"]
    assert prerequisites == []
    assert len(recipe) == 1
    line = recipe[0]
    assert line.startswith("uv run python -m metricmine.agents propose amend")
    assert '--table "$(TABLE)"' in line
    assert '--intent "$(INTENT)"' in line
    assert "$(MODEL_FLAG)" in line  # the D-34 per-run override
    assert "$(RELAX_FLAG)" in line  # the D-35 narrowing gate, explicit


def test_propose_queue_is_one_capped_driver_invocation() -> None:
    """propose-queue is deterministic sequencing (D-35): one module
    call carrying the explicit MAX cap, the optional batch INTENT, and
    the D-34 model override; never a loop in make itself."""
    targets = _parse()
    prerequisites, recipe = targets["propose-queue"]
    assert prerequisites == []
    assert len(recipe) == 1
    line = recipe[0]
    assert line.startswith("uv run python -m metricmine.agents propose-queue")
    assert '--max "$(MAX)"' in line
    assert '--intent "$(INTENT)"' in line
    assert "$(MODEL_FLAG)" in line  # the D-34 per-run override
