"""The shared proposer call: structured outputs, retry budget, record.

Spec: docs/spec/agent-layer.md §1–§4 (D-21 as amended by Amendment F,
D-22, D-23 as amended by Amendment H, D-24, D-34) and CLAUDE.md rules
15–17. One structured call per run; no tools, no MCP, no loops. Retries
are bounded and apply only to errors the model can repair (errors fed
back verbatim, then fail closed with nothing but the raw response
preserved); staleness, integrity, and API errors fail closed at once
(S-N-1). Drafts and records land only in the gitignored outbox,
temp-then-rename (the profiler writer's discipline).

Three D-35 readiness hooks, deliberately ahead of need:
- HOOK 1: `stance` is a plain string resolved from the config block
  agents.<proposer>.stances.<stance>; a later stance is a config block
  plus a prompt plus a validate callable, no harness change.
- HOOK 2: the user turn is built from an ORDERED list of governed
  inputs, each rendered inside its own delimiter tag named by kind
  (today only <profile_artifact>); the record carries inputs[] and the
  staleness re-check re-reads and re-hashes EVERY input.
- HOOK 3 lives in render.py: provenance extras append after the six
  Appendix B keys.

This is a CLI, not the stdio server: stdout carries the run summary and
stderr the diagnostics (rule 18's stdout discipline governs
src/metricmine/server/ only).
"""

from __future__ import annotations

import copy
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import anthropic
import yaml
from jsonschema import Draft202012Validator

from metricmine.agents import models
from metricmine.agents.render import (
    Provenance,
    dump_yaml,
    next_version,
    to_yaml,
)
from metricmine.agents.validate import check_staleness
from metricmine.profiling import canonical, writer

LintRunner = Callable[[Path], tuple[bool, str]]

_INSTALL_REMEDY = (
    "datacontract is not on PATH; install the pinned isolated tool "
    "(CLAUDE.md rule 1): uv tool install --python 3.12 "
    '"datacontract-cli[duckdb]==1.0.12"'
)


@dataclass(frozen=True)
class ProposerSpec:
    """One proposer bound to one stance (HOOK 1)."""

    name: str
    version: str
    stance: str
    profile_dir: Path
    prompt_path: Path
    proposal_schema: Path
    contract_schema: Path | None
    target_contract: Path
    render: Callable[[dict, Provenance, str], dict]
    validate: Callable[[dict, dict], list[str]]


@dataclass(frozen=True)
class GovernedInput:
    """One governed input bound into the proposal (HOOK 2, Amendment H)."""

    kind: str
    path: str
    content_hash: str
    schema_version: str


@dataclass(frozen=True)
class AgentsConfig:
    effort: str
    max_tokens: int
    max_retries: int
    outbox_dir: str


class PromptError(ValueError):
    """The prompt file is missing or its front matter is incomplete."""


def load_agents_config(repo_root: Path) -> dict:
    config_path = repo_root / "config" / "default.yaml"
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))["agents"]


def parse_prompt_front_matter(path: Path) -> tuple[dict, str]:
    """YAML front matter (version, date, changelog) plus the prompt body."""
    if not path.exists():
        raise PromptError(
            f"prompt file {path} does not exist; prompt bodies land by "
            f"pull request (D-22) in the prompt PR"
        )
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise PromptError(f"prompt {path} carries no YAML front matter block")
    rest = text[4:]
    fence = rest.index("\n---\n")
    meta = yaml.safe_load(rest[:fence])
    body = rest[fence + len("\n---\n") :].lstrip("\n")
    if not isinstance(meta, dict) or "version" not in meta:
        raise PromptError(
            f"prompt {path} front matter carries no version (D-22: the "
            f"semver header is the lineage)"
        )
    return meta, body


