"""The batch driver: plan order, the explicit cap, the intent gate, and
report-and-stop (D-35, D-10 Amendment G).

The driver is deterministic sequencing over the scan's own derived
queue; these tests hold it to the addendum's sentences: one call per
item in plan order, adopt items through the describe stance, amend
items only under an operator intent, the first fail-closed exit stops
the batch, and a failed item is never re-invoked. The scan inventory
and run_proposer are stubbed, so every test is keyless and warehouse-
free; one local-marked test pins the committed repository's empty walk.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from metricmine.agents import __main__ as cli
from metricmine.agents import propose_queue

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def keyless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MM_PROPOSER_MODEL", raising=False)


def _model(name: str, state: str, layer: str = "silver") -> dict:
    return {
        "name": name,
        "state": state,
        "layer": layer,
        "reason": "constructed",
        "next_command": f'make propose-amend TABLE={name} INTENT="..."',
    }


def _stub_inventory(
    monkeypatch: pytest.MonkeyPatch, models: list[dict]
) -> None:
    monkeypatch.setattr(
        propose_queue.scan, "inventory", lambda repo: {"models": models}
    )


class _Recorder:
    """Stands in for run_proposer: records invocations, scripts exits."""

    def __init__(self, exits: list[int]) -> None:
        self.exits = list(exits)
        self.calls: list[dict] = []

    def __call__(self, spec, repo_root, **kwargs):  # noqa: ANN001
        self.calls.append({"spec": spec, "kwargs": kwargs})
        code = self.exits.pop(0)
        if code == 0:
            kwargs["report"]["record"] = {
                "draft_path": f"proposals/x/{len(self.calls)}/draft.odcs.yaml",
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "cost_usd_estimate": 0.001,
                "validation": {"attempts": 1},
            }
        return code


def _stub_specs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        propose_queue.silver_proposer,
        "build_describe_spec",
        lambda repo, table: f"describe-spec:{table}",
    )

    committed_path = REPO_ROOT / "contracts" / "silver_invoice_lines.odcs.yaml"

    def fake_amend_spec(repo, table, **kwargs):  # noqa: ANN001
        return (
            f"amend-spec:{table}",
            {"id": table, "version": "1.1.0"},
            committed_path.read_bytes(),
        )

    monkeypatch.setattr(
        propose_queue.silver_proposer, "build_amend_spec", fake_amend_spec
    )


def test_an_empty_queue_invokes_nothing_and_exits_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _stub_inventory(monkeypatch, [_model("silver_a", "in_sync")])
    recorder = _Recorder([])
    monkeypatch.setattr(propose_queue.harness, "run_proposer", recorder)
    assert propose_queue.run_queue(REPO_ROOT, 5) == 0
    out = capsys.readouterr().out
    assert "nothing to invoke" in out
    assert recorder.calls == []


def test_adopt_items_run_the_describe_stance_in_plan_order(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _stub_inventory(
        monkeypatch,
        [
            _model("silver_b", "adopt"),
            _model("silver_a", "adopt"),
            _model("silver_c", "needs_profile"),
        ],
    )
    _stub_specs(monkeypatch)
    recorder = _Recorder([0, 0])
    monkeypatch.setattr(propose_queue.harness, "run_proposer", recorder)
    assert propose_queue.run_queue(REPO_ROOT, 5) == 0
    assert [c["spec"] for c in recorder.calls] == [
        "describe-spec:silver_a",
        "describe-spec:silver_b",
    ]
    out = capsys.readouterr().out
    assert "not driven: silver_c at needs_profile" in out
    assert "walked 2 item(s)" in out
    assert "total cost" in out


def test_the_cap_is_honored_and_reported(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _stub_inventory(
        monkeypatch,
        [_model("silver_a", "adopt"), _model("silver_b", "adopt")],
    )
    _stub_specs(monkeypatch)
    recorder = _Recorder([0])
    monkeypatch.setattr(propose_queue.harness, "run_proposer", recorder)
    assert propose_queue.run_queue(REPO_ROOT, 1) == 0
    assert len(recorder.calls) == 1
    assert "cap reached: MAX=1" in capsys.readouterr().out


def test_amend_items_without_intent_are_listed_never_invoked(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _stub_inventory(
        monkeypatch, [_model("silver_invoice_lines", "amend")]
    )
    _stub_specs(monkeypatch)
    recorder = _Recorder([])
    monkeypatch.setattr(propose_queue.harness, "run_proposer", recorder)
    assert propose_queue.run_queue(REPO_ROOT, 5) == 0
    out = capsys.readouterr().out
    assert recorder.calls == []
    assert "skipped (no INTENT): silver_invoice_lines" in out
    assert 'make propose-amend TABLE=silver_invoice_lines INTENT="..."' in out
    assert 'pass INTENT="..."' in out


def test_amend_items_with_intent_bind_all_three_governed_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_inventory(
        monkeypatch, [_model("silver_invoice_lines", "amend")]
    )
    _stub_specs(monkeypatch)
    recorder = _Recorder([0])
    monkeypatch.setattr(propose_queue.harness, "run_proposer", recorder)
    assert (
        propose_queue.run_queue(
            REPO_ROOT, 5, intent="reconcile the scan's drift reading"
        )
        == 0
    )
    kwargs = recorder.calls[0]["kwargs"]
    assert kwargs["intent"] == "reconcile the scan's drift reading"
    bound, text = kwargs["extra_inputs"][0]
    assert bound.kind == "committed_contract"
    assert kwargs["provenance_extras"]["amendsContract"].startswith(
        "silver_invoice_lines@1.1.0#sha256:"
    )
    assert kwargs["quiet"] is True


def test_a_fail_closed_exit_stops_the_batch_and_never_reinvokes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _stub_inventory(
        monkeypatch,
        [_model("silver_a", "adopt"), _model("silver_b", "adopt")],
    )
    _stub_specs(monkeypatch)
    recorder = _Recorder([2])
    monkeypatch.setattr(propose_queue.harness, "run_proposer", recorder)
    assert propose_queue.run_queue(REPO_ROOT, 5) == 1
    out = capsys.readouterr().out
    assert len(recorder.calls) == 1
    assert "stopped: silver_a exited 2 (failed closed)" in out
    assert "never re-invoked unattended (Amendment G)" in out


def test_a_refusal_exit_also_stops_the_batch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _stub_inventory(monkeypatch, [_model("silver_a", "adopt")])
    _stub_specs(monkeypatch)
    recorder = _Recorder([1])
    monkeypatch.setattr(propose_queue.harness, "run_proposer", recorder)
    assert propose_queue.run_queue(REPO_ROOT, 5) == 1
    assert "refused" in capsys.readouterr().out


def test_the_cli_requires_an_explicit_positive_cap(
    capsys: pytest.CaptureFixture,
) -> None:
    for raw in ("", "0", "-1", "five"):
        code = cli.main(["propose-queue", "--max", raw])
        err = capsys.readouterr().err
        assert code == 1
        assert "explicit positive cap" in err


def test_adopt_outranks_amend_in_the_walk_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_inventory(
        monkeypatch,
        [
            _model("silver_invoice_lines", "amend"),
            _model("silver_new", "adopt"),
        ],
    )
    _stub_specs(monkeypatch)
    recorder = _Recorder([0, 0])
    monkeypatch.setattr(propose_queue.harness, "run_proposer", recorder)
    assert propose_queue.run_queue(REPO_ROOT, 5, intent="drift") == 0
    assert [c["spec"] for c in recorder.calls] == [
        "describe-spec:silver_new",
        "amend-spec:silver_invoice_lines",
    ]


@pytest.mark.local
def test_the_committed_repository_walks_empty(
    capsys: pytest.CaptureFixture,
) -> None:
    """At the committed state with a built warehouse the queue is empty,
    so the driver invokes nothing, needs no key, and exits 0."""
    assert propose_queue.run_queue(REPO_ROOT, 5) == 0
    out = capsys.readouterr().out
    assert "nothing to invoke" in out
