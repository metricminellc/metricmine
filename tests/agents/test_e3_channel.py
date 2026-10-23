"""The context channel (E3a, experiment branch; docs/experiments/e3/KEY.md
Section 4): one more governed input on every stance, keyless.

The operator's context is bound LAST, inside its own delimiter tag, hashed
over its UTF-8 bytes, recorded verbatim with the committed path it was
read from, and re-checked for staleness before the draft is written, the
same way the intent and the committed contract are. Without it the
payload is byte-identical to head's. Nothing is retrieved: the channel
takes a string or a committed file and nothing else.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from metricmine.agents import __main__ as cli
from metricmine.agents import harness, models, propose_queue, silver_proposer
from metricmine.agents.harness import GovernedInput

from .e3_support import (
    REPO_ROOT,
    RoutingClient,
    lint_ok,
    mirrored_root,
    recorded,
)

CONTEXT = "This source is a toy. We name a code column with `_code`.\n"


@pytest.fixture(autouse=True)
def _keyless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv(models.ENV_VAR, raising=False)


def _run_cleanup(root: Path, client: RoutingClient, **kwargs: object) -> tuple[int, dict]:
    spec = silver_proposer.build_spec(root, source="nyc_airlines")
    report: dict = {}
    code = harness.run_proposer(
        spec, root, profile=str(root / "profiles/bronze.nyc_airlines/v0001.json"),
        client=client, lint_runner=lint_ok, report=report, quiet=True, **kwargs,
    )
    return code, report


def _tags(client: RoutingClient) -> list[str]:
    content = client.calls[-1]["messages"][0]["content"]
    return [line[1:-1] for line in content.splitlines() if line.startswith("<") and not line.startswith("</")]


def test_without_a_context_the_payload_is_heads_byte_for_byte(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    client = RoutingClient({"nyc_airlines": [recorded("silver-cleanup-nyc-airlines")]})
    code, report = _run_cleanup(root, client)
    assert code == 0
    assert _tags(client) == ["profile_artifact"]
    record = report["record"]
    assert record["context"] is None and record["context_path"] is None
    assert record["skeleton"] is False
    assert [i["kind"] for i in record["inputs"]] == ["profile_artifact"]
    assert "operator_context" not in client.calls[-1]["messages"][0]["content"]


def test_a_context_is_the_last_tag_hashed_and_recorded_verbatim(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    client = RoutingClient({"nyc_airlines": [recorded("silver-cleanup-nyc-airlines")]})
    code, report = _run_cleanup(root, client, context=CONTEXT)
    assert code == 0
    assert _tags(client) == ["profile_artifact", "operator_context"]
    content = client.calls[-1]["messages"][0]["content"]
    assert content.endswith(f"<operator_context>\n{CONTEXT}\n</operator_context>")
    record = report["record"]
    assert record["context"] == CONTEXT
    assert record["context_path"] is None
    last = record["inputs"][-1]
    assert last == {
        "kind": "operator_context",
        "path": "",
        "content_hash": "sha256:" + hashlib.sha256(CONTEXT.encode("utf-8")).hexdigest(),
        "schema_version": "",
    }
    # The system prompt is head's body, untouched by the channel: the
    # context travels in the user turn only.
    head_body = harness.parse_prompt_front_matter(
        root / "src/metricmine/agents/prompts/silver_cleanup.md"
    )[1]
    assert client.calls[-1]["system"] == head_body


def test_a_context_file_records_its_path_and_the_hash_of_its_bytes(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    context_path = root / "docs" / "experiments" / "e3" / "contexts" / "silver-cleanup-nyc-airlines.md"
    raw = context_path.read_bytes()
    client = RoutingClient({"nyc_airlines": [recorded("silver-cleanup-nyc-airlines")]})
    code, report = _run_cleanup(root, client, context=raw.decode("utf-8"), context_path=str(context_path))
    assert code == 0
    record = report["record"]
    assert record["context"] == raw.decode("utf-8")
    assert record["context_path"] == str(context_path)
    assert record["inputs"][-1]["path"] == str(context_path)
    assert record["inputs"][-1]["content_hash"] == "sha256:" + hashlib.sha256(raw).hexdigest()


def test_a_context_file_that_moves_before_the_write_fails_closed(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    moving = tmp_path / "context.md"
    moving.write_bytes(CONTEXT.encode("utf-8"))

    def answer_and_move() -> str:
        moving.write_bytes((CONTEXT + "An edit after binding.\n").encode("utf-8"))
        return recorded("silver-cleanup-nyc-airlines")

    client = RoutingClient({"nyc_airlines": [answer_and_move]})
    code, report = _run_cleanup(root, client, context=CONTEXT, context_path=str(moving))
    assert code == 2
    record = report["record"]
    assert record["disposition"] == "failed_closed"
    assert record["validation"]["staleness_pass"] is False
    assert any(
        e.startswith("staleness: input operator_context at") for e in record["validation"]["errors"]
    )
    assert record["draft_path"] is None
    assert len(client.calls) == 1  # a moved input is never re-asked
    assert not list(Path(report["run_dir"]).glob("draft.odcs.yaml"))


def test_the_same_file_unchanged_passes_the_staleness_recheck(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    steady = tmp_path / "context.md"
    steady.write_bytes(CONTEXT.encode("utf-8"))
    client = RoutingClient({"nyc_airlines": [recorded("silver-cleanup-nyc-airlines")]})
    code, report = _run_cleanup(root, client, context=CONTEXT, context_path=str(steady))
    assert code == 0
    assert report["record"]["validation"]["staleness_pass"] is True


def test_recheck_inputs_rehashes_an_operator_context_by_path(tmp_path: Path) -> None:
    path = tmp_path / "c.md"
    path.write_bytes(b"one\n")
    bound = GovernedInput(
        kind="operator_context", path=str(path),
        content_hash="sha256:" + hashlib.sha256(b"one\n").hexdigest(), schema_version="",
    )
    assert harness.recheck_inputs([bound]) == []
    path.write_bytes(b"two\n")
    errors = harness.recheck_inputs([bound])
    assert len(errors) == 1 and errors[0].startswith("staleness: input operator_context at")
    unpathed = GovernedInput(kind="operator_context", path="", content_hash="sha256:x", schema_version="")
    assert harness.recheck_inputs([unpathed]) == []


def test_amend_binds_the_context_after_the_intent(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    committed_path = root / "docs/experiments/e3/fixtures/silver_invoice_lines@1.2.0.odcs.yaml"
    spec, committed, committed_bytes = silver_proposer.build_amend_spec(
        root, "silver_invoice_lines", committed_path=committed_path
    )
    from metricmine.agents import render

    bound = GovernedInput(
        kind="committed_contract", path=str(committed_path),
        content_hash=render.canonical_contract_bytes(committed_bytes),
        schema_version=str(committed["version"]),
    )
    from .e3_support import amend_proposal

    client = RoutingClient({"silver_invoice_lines": [json.dumps(amend_proposal(committed))]})
    report: dict = {}
    code = harness.run_proposer(
        spec, root, profile=str(root / "profiles/silver.silver_invoice_lines/v0002.json"),
        client=client, lint_runner=lint_ok, report=report, quiet=True,
        extra_inputs=[(bound, committed_bytes.decode("utf-8"))], intent="Tighten captured_at.",
        provenance_extras={"amendsContract": render.amends_contract_stamp(committed, committed_bytes)},
        context=CONTEXT,
    )
    assert code == 0, report["record"]["validation"]["errors"]
    assert _tags(client) == ["profile_artifact", "committed_contract", "operator_intent", "operator_context"]
    kinds = [i["kind"] for i in report["record"]["inputs"]]
    assert kinds == ["profile_artifact", "committed_contract", "operator_intent", "operator_context"]
    assert report["record"]["intent"] == "Tighten captured_at."
    assert report["record"]["context"] == CONTEXT


def test_the_cli_reads_a_context_file_by_bytes_and_refuses_both_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "ctx.md"
    path.write_bytes("Line one.\r\nLine two.\n".encode("utf-8"))
    captured: dict = {}

    def fake_run_proposer(spec, repo_root, **kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(cli.harness, "run_proposer", fake_run_proposer)
    assert cli.main(["propose", "silver", "--context-file", str(path)]) == 0
    assert captured["context"] == "Line one.\r\nLine two.\n"  # bytes decoded, never newline-translated
    assert captured["context_path"] == str(path)
    assert cli.main(["propose", "silver", "--context", "A sentence."]) == 0
    assert captured["context"] == "A sentence." and captured["context_path"] is None
    assert cli.main(["propose", "silver", "--context", "x", "--context-file", str(path)]) == 1
    assert "not both" in capsys.readouterr().err
    assert cli.main(["propose", "silver", "--context", "   "]) == 1
    assert "--context is empty" in capsys.readouterr().err
    assert cli.main(["propose", "silver", "--context-file", str(tmp_path / "missing.md")]) == 1
    assert "does not exist" in capsys.readouterr().err


def test_the_batch_driver_passes_the_context_to_every_item(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        propose_queue.scan, "inventory",
        lambda repo: {"models": [{"name": "silver_x", "state": "adopt", "layer": "silver",
                                  "reason": "constructed", "next_command": "make propose-describe TABLE=silver_x"}]},
    )
    monkeypatch.setattr(
        propose_queue.silver_proposer, "build_describe_spec", lambda repo, table: f"describe-spec:{table}"
    )
    calls: list[dict] = []

    def recorder(spec, repo_root, **kwargs):  # noqa: ANN001
        calls.append(kwargs)
        kwargs["report"]["record"] = {
            "draft_path": "proposals/x/1/draft.odcs.yaml",
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "cost_usd_estimate": 0.0, "validation": {"attempts": 1},
        }
        return 0

    monkeypatch.setattr(propose_queue.harness, "run_proposer", recorder)
    assert propose_queue.run_queue(REPO_ROOT, 5, context=CONTEXT) == 0
    assert len(calls) == 1 and calls[0]["context"] == CONTEXT
    calls.clear()
    assert propose_queue.run_queue(REPO_ROOT, 5) == 0
    assert calls[0]["context"] is None
