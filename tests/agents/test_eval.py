"""The eval lane end to end with a routing fake client, keyless (D-25).

Spec: docs/spec/agent-layer.md §5. The lane runs the ordinary harness
call per fixture and scores first-attempt lint and groundedness from
each record's attempt_log, so these tests drive run_eval through the
three golden-profile fixtures with a fake that answers by the table
name inside the delimited payload. No network, no key, no real client.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from metricmine.agents import eval as eval_lane
from metricmine.agents import models

REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
EVAL_DIR_NAME = "20260822T120000Z_claude-sonnet-5"

_CONFIG = f"""agents:
  effort: high
  max_tokens: 8192
  max_retries: 2
  outbox_dir: proposals
  silver:
    stances:
      cleanup:
        profile_dir: {REPO_ROOT}/profiles/bronze.online_retail_ii
        prompt: {REPO_ROOT}/src/metricmine/agents/prompts/silver_cleanup.md
        proposal_schema: {REPO_ROOT}/docs/spec/agent-layer/silver-cleanup-proposal.schema.json
        target_contract: {REPO_ROOT}/contracts/silver_invoice_lines.odcs.yaml
  mapping:
    stances:
      propose:
        profile_dir: {REPO_ROOT}/profiles/silver.silver_invoice_lines
        prompt: {REPO_ROOT}/src/metricmine/agents/prompts/gold_mapping.md
        proposal_schema: {REPO_ROOT}/docs/spec/agent-layer/gold-mapping-proposal.schema.json
        target_contract: {REPO_ROOT}/contracts/gold_invoice_lines_mapping.odcs.yaml
        contract_schema: {REPO_ROOT}/docs/spec/engine/mapping-contract.schema.json
  eval:
    fixtures:
      - label: silver-cleanup-online-retail
        proposer: silver
        profile: {REPO_ROOT}/profiles/bronze.online_retail_ii/v0001.json
      - label: mapping-propose-invoice-lines
        proposer: mapping
        profile: {REPO_ROOT}/profiles/silver.silver_invoice_lines/v0001.json
      - label: silver-cleanup-messy-orders
        proposer: silver
        profile: {REPO_ROOT}/tests/agents/fixtures/profiles/bronze.messy_orders/v0001.json
