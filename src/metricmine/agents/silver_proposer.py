"""Thin binding: the silver cleanup proposer at stance `cleanup`.

Spec: docs/spec/agent-layer.md Appendix C (D-21, D-35 HOOK 1). Bronze
profile in, draft ODCS cleanup contract out. All behavior lives in the
shared harness; this module only binds the config stance block to the
cleanup validator and renderer.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from metricmine.agents.harness import ProposerSpec, load_agents_config
from metricmine.agents.render import render_amend, render_cleanup, render_describe
from metricmine.agents.validate import (
    validate_amend,
    validate_cleanup,
    validate_describe,
)

NAME = "silver-cleanup-proposer"
VERSION = "0.1.0"
STANCE = "cleanup"


def build_spec(
    repo_root: Path, source: str | None = None, target: str | None = None
) -> ProposerSpec:
    """The cleanup stance over one bronze table's profile.

    Without a source the stance runs over the configured table (the
    retail sample, the committed default). With ``source`` (D-41, the
    multi-source proof) the profile directory is profiles/bronze.<source>/
    and the target contract contracts/<target>.odcs.yaml, where target
    defaults to silver_<source>; the same proposer, the same stance, one
    structured call, so a family of sources is a family of runs and the
    eval lane can score each draft against its human-authored oracle.
    """
    stance_cfg = load_agents_config(repo_root)["silver"]["stances"][STANCE]
    if source:
        profile_dir = repo_root / "profiles" / f"bronze.{source}"
        target_contract = (
            repo_root / "contracts" / f"{target or 'silver_' + source}.odcs.yaml"
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
        contract_schema=None,
        target_contract=target_contract,
        render=render_cleanup,
        validate=validate_cleanup,
    )


def build_describe_spec(repo_root: Path, table: str) -> ProposerSpec:
    """The describe stance over one existing silver table (D-35).

    The stance config block carries the prompt and the proposal schema
    only; the profile directory and the target contract derive from the
    table argument, because describe consumes the TARGET table's own
    profile artifact (profiles/silver.<table>/) and drafts the contract
    that would enforce that table (contracts/<table>.odcs.yaml). Same
    proposer, same provenance identity: a stance is a mode, never a
    third agent (D-10 Amendment G).
    """
    stance_cfg = load_agents_config(repo_root)["silver"]["stances"]["describe"]
    return ProposerSpec(
        name=NAME,
        version=VERSION,
        stance="describe",
        profile_dir=repo_root / "profiles" / f"silver.{table}",
        prompt_path=repo_root / stance_cfg["prompt"],
        proposal_schema=repo_root / stance_cfg["proposal_schema"],
        contract_schema=None,
        target_contract=repo_root / "contracts" / f"{table}.odcs.yaml",
        render=render_describe,
        validate=validate_describe,
    )


def build_amend_spec(
    repo_root: Path, table: str, *, allow_relaxation: bool = False
) -> tuple[ProposerSpec, dict, bytes]:
    """The amend stance over one contracted silver table (D-35).

    Amend consumes three governed inputs: the fresh profile, the
    committed contract it amends, and the operator's intent (D-23
    Amendment H). The committed document is read here ONCE, and its raw
    bytes are the canonical bytes both consumers hash: the
    amendsContract stamp and the staleness re-check (D-22 Amendment I).
    The validator and renderer close over the parsed document, so the
    harness stays stance-agnostic. Returns the spec, the parsed
    committed document, and its raw bytes; the CLI builds the governed
    input and the provenance stamp from the latter two. Same proposer,
    same provenance identity (D-10 Amendment G).
    """
    stance_cfg = load_agents_config(repo_root)["silver"]["stances"]["amend"]
    target = repo_root / "contracts" / f"{table}.odcs.yaml"
    committed_bytes = target.read_bytes()
    committed = yaml.safe_load(committed_bytes.decode("utf-8"))
    spec = ProposerSpec(
        name=NAME,
        version=VERSION,
        stance="amend",
        profile_dir=repo_root / "profiles" / f"silver.{table}",
        prompt_path=repo_root / stance_cfg["prompt"],
        proposal_schema=repo_root / stance_cfg["proposal_schema"],
        contract_schema=None,
        target_contract=target,
        render=lambda proposal, provenance, version: render_amend(
            committed, proposal, provenance, version
        ),
        validate=lambda proposal, profile: validate_amend(
            proposal, profile, committed, allow_relaxation=allow_relaxation
        ),
    )
    return spec, committed, committed_bytes
