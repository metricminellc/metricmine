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


def build_spec(repo_root: Path) -> ProposerSpec:
    stance_cfg = load_agents_config(repo_root)["mapping"]["stances"][STANCE]
    return ProposerSpec(
        name=NAME,
        version=VERSION,
        stance=STANCE,
        profile_dir=repo_root / stance_cfg["profile_dir"],
        prompt_path=repo_root / stance_cfg["prompt"],
        proposal_schema=repo_root / stance_cfg["proposal_schema"],
        contract_schema=repo_root / stance_cfg["contract_schema"],
        target_contract=repo_root / stance_cfg["target_contract"],
        render=render_mapping,
        validate=validate_mapping,
    )