def load_proposal_schema(path: Path) -> tuple[dict, dict]:
    """The local validator schema and the wire schema, strip-first.

    $schema and $id are stripped BEFORE anthropic.transform_schema:
    measured at 1.0.0, the transform is an exact identity on the stripped
    schema, while on the unstripped file it relocates the two keys into
    the top-level description text (tests/agents/test_transform_noop.py
    pins the order).
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    stripped = {k: v for k, v in raw.items() if k not in ("$schema", "$id")}
    transformed = anthropic.transform_schema(copy.deepcopy(stripped))
    return stripped, transformed


def build_user_content(inputs: list[tuple[str, str]]) -> str:
    """Each governed input inside its own delimiter tag, in order (HOOK 2)."""
    return "\n".join(
        f"<{kind}>\n{text}\n</{kind}>" for kind, text in inputs
    )


def recheck_inputs(inputs: list[GovernedInput]) -> list[str]:
    """Re-read and re-hash EVERY governed input (D-23 Amendment H)."""
    errors: list[str] = []
    for bound in inputs:
        path = Path(bound.path)
        if bound.kind == "profile_artifact":
            errors.extend(check_staleness(path, bound.content_hash))
            continue
        try:
            current = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            errors.append(f"staleness: cannot re-read {path}: {exc}")
            continue
        if current != bound.content_hash:
            errors.append(
                f"staleness: input {bound.kind} at {path} moved to {current} "
                f"after binding to {bound.content_hash}"
            )
    return errors


def _replace_bytes(path: Path, data: bytes) -> None:
    # Temp-then-rename in the same directory (the profiler writer's
    # discipline): a crash mid-write never leaves a truncated file.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _default_lint_runner(path: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        ["datacontract", "lint", str(path)], capture_output=True, text=True
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def _first_text_block(response: Any) -> str:
    for block in response.content:
        text = getattr(block, "text", None)
        if text is not None:
            return text
    raise ValueError("response carries no text block")


def _fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def _select_profile(
    spec: ProposerSpec, profile: str | None
) -> tuple[Path | None, str | None]:
    newest = writer.latest_version(spec.profile_dir)
    if profile is not None:
        path = Path(profile)
        if newest and path != spec.profile_dir / f"v{newest:04d}.json":
            print(
                f"warning: --profile {path} is not the newest artifact "
                f"in {spec.profile_dir} (v{newest:04d})",
                file=sys.stderr,
            )
        return path, None
    if not newest:
        return None, f"no profile artifact found under {spec.profile_dir}"
    return spec.profile_dir / f"v{newest:04d}.json", None


def _rationale_lines(proposal: dict) -> list[str]:
    lines: list[str] = []
    if "grain_rationale" in proposal:
        lines.append(f"grain: {proposal['grain_rationale']}")
    for decision in proposal.get("decisions", []):
        lines.append(f"{decision['key']}: {decision['rationale']}")
    return lines


def run_proposer(
    spec: ProposerSpec,
    repo_root: Path,
    *,
    profile: str | None = None,
    model_flag: str | None = None,
    client: Any = None,
    lint_runner: LintRunner | None = None,
    now: datetime | None = None,
) -> int:
    """One governed proposer run. 0 = draft written; 1 = refused before
    any call; 2 = failed closed after the retry budget or on staleness."""
    raw_cfg = load_agents_config(repo_root)
    cfg = AgentsConfig(
        effort=raw_cfg["effort"],
        max_tokens=raw_cfg["max_tokens"],
        max_retries=raw_cfg["max_retries"],
        outbox_dir=raw_cfg["outbox_dir"],
    )

    # Preconditions, all before any API call, all exit 1.
    try:
        resolved = models.resolve_model(model_flag)
    except models.ModelNotAllowedError as exc:
        return _fail(str(exc))
    if client is None and not os.environ.get("ANTHROPIC_API_KEY"):
        # Presence only: the value is never read beyond truthiness, never
        # compared, never printed, never logged. Tests inject a client, so
        # the check applies only when the harness constructs one itself.
        return _fail(
            "ANTHROPIC_API_KEY is not set; load it into this shell before "
            "running a proposer (make demo and the test lane never need it)"
        )
    if lint_runner is None:
        if shutil.which("datacontract") is None:
            return _fail(_INSTALL_REMEDY)
        lint_runner = _default_lint_runner
    try:
        prompt_meta, prompt_body = parse_prompt_front_matter(spec.prompt_path)
    except PromptError as exc:
        return _fail(str(exc))
    profile_path, error = _select_profile(spec, profile)
    if profile_path is None:
        return _fail(error or "no profile artifact")
    try:
        artifact = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _fail(f"cannot read profile {profile_path}: {exc}")
    recomputed = canonical.content_hash(artifact["dataset"])
    stored = artifact.get("content_hash")
    if recomputed != stored:
        return _fail(
            f"profile {profile_path} fails integrity: stored content_hash "
            f"{stored} disagrees with the recomputed dataset hash "
            f"{recomputed}"
        )
    profile_hash = stored
    local_schema, wire_schema = load_proposal_schema(spec.proposal_schema)
    proposal_validator = Draft202012Validator(local_schema)
    contract_validator = None
    if spec.contract_schema is not None:
        contract_validator = Draft202012Validator(
            json.loads(spec.contract_schema.read_text(encoding="utf-8"))
        )

    committed_version = None
    committed_id = None
    if spec.target_contract.exists():
        committed = yaml.safe_load(
            spec.target_contract.read_text(encoding="utf-8")
        )
        committed_version = committed.get("version")
        committed_id = committed.get("id")
    # The version bumps the committed target only when the draft carries
    # the SAME contract id (a regeneration); a first proposal for another
    # id starts its own line at 1.0.0, whatever the configured target.
    regen_version = next_version(committed_version, "minor")

    now = now or datetime.now(timezone.utc)
    created_at = now.isoformat()
    provenance = Provenance(
        proposed_by=spec.name,
        proposer_version=spec.version,
        prompt_version=str(prompt_meta["version"]),
        model_id=resolved.model_id,
        profile_hash=profile_hash,
        proposed_at=now.date().isoformat(),
        extras={"proposerStance": spec.stance},
    )

    canonical_text = (
        canonical.canonical_bytes(artifact).decode("utf-8").rstrip("\n")
    )
    inputs = [
        GovernedInput(
            kind="profile_artifact",
            path=str(profile_path),
            content_hash=profile_hash,
            schema_version=str(artifact.get("schema_version", "")),
        )
    ]
    user_content = build_user_content([("profile_artifact", canonical_text)])

    run_dir = (
        repo_root
        / cfg.outbox_dir
        / spec.name
        / (
            f"{now.strftime('%Y%m%dT%H%M%SZ')}_"
            f"{profile_hash.removeprefix('sha256:')[:8]}"
        )
    )
    draft_path = run_dir / "draft.odcs.yaml"
    draft_tmp = run_dir / "draft.odcs.yaml.tmp"

    if client is None:
        # Key from the environment inside the SDK; never read or log it.
        client = anthropic.Anthropic()

    messages: list[dict] = [{"role": "user", "content": user_content}]
    usage = {"input_tokens": 0, "output_tokens": 0}
    response_id = None
    stop_reason = None
    raw_text = ""
    attempts = 0
    validation: dict = {}
    proposal: dict | None = None
    draft_text: str | None = None
    stale = False

    api_error: dict | None = None
    while attempts < cfg.max_retries + 1:
        attempts += 1
        try:
            response = client.messages.create(
                model=resolved.model_id,
                max_tokens=cfg.max_tokens,
                system=prompt_body,
                messages=messages,
                output_config={
                    "effort": cfg.effort,
                    "format": {"type": "json_schema", "schema": wire_schema},
                },
            )
        except (anthropic.APIConnectionError, anthropic.APIError) as exc:
            # The first is a subclass of the second; both named for the
            # reader. Transport and API failures are not errors the model
            # can repair (S-N-1): fail closed at once, record the class
            # and message, write no draft. The SDK's own bounded retry for
            # transient status codes has already run inside the call.
            api_error = {"class": type(exc).__name__, "message": str(exc)}
            validation = {
                "schema_pass": False,
                "groundedness_pass": False,
                "completeness_pass": False,
                "staleness_pass": False,
                "lint_pass": False,
                "attempts": attempts,
                "errors": [f"api error: {type(exc).__name__}: {exc}"],
            }
            break
        response_id = getattr(response, "id", None)
        stop_reason = response.stop_reason
        usage["input_tokens"] += response.usage.input_tokens
        usage["output_tokens"] += response.usage.output_tokens
        raw_text = _first_text_block(response)

        errors: list[str] = []
        validation = {
            "schema_pass": False,
            "groundedness_pass": False,
            "completeness_pass": False,
            "staleness_pass": False,
            "lint_pass": False,
            "attempts": attempts,
            "errors": [],
        }
        proposal = None
        draft_text = None
        if stop_reason != "end_turn":
            errors.append(
                f"response stopped on {stop_reason!r}, not end_turn; the "
                f"proposal is incomplete"
            )
        else:
            try:
                proposal = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                errors.append(f"response is not valid JSON: {exc}")
        if proposal is not None:
            schema_errors = [
                f"proposal schema: {e.message}"
                for e in proposal_validator.iter_errors(proposal)
            ]
            errors.extend(schema_errors)
            validation["schema_pass"] = not schema_errors
        if proposal is not None and not errors:
            found = spec.validate(proposal, artifact)
            errors.extend(found)
            validation["groundedness_pass"] = not any(
                e.startswith("groundedness") for e in found
            )
            validation["completeness_pass"] = not any(
                e.startswith("completeness") for e in found
            )
        if not errors and proposal is not None:
            document = spec.render(proposal, provenance, regen_version)
            if document.get("id") != committed_id:
                document["version"] = next_version(None, "minor")
            if contract_validator is not None:
                errors.extend(
                    f"contract schema: {e.message}"
                    for e in contract_validator.iter_errors(document)
                )
            if not errors:
                draft_text = to_yaml(
                    document,
                    [
                        f"Draft proposed by {spec.name} v{spec.version} "
                        f"at {created_at}.",
                        "Review before approval (D-24): merge is approval; "
                        "drafts never auto-land.",
                    ],
                )
                run_dir.mkdir(parents=True, exist_ok=True)
                draft_tmp.write_text(draft_text, encoding="utf-8")
                lint_ok, lint_output = lint_runner(draft_tmp)
                validation["lint_pass"] = lint_ok
                if not lint_ok:
                    errors.append(f"datacontract lint failed:\n{lint_output}")
        if not errors:
            stale_errors = recheck_inputs(inputs)
            validation["staleness_pass"] = not stale_errors
            if stale_errors:
                errors.extend(stale_errors)
                # A moved input cannot be fixed by re-asking the model on
                # the same (now stale) payload: fail closed immediately.
                stale = True
        validation["errors"] = errors
        if not errors or stale:
            break
        if attempts < cfg.max_retries + 1:
            messages.append({"role": "assistant", "content": raw_text})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The proposal failed validation. Errors:\n"
                        + "\n".join(errors)
                        + "\nEmit a corrected proposal."
                    ),
                }
            )

    succeeded = not validation["errors"]
    record = {
        "agent": {"name": spec.name, "version": spec.version},
        "stance": spec.stance,
        "prompt_version": str(prompt_meta["version"]),
        "prompt_path": str(spec.prompt_path),
        "model_id": resolved.model_id,
        "model_source": resolved.source,
        "rates": asdict(models.MODELS[resolved.model_id]),
        "sdk_version": anthropic.__version__,
        "request_params": {
            "effort": cfg.effort,
            "max_tokens": cfg.max_tokens,
        },
        "profile_path": str(profile_path),
        "profile_hash": profile_hash,
        "profile_schema_version": str(artifact.get("schema_version", "")),
        "inputs": [asdict(bound) for bound in inputs],
        "created_at": created_at,
        "response_id": response_id,
        "stop_reason": stop_reason,
        "usage": usage,
        "cost_usd_estimate": models.cost_usd(
            resolved.model_id, usage["input_tokens"], usage["output_tokens"]
        ),
        "validation": validation,
        "api_error": api_error,
        "disposition": "draft_written" if succeeded else "failed_closed",
        "draft_path": str(draft_path) if succeeded else None,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    if succeeded:
        os.replace(draft_tmp, draft_path)
    else:
        draft_tmp.unlink(missing_ok=True)
        if api_error is None:
            _replace_bytes(
                run_dir / "raw_response.txt", raw_text.encode("utf-8")
            )
    record_bytes = (
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    _replace_bytes(run_dir / "record.json", record_bytes)

    if not succeeded:
        for line in validation["errors"]:
            print(f"error: {line}", file=sys.stderr)
        preserved = "record" if api_error else "raw response and record"
        print(
            f"failed closed after {attempts} attempt(s); {preserved} "
            f"preserved in {run_dir}",
            file=sys.stderr,
        )
        return 2

    assert proposal is not None and draft_text is not None
    document_id = yaml.safe_load(draft_text).get("id")
    for line in _rationale_lines(proposal):
        print(line)
    print(
        "validation: schema ok, groundedness ok, completeness ok, lint ok, "
        f"staleness ok (attempts: {attempts})"
    )
    print(
        f"model {resolved.model_id} ({resolved.source}); "
        f"tokens in {usage['input_tokens']}, out {usage['output_tokens']}; "
        f"cost ~${record['cost_usd_estimate']:.4f}"
    )
    print(f"draft:  {draft_path}")
    print(f"record: {run_dir / 'record.json'}")
    if spec.target_contract.exists() and committed_id == document_id:
        # Regeneration: both sides normalized through the same
        # parse-and-dump path, so comments drop, scalar styles and line
        # folds converge, and the diff shows element changes rather than
        # serialization style (Session N item 13).
        diff = difflib.unified_diff(
            _normalized_lines(
                spec.target_contract.read_text(encoding="utf-8")
            ),
            _normalized_lines(draft_text),
            fromfile=str(spec.target_contract),
            tofile=str(draft_path),
        )
        sys.stdout.writelines(diff)
    else:
        print(
            f"diff: no committed contract with id {document_id!r} at "
            f"{spec.target_contract}; first proposal for this id"
        )
    return 0


def _strip_scalars(node: Any) -> Any:
    # Folded (>) and literal (|) scalars keep a trailing newline that a
    # plain scalar lacks; for the diff that is style, not content.
    if isinstance(node, dict):
        return {k: _strip_scalars(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_strip_scalars(v) for v in node]
    if isinstance(node, str):
        return node.rstrip()
    return node


def _normalized_lines(text: str) -> list[str]:
    normalized = dump_yaml(
        _strip_scalars(yaml.safe_load(text)), width=1_000_000
    )
    return normalized.splitlines(keepends=True)
