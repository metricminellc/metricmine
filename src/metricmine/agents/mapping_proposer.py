"""Thin binding: the gold mapping proposer at stance `propose`.

Spec: docs/spec/agent-layer.md Appendix C (D-21, D-35 HOOK 1). Silver
profile in, draft ODCS mapping contract out; the rendered document is
additionally validated against the frozen mapping-contract schema
(F-26: the projection travels to the API, the frozen schema judges the
render). All behavior lives in the shared harness.
"""

from __future__ import annotations

from pathlib import Path

from metricmine.agents.harness import ProposerSpec, load_agents_config
from metricmine.agents.render import render_mapping
from metricmine.agents.validate import validate_mapping

NAME = "gold-mapping-proposer"
VERSION = "0.1.0"
STANCE = "propose"


def default_target(table: str) -> str:
    """gold_<category>_mapping for silver_<category>; the whole table
    name is the category when the silver_ prefix is absent."""
    stem = table[len("silver_"):] if table.startswith("silver_") else table
    return f"gold_{stem}_mapping"


def build_spec(
    repo_root: Path, table: str | None = None, target: str | None = None
) -> ProposerSpec:
    """The propose stance over one silver table's profile.

    Without a table the stance runs over the configured table (the
    retail sample). With ``table`` (D-41) the profile directory is
    profiles/silver.<table>/ and the target contract
    contracts/<target>.odcs.yaml, where target defaults to
    gold_<category>_mapping; one structured call either way.
    """
    stance_cfg = load_agents_config(repo_root)["mapping"]["stances"][STANCE]
    if table:
        profile_dir = repo_root / "profiles" / f"silver.{table}"
        target_contract = (
            repo_root / "contracts" / f"{target or default_target(table)}.odcs.yaml"
        )
    else:
        profile_dir = repo_root / stance_cfg["profile_dir"]
        target_contract = repo_root / (target and f"contracts/{target}.odcs.yaml" or stance_cfg["target_contract"])
    return ProposerSpec(
        name=NAME,
        version=VERSION,
        stance=STANCE,
        profile_dir=profile_dir,
        prompt_path=repo_root / stance_cfg["prompt"],
        proposal_schema=repo_root / stance_cfg["proposal_schema"],
        contract_schema=repo_root / stance_cfg["contract_schema"],
        target_contract=target_contract,
        render=render_mapping,
        validate=validate_mapping,
    )
