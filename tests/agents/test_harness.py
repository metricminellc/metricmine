"""The proposer harness end to end with a fake client, keyless.

Spec: docs/spec/agent-layer.md §1 (D-21 as amended, D-23 as amended,
D-24, D-34) and CLAUDE.md rule 15. Every test runs under tmp_path with a
copied profile; no network, no key, no real client is ever constructed.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import pytest

from metricmine.agents import harness, models
from metricmine.agents.harness import ProposerSpec
from metricmine.agents.render import render_mapping
from metricmine.agents.validate import validate_mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)

_PROMPT = """---
version: 1.0.0
date: 2026-08-22
changelog: 1.0.0, harness test fixture.
---

You are the fixture proposer.
"""

_CONFIG = """agents:
  effort: high
  max_tokens: 8192
  max_retries: 2
  outbox_dir: proposals
"""


def _response(text: str, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=100, output_tokens=50),
        id="msg_fixture",
    )


class FakeMessages:
    def __init__(self, outer: "FakeClient") -> None:
        self._outer = outer

    def create(self, **kwargs: object) -> SimpleNamespace:
        self._outer.calls.append(kwargs)
        return self._outer.responses.pop(0)


class FakeClient:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []
        self.messages = FakeMessages(self)


def _lint_recorder(
    results: list[tuple[bool, str]] | None = None,
    side_effect: Callable[[Path], None] | None = None,
) -> tuple[Callable[[Path], tuple[bool, str]], list[Path]]:
    calls: list[Path] = []
    queued = list(results or [])

    def runner(path: Path) -> tuple[bool, str]:
        calls.append(path)
        if side_effect is not None:
            side_effect(path)
        return queued.pop(0) if queued else (True, "lint ok")

    return runner, calls


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(models.ENV_VAR, raising=False)


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "default.yaml").write_text(
        _CONFIG, encoding="utf-8"
    )
    (tmp_path / "profiles").mkdir()
    shutil.copy(
        REPO_ROOT / "profiles" / "silver.silver_invoice_lines" / "v0001.json",
        tmp_path / "profiles" / "v0001.json",
    )
    (tmp_path / "prompt.md").write_text(_PROMPT, encoding="utf-8")
    return tmp_path


@pytest.fixture()
def spec(root: Path) -> ProposerSpec:
    return ProposerSpec(
        name="gold-mapping-proposer",
        version="0.1.0",
        stance="propose",
        profile_dir=root / "profiles",
        prompt_path=root / "prompt.md",
        proposal_schema=REPO_ROOT
        / "docs"
        / "spec"
        / "agent-layer"
        / "gold-mapping-proposal.schema.json",
        contract_schema=REPO_ROOT
        / "docs"
        / "spec"
        / "engine"
        / "mapping-contract.schema.json",
        target_contract=root / "contracts" / "does-not-exist.odcs.yaml",
        render=render_mapping,
        validate=validate_mapping,
    )


@pytest.fixture(scope="module")
def good_proposal() -> str:
    path = (
        REPO_ROOT / "docs" / "spec" / "agent-layer"
        / "example-gold-mapping-proposal.json"
    )
    return path.read_text(encoding="utf-8")


def _run(spec: ProposerSpec, root: Path, client: FakeClient, **kwargs) -> int:
    lint_runner = kwargs.pop("lint_runner", None)
    if lint_runner is None:
        lint_runner, _ = _lint_recorder()
    return harness.run_proposer(
        spec, root, client=client, lint_runner=lint_runner, now=NOW, **kwargs
    )


def _only_run_dir(root: Path, name: str = "gold-mapping-proposer") -> Path:
    run_dirs = list((root / "proposals" / name).iterdir())
    assert len(run_dirs) == 1
    return run_dirs[0]


def test_success_writes_draft_and_record_only(
    spec: ProposerSpec, root: Path, good_proposal: str
) -> None:
    client = FakeClient([_response(good_proposal)])
    assert _run(spec, root, client) == 0
    run_dir = _only_run_dir(root)
    assert sorted(p.name for p in run_dir.iterdir()) == [
        "draft.odcs.yaml",
        "proposal.json",
        "record.json",
    ]
    record = json.loads((run_dir / "record.json").read_text(encoding="utf-8"))
    assert record["disposition"] == "draft_written"
    assert record["stance"] == "propose"
    validation = record["validation"]
    assert validation["attempts"] == 1
    for flag in (
        "schema_pass",
        "groundedness_pass",
        "completeness_pass",
        "staleness_pass",
        "lint_pass",
    ):
        assert validation[flag] is True, flag
    assert record["inputs"][0]["kind"] == "profile_artifact"
    assert record["usage"] == {"input_tokens": 100, "output_tokens": 50}


def test_call_kwargs_carry_no_tools_and_carry_output_config(
    spec: ProposerSpec, root: Path, good_proposal: str
) -> None:
    client = FakeClient([_response(good_proposal)])
    assert _run(spec, root, client) == 0
    kwargs = client.calls[0]
    for forbidden in ("tools", "temperature", "thinking"):
        assert forbidden not in kwargs
    assert kwargs["max_tokens"] == 8192
    assert kwargs["output_config"]["effort"] == "high"
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert kwargs["messages"][0]["content"].startswith("<profile_artifact>\n")
    assert kwargs["messages"][0]["content"].endswith("\n</profile_artifact>")


def test_model_source_env_and_flag(
    spec: ProposerSpec,
    root: Path,
    good_proposal: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(models.ENV_VAR, "claude-opus-5")
    client = FakeClient([_response(good_proposal)])
    assert _run(spec, root, client) == 0
    record = json.loads(
        (_only_run_dir(root) / "record.json").read_text(encoding="utf-8")
    )
    assert record["model_id"] == "claude-opus-5"
    assert record["model_source"] == "env"
    assert client.calls[0]["model"] == "claude-opus-5"

    shutil.rmtree(root / "proposals")
    client = FakeClient([_response(good_proposal)])
    assert _run(spec, root, client, model_flag="claude-fable-5") == 0
    record = json.loads(
        (_only_run_dir(root) / "record.json").read_text(encoding="utf-8")
    )
    assert record["model_id"] == "claude-fable-5"
    assert record["model_source"] == "flag"


def test_max_tokens_stop_is_a_failed_attempt(
    spec: ProposerSpec, root: Path, good_proposal: str
) -> None:
    client = FakeClient(
        [
            _response(good_proposal, stop_reason="max_tokens"),
            _response(good_proposal),
        ]
    )
    assert _run(spec, root, client) == 0
    record = json.loads(
        (_only_run_dir(root) / "record.json").read_text(encoding="utf-8")
    )
    assert record["validation"]["attempts"] == 2
    retry_turn = client.calls[1]["messages"][-1]["content"]
    assert "max_tokens" in retry_turn


def test_three_failures_fail_closed(spec: ProposerSpec, root: Path) -> None:
    client = FakeClient([_response("not json")] * 3)
    assert _run(spec, root, client) == 2
    assert len(client.calls) == 3
    run_dir = _only_run_dir(root)
    assert sorted(p.name for p in run_dir.iterdir()) == [
        "raw_response.txt",
        "record.json",
    ]
    record = json.loads((run_dir / "record.json").read_text(encoding="utf-8"))
    assert record["disposition"] == "failed_closed"
    assert record["draft_path"] is None
    assert record["validation"]["attempts"] == 3


def test_lint_failure_feeds_output_into_the_retry(
    spec: ProposerSpec, root: Path, good_proposal: str
) -> None:
    lint_runner, lint_calls = _lint_recorder(
        [(False, "LINT BOOM: bad shape"), (True, "ok")]
    )
    client = FakeClient([_response(good_proposal)] * 2)
    assert _run(spec, root, client, lint_runner=lint_runner) == 0
    assert len(lint_calls) == 2
    retry_turn = client.calls[1]["messages"][-1]["content"]
    assert "LINT BOOM" in retry_turn


def test_attempt_log_records_each_attempt(
    spec: ProposerSpec, root: Path, good_proposal: str
) -> None:
    lint_runner, _ = _lint_recorder(
        [(False, "LINT BOOM: bad shape"), (True, "ok")]
    )
    client = FakeClient([_response(good_proposal)] * 2)
    assert _run(spec, root, client, lint_runner=lint_runner) == 0
    record = json.loads(
        (_only_run_dir(root) / "record.json").read_text(encoding="utf-8")
    )
    log = record["validation"]["attempt_log"]
    assert len(log) == 2
    assert log[0]["schema_pass"] is True
    assert log[0]["lint_pass"] is False
    assert any("LINT BOOM" in e for e in log[0]["errors"])
    assert log[1]["lint_pass"] is True
    assert log[1]["errors"] == []


def test_tampered_profile_refused_before_any_call(
    spec: ProposerSpec, root: Path
) -> None:
    profile_path = root / "profiles" / "v0001.json"
    artifact = json.loads(profile_path.read_text(encoding="utf-8"))
    artifact["content_hash"] = "sha256:" + "f" * 64
    profile_path.write_text(json.dumps(artifact), encoding="utf-8")
    client = FakeClient([])
    assert _run(spec, root, client) == 1
    assert client.calls == []


def test_hash_moving_between_call_and_write_fails_closed(
    spec: ProposerSpec, root: Path, good_proposal: str
) -> None:
    profile_path = root / "profiles" / "v0001.json"

    def tamper(_: Path) -> None:
        artifact = json.loads(profile_path.read_text(encoding="utf-8"))
        artifact["dataset"]["row_count"] = 1
        profile_path.write_text(json.dumps(artifact), encoding="utf-8")

    lint_runner, _ = _lint_recorder(side_effect=tamper)
    client = FakeClient([_response(good_proposal)] * 3)
    assert _run(spec, root, client, lint_runner=lint_runner) == 2
    assert len(client.calls) == 1  # staleness is not retryable
    record = json.loads(
        (_only_run_dir(root) / "record.json").read_text(encoding="utf-8")
    )
    assert record["validation"]["staleness_pass"] is False
    assert record["disposition"] == "failed_closed"


def test_unlisted_model_refused_before_any_call(
    spec: ProposerSpec, root: Path
) -> None:
    client = FakeClient([])
    assert _run(spec, root, client, model_flag="bogus") == 1
    assert client.calls == []


def test_missing_datacontract_refused_before_any_call(
    spec: ProposerSpec, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(harness.shutil, "which", lambda _: None)
    client = FakeClient([])
    exit_code = harness.run_proposer(
        spec, root, client=client, lint_runner=None, now=NOW
    )
    assert exit_code == 1
    assert client.calls == []


def test_run_folder_stamps_are_sub_second(
    spec: ProposerSpec, root: Path, good_proposal: str
) -> None:
    # Same-second runs must land in distinct folders: the batch driver
    # (D-35) fires proposer runs back to back, and a second-granular
    # stamp collided in the Session O-1 rehearsal. The module's _run
    # helper pins its own now, so run_proposer is called directly here.
    first = datetime(2026, 8, 25, 12, 0, 0, 111111, tzinfo=timezone.utc)
    second = datetime(2026, 8, 25, 12, 0, 0, 222222, tzinfo=timezone.utc)
    for now in (first, second):
        code = harness.run_proposer(
            spec,
            root,
            client=FakeClient([_response(good_proposal)]),
            lint_runner=_lint_recorder()[0],
            now=now,
        )
        assert code == 0
    run_dirs = sorted(
        path.name for path in (root / "proposals" / spec.name).iterdir()
    )
    assert len(run_dirs) == 2
    assert run_dirs[0].startswith("20260825T120000111111Z_")
    assert run_dirs[1].startswith("20260825T120000222222Z_")


def test_amend_inputs_bind_the_contract_and_the_intent_verbatim(
    spec: ProposerSpec, root: Path, good_proposal: str
) -> None:
    """The three governed inputs (D-23 Amendment H): the record carries
    the ordered inputs with hashes and the intent verbatim (Amendment I),
    and the user turn wraps each in its own delimiter tag, intent LAST."""
    contract_path = root / "committed.odcs.yaml"
    contract_path.write_text("id: fake\nversion: 1.0.0\n", encoding="utf-8")
    digest = "sha256:" + hashlib.sha256(contract_path.read_bytes()).hexdigest()
    bound = harness.GovernedInput(
        kind="committed_contract",
        path=str(contract_path),
        content_hash=digest,
        schema_version="1.0.0",
    )
    client = FakeClient([_response(good_proposal)])
    code = _run(
        spec,
        root,
        client,
        extra_inputs=[(bound, contract_path.read_text(encoding="utf-8"))],
        intent="correct the quantity description",
        provenance_extras={"amendsContract": "fake@1.0.0#" + digest},
    )
    assert code == 0
    record = json.loads(
        (_only_run_dir(root) / "record.json").read_text(encoding="utf-8")
    )
    assert record["intent"] == "correct the quantity description"
    kinds = [entry["kind"] for entry in record["inputs"]]
    assert kinds == ["profile_artifact", "committed_contract", "operator_intent"]
    assert record["inputs"][1]["content_hash"] == digest
    assert record["inputs"][2]["path"] == ""
    user_content = client.calls[0]["messages"][0]["content"]
    assert user_content.index("<profile_artifact>") < user_content.index(
        "<committed_contract>"
    )
    assert user_content.index("<committed_contract>") < user_content.index(
        "<operator_intent>"
    )
    assert (
        "<operator_intent>\ncorrect the quantity description\n"
        "</operator_intent>" in user_content
    )


def test_a_moved_committed_contract_fails_closed_at_once(
    spec: ProposerSpec, root: Path, good_proposal: str
) -> None:
    """The committed contract is a hashed governed input: moving it
    between read and write fails staleness with no retry (Amendment H)."""
    contract_path = root / "committed.odcs.yaml"
    contract_path.write_text("id: fake\nversion: 1.0.0\n", encoding="utf-8")
    digest = "sha256:" + hashlib.sha256(contract_path.read_bytes()).hexdigest()
    bound = harness.GovernedInput(
        kind="committed_contract",
        path=str(contract_path),
        content_hash=digest,
        schema_version="1.0.0",
    )

    def tampering_lint(path: Path) -> tuple[bool, str]:
        contract_path.write_text("id: fake\nversion: 1.0.1\n", encoding="utf-8")
        return True, "valid"

    client = FakeClient([_response(good_proposal), _response(good_proposal)])
    code = _run(
        spec,
        root,
        client,
        lint_runner=tampering_lint,
        extra_inputs=[(bound, "id: fake\nversion: 1.0.0\n")],
        intent="x",
    )
    assert code == 2
    assert len(client.calls) == 1
    record = json.loads(
        (_only_run_dir(root) / "record.json").read_text(encoding="utf-8")
    )
    assert record["validation"]["attempts"] == 1
    assert record["disposition"] == "failed_closed"
    assert any(
        "committed_contract" in error
        for error in record["validation"]["errors"]
    )


def test_a_relaxation_refusal_fails_closed_without_a_retry(
    spec: ProposerSpec, root: Path, good_proposal: str
) -> None:
    """A relaxation: error is the operator's gate (D-35, D-08): re-asking
    the model would only talk it out of the narrowing the intent asked
    for, so the harness breaks at once, exactly like staleness."""
    refusing = ProposerSpec(
        name=spec.name,
        version=spec.version,
        stance="amend",
        profile_dir=spec.profile_dir,
        prompt_path=spec.prompt_path,
        proposal_schema=spec.proposal_schema,
        contract_schema=None,
        target_contract=spec.target_contract,
        render=spec.render,
        validate=lambda proposal, profile: [
            "relaxation: this amendment NARROWS the contract "
            "(drop_column x); narrowing is refused without "
            "--allow-relaxation"
        ],
    )
    client = FakeClient([_response(good_proposal), _response(good_proposal)])
    code = _run(refusing, root, client)
    assert code == 2
    assert len(client.calls) == 1
    record = json.loads(
        (_only_run_dir(root) / "record.json").read_text(encoding="utf-8")
    )
    assert record["validation"]["attempts"] == 1
    assert record["validation"]["errors"][0].startswith("relaxation:")
