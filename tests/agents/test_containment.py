"""Key presence, API-error containment, stance stamp, normalized diff.

Spec: docs/spec/agent-layer.md §1 (S-N-1: an SDK or transport error is
not an error the model can repair, so the harness fails closed at once
with the error class and message in the record), D-22 Amendment I (the
proposerStance provenance key), and D-24 (the id-gated normalized
terminal diff). Every test is keyless: the fake client is injected or
returned by a monkeypatched constructor, and no network call is ever
made.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import anthropic
import httpx2
import pytest
import yaml

from metricmine.agents import harness, models
from metricmine.agents.harness import ProposerSpec
from metricmine.agents.render import render_mapping, to_yaml
from metricmine.agents.validate import validate_mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)

_PROMPT = """---
version: 1.0.0
date: 2026-08-22
changelog: 1.0.0 containment test fixture.
---

You are the fixture proposer.
"""

_CONFIG = """agents:
  effort: high
  max_tokens: 8192
  max_retries: 2
  outbox_dir: proposals
"""

_REQUEST = httpx2.Request("POST", "https://x.invalid")


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
        if self._outer.error is not None:
            raise self._outer.error
        return self._outer.responses.pop(0)


class FakeClient:
    def __init__(
        self,
        responses: list[SimpleNamespace] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.responses = list(responses or [])
        self.error = error
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
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
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
        target_contract=root
        / "contracts"
        / "gold_invoice_lines_mapping.odcs.yaml",
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


def _run(
    spec: ProposerSpec, root: Path, client: FakeClient | None, **kwargs
) -> int:
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


def test_missing_key_refuses_before_any_client(
    spec: ProposerSpec,
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("client constructed without a key")

    monkeypatch.setattr(harness.anthropic, "Anthropic", boom)
    assert _run(spec, root, client=None) == 1
    assert "ANTHROPIC_API_KEY is not set" in capsys.readouterr().err
    assert not (root / "proposals").exists()


def test_key_presence_is_boolean_and_never_echoed(
    spec: ProposerSpec,
    root: Path,
    good_proposal: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    placeholder = "placeholder-key-value"
    monkeypatch.setenv("ANTHROPIC_API_KEY", placeholder)
    fake = FakeClient([_response(good_proposal)])
    monkeypatch.setattr(
        harness.anthropic, "Anthropic", lambda *a, **k: fake
    )
    assert _run(spec, root, client=None) == 0
    captured = capsys.readouterr()
    assert placeholder not in captured.out
    assert placeholder not in captured.err
    record_text = (_only_run_dir(root) / "record.json").read_text(
        encoding="utf-8"
    )
    assert placeholder not in record_text


@pytest.mark.parametrize(
    "error",
    [
        anthropic.APIConnectionError(request=_REQUEST),
        anthropic.AuthenticationError(
            "bad key",
            response=httpx2.Response(401, request=_REQUEST),
            body=None,
        ),
        anthropic.RateLimitError(
            "slow down",
            response=httpx2.Response(429, request=_REQUEST),
            body=None,
        ),
    ],
    ids=lambda error: type(error).__name__,
)
def test_api_errors_fail_closed_at_once(
    spec: ProposerSpec, root: Path, error: Exception
) -> None:
    client = FakeClient(error=error)
    assert _run(spec, root, client) == 2
    assert len(client.calls) == 1
    run_dir = _only_run_dir(root)
    assert sorted(p.name for p in run_dir.iterdir()) == ["record.json"]
    record = json.loads((run_dir / "record.json").read_text(encoding="utf-8"))
    assert record["disposition"] == "failed_closed"
    assert record["api_error"] == {
        "class": type(error).__name__,
        "message": str(error),
    }
    assert record["validation"]["attempts"] == 1


def test_success_record_carries_null_api_error_and_stance_stamp(
    spec: ProposerSpec, root: Path, good_proposal: str
) -> None:
    client = FakeClient([_response(good_proposal)])
    assert _run(spec, root, client) == 0
    run_dir = _only_run_dir(root)
    record = json.loads((run_dir / "record.json").read_text(encoding="utf-8"))
    assert record["api_error"] is None
    draft = (run_dir / "draft.odcs.yaml").read_text(encoding="utf-8")
    assert "- property: proposerStance\n" in draft
    assert draft.index("proposerStance") > draft.index("proposedAt")
    assert "value: propose\n" in draft


def test_diff_is_normalized_and_gated_on_id(
    spec: ProposerSpec,
    root: Path,
    good_proposal: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client = FakeClient([_response(good_proposal)])
    assert _run(spec, root, client) == 0
    first_out = capsys.readouterr().out
    assert "first proposal for this id" in first_out
    draft = (_only_run_dir(root) / "draft.odcs.yaml").read_text(
        encoding="utf-8"
    )
    document = yaml.safe_load(draft)
    assert document["version"] == "1.0.0"

    # Commit the draft's own document, re-dumped in double-quoted style
    # behind a comment line: on elements only version and status differ,
    # so the normalized diff must show exactly those.
    document["version"] = "1.1.0"
    document["status"] = "active"
    (root / "contracts").mkdir()
    spec.target_contract.write_text(
        "# a comment line\n"
        + yaml.dump(document, sort_keys=False, default_style='"'),
        encoding="utf-8",
    )
    shutil.rmtree(root / "proposals")
    client = FakeClient([_response(good_proposal)])
    assert _run(spec, root, client) == 0
    out = capsys.readouterr().out
    changed = [
        line
        for line in out.splitlines()
        if line.startswith(("+", "-"))
        and not line.startswith(("+++", "---"))
    ]
    assert sorted(changed) == sorted(
        [
            "-version: 1.1.0",
            "+version: 1.2.0",
            "-status: active",
            "+status: draft",
        ]
    )
    assert not any(line.startswith(("-#", "+#")) for line in out.splitlines())


def test_literal_block_round_trips() -> None:
    doc = {"query": "SELECT 1\nFROM t\n", "single": "one line"}
    text = to_yaml(doc, ["header"])
    assert "query: |" in text
    assert yaml.safe_load(text) == doc
