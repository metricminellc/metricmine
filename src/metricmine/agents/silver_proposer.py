"""Thin binding: the silver cleanup proposer at stance `cleanup`.

Spec: docs/spec/agent-layer.md Appendix C (D-21, D-35 HOOK 1). Bronze
profile in, draft ODCS cleanup contract out. All behavior lives in the
shared harness; this module only binds the config stance block to the
cleanup validator and renderer.
"""

from __future__ import annotations

from pathlib import Path

from metricmine.agents.harness import ProposerSpec, load_agents_config
from metricmine.agents.render import render_cleanup
from metricmine.agents.validate import validate_cleanup

NAME = "silver-cleanup-proposer"
VERSION = "0.1.0"
STANCE = "cleanup"


def build_spec(repo_root: Path) -> ProposerSpec:
    stance_cfg = load_agents_config(repo_root)["silver"]["stances"][STANCE]
    return ProposerSpec(
        name=NAME,
        version=VERSION,
        stance=STANCE,
        profile_dir=repo_root / stance_cfg["profile_dir"],
        prompt_path=repo_root / stance_cfg["prompt"],
        proposal_schema=repo_root / stance_cfg["proposal_schema"],
        contract_schema=None,
        target_contract=repo_root / stance_cfg["target_contract"],
        render=render_cleanup,
        validate=validate_cleanup,
    )