"""

SILVER_EXAMPLE = (
    REPO_ROOT / "docs" / "spec" / "agent-layer"
    / "example-silver-cleanup-proposal.json"
).read_text(encoding="utf-8")
MAPPING_EXAMPLE = (
    REPO_ROOT / "docs" / "spec" / "agent-layer"
    / "example-gold-mapping-proposal.json"
).read_text(encoding="utf-8")
MESSY_EXAMPLE = (
    REPO_ROOT / "tests" / "agents" / "fixtures" / "proposals"
    / "example-silver-cleanup-messy-orders.json"
).read_text(encoding="utf-8")


def _response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=100, output_tokens=50),
        id="msg_fixture",
    )


class RoutingMessages:
    def __init__(self, outer: "RoutingClient") -> None:
        self._outer = outer

    def create(self, **kwargs: object) -> SimpleNamespace:
        self._outer.calls.append(kwargs)
        payload = kwargs["messages"][0]["content"]
        for key, queue in self._outer.queues.items():
            if key in payload:
                # Consume the queue; keep repeating the last entry so an
                # always-failing fixture can exhaust the retry budget.
                text = queue.pop(0) if len(queue) > 1 else queue[0]
                return _response(text)
        raise AssertionError(f"no route matches the payload: {payload[:80]}")


class RoutingClient:
    """Answers by the table name inside the delimited payload."""

    def __init__(self, queues: dict[str, list[str]]) -> None:
        self.queues = {key: list(texts) for key, texts in queues.items()}
        self.calls: list[dict] = []
        self.messages = RoutingMessages(self)


def _clean_queues() -> dict[str, list[str]]:
    return {
        "messy_orders": [MESSY_EXAMPLE],
        "silver_invoice_lines": [MAPPING_EXAMPLE],
        "online_retail_ii": [SILVER_EXAMPLE],
    }


def _lint_ok(path: Path) -> tuple[bool, str]:
    return True, "lint ok"


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
    return tmp_path


def _run(root: Path, client: RoutingClient, **kwargs: object) -> int:
    return eval_lane.run_eval(
        root, client=client, lint_runner=_lint_ok, now=NOW, **kwargs
    )


def _summary(root: Path) -> dict:
    report = root / "proposals" / "eval" / EVAL_DIR_NAME / "report.json"
    return json.loads(report.read_text(encoding="utf-8"))


def test_all_clean_scores_three_of_three(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    client = RoutingClient(_clean_queues())
    assert _run(root, client) == 0
    eval_dir = root / "proposals" / "eval" / EVAL_DIR_NAME
    assert sorted(p.name for p in eval_dir.iterdir()) == [
        "report.json",
        "report.md",
    ]
    summary = _summary(root)
    assert summary["fixtures"] == 3
    assert summary["drafts_written"] == 3
    assert summary["first_attempt_lint_pass_rate"] == "3/3"
    assert summary["first_attempt_groundedness_pass_rate"] == "3/3"
    assert summary["input_tokens"] == 300
    assert summary["output_tokens"] == 150
    assert summary["exit"] == 0
    markdown = (eval_dir / "report.md").read_text(encoding="utf-8")
    assert "first-attempt lint pass rate: 3/3" in markdown
    assert "first-attempt groundedness pass rate: 3/3" in markdown
    out = capsys.readouterr().out
    assert "first-attempt lint pass rate: 3/3" in out
    assert "report:" in out


def test_groundedness_retry_scores_two_of_three(root: Path) -> None:
    planted = json.loads(MAPPING_EXAMPLE)
    planted["fields"].append(
        {
            "name": "region",
            "logical_type": "string",
            "physical_type": "VARCHAR",
            "required": False,
            "mapping_role": "dimension",
            "description": "planted ungrounded field",
        }
    )
    queues = _clean_queues()
    queues["silver_invoice_lines"] = [json.dumps(planted), MAPPING_EXAMPLE]
    client = RoutingClient(queues)
    assert _run(root, client) == 0
    summary = _summary(root)
    row = next(
        r
        for r in summary["rows"]
        if r["label"] == "mapping-propose-invoice-lines"
    )
    assert row["disposition"] == "draft_written"
    assert row["attempts"] == 2
    assert row["first_attempt_groundedness_pass"] is False
    assert row["first_attempt_lint_pass"] is False
    assert summary["first_attempt_lint_pass_rate"] == "2/3"
    assert summary["first_attempt_groundedness_pass_rate"] == "2/3"
    assert summary["drafts_written"] == 3


def test_failed_closed_fixture_still_reports(root: Path) -> None:
    queues = _clean_queues()
    queues["messy_orders"] = ["this is not json"]
    client = RoutingClient(queues)
    assert _run(root, client) == 2
    summary = _summary(root)
    assert summary["fixtures"] == 3
    assert summary["drafts_written"] == 2
    assert summary["first_attempt_lint_pass_rate"] == "2/3"
    assert summary["first_attempt_groundedness_pass_rate"] == "2/3"
    assert summary["exit"] == 2
    row = next(
        r
        for r in summary["rows"]
        if r["label"] == "silver-cleanup-messy-orders"
    )
    assert row["disposition"] == "failed_closed"
    assert row["attempts"] == 3


def test_unlisted_model_refuses_before_any_call(root: Path) -> None:
    client = RoutingClient(_clean_queues())
    assert _run(root, client, model_flag="bogus") == 1
    assert client.calls == []


def test_missing_key_refuses_before_any_call(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        eval_lane.run_eval(root, client=None, lint_runner=_lint_ok, now=NOW)
        == 1
    )
    assert "ANTHROPIC_API_KEY is not set" in capsys.readouterr().err
    assert not (root / "proposals").exists()


def test_fixture_filter_narrows_to_one_row(root: Path) -> None:
    client = RoutingClient(_clean_queues())
    assert _run(root, client, labels=["mapping-propose-invoice-lines"]) == 0
    summary = _summary(root)
    assert summary["fixtures"] == 1
    assert summary["rows"][0]["label"] == "mapping-propose-invoice-lines"
    assert summary["first_attempt_lint_pass_rate"] == "1/1"
    assert summary["first_attempt_groundedness_pass_rate"] == "1/1"

    client = RoutingClient(_clean_queues())
    assert _run(root, client, labels=["no-such-label"]) == 1
    assert client.calls == []
