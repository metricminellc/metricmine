"""The arm runner, the ledger, the bound, the screen, the evidence copier,
the scorer, and the finding renderer on a routing fake, keyless
(experiment branch; docs/experiments/e3/KEY.md Sections 6, 8, and 9).

Every run is one ordinary harness call. The ledger is the record of what
was spent and what came back: a result is never re-run unattended, a
technical failure at attempt 1 is re-run only when a person passes the
flag, a fixture whose latest result failed closed loses its remaining
attempts until a person continues it by name (D-10 Amendment G), the bound
is checked before every call against the ledger total plus the next
estimate, and an attempt reaches the committed evidence folder only after
the screen. The scorer reads the ledger and the committed evidence, never
the outbox, and a cell below the floor decides no rule.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
import yaml

from metricmine.agents import e3, models

from .e3_support import (
    REPO_ROOT,
    RoutingClient,
    amend_proposal,
    connection_error,
    describe_judgment,
    describe_proposal,
    lint_ok,
    mirrored_root,
    profile,
    recorded,
)


@pytest.fixture(autouse=True)
def _keyless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv(models.ENV_VAR, raising=False)


def _arms(root: Path, **overrides: dict) -> dict:
    """The committed arms file with per-arm fixture lists or counts
    narrowed for the test (never widened)."""
    arms = e3.load_arms(root)
    for name, change in overrides.items():
        if name == "spend_bound_usd":
            arms["spend_bound_usd"] = change
            continue
        arms["arms"][name].update(change)
    return arms


def _queues() -> dict:
    return {
        "nyc_airlines": [recorded("silver-cleanup-nyc-airlines")],
        "nyc_planes": [recorded("silver-cleanup-nyc-planes")],
        "online_retail_ii": [recorded("silver-cleanup-online-retail")],
        "messy_orders": [recorded("silver-cleanup-messy-orders")],
        ("stance: propose", "silver_flights"): [recorded("mapping-propose-flights")],
    }


def _run(root: Path, arm: str, client: RoutingClient, *, arms: dict, **kwargs: object) -> tuple[int, str]:
    out = io.StringIO()
    code = e3.run_arm(
        root, arm, client=client, lint_runner=lint_ok, out=out, arms=arms,
        ledger=root / "ledger.jsonl", evidence_dir=root / "runs", **kwargs,
    )
    return code, out.getvalue()


def _rows(root: Path) -> list[dict]:
    return e3.read_ledger(root / "ledger.jsonl")


def test_a_batch_runs_every_planned_attempt_and_records_each(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    arms = _arms(root, baseline={"fixtures": ["silver-cleanup-nyc-airlines", "silver-cleanup-nyc-planes"]})
    client = RoutingClient(_queues())
    code, text = _run(root, "baseline", client, arms=arms, repeats=2)
    assert code == 0, text
    lines = text.splitlines()
    assert lines[0] == (
        "SPEND-BOUND 200.00 USD; ledger total 0.0000 USD; this batch: baseline claude-sonnet-5 4 runs estimated 0.1676 USD"
    )
    runs = [line for line in lines if line.startswith("RUN ")]
    assert len(runs) == 4 == len(client.calls)
    assert runs[0].startswith(
        "RUN baseline silver-cleanup-nyc-airlines a01 draft_written attempts=1 lint@1=yes grounded@1=yes "
        "machine@1=0 judgment@1=0 agreement=0/0 shared=0 in=100 out=50 cost=0.0007"
    )
    assert "agreement=" in runs[2] and "shared=2 " in runs[2]
    assert "COST-HIGH" not in text
    assert lines[-2] == "BATCH baseline claude-sonnet-5: runs=4 written=4 failed=0 technical=0 lost=0 skipped=0 cost=0.0028 USD; ledger total 0.0028 USD"
    assert lines[-1].startswith("EVIDENCE baseline: 16 file(s) copied under docs/experiments/e3/runs/baseline (screen: 0 refusal(s), ")
    rows = _rows(root)
    assert [(r["label"], r["attempt"]) for r in rows] == [
        ("silver-cleanup-nyc-airlines", 1), ("silver-cleanup-nyc-airlines", 2),
        ("silver-cleanup-nyc-planes", 1), ("silver-cleanup-nyc-planes", 2),
    ]
    for row in rows:
        assert sorted(row) == sorted(e3.LEDGER_FIELDS)
        assert row["arm"] == "baseline" and row["model"] == "claude-sonnet-5" and row["stance"] == "cleanup"
        assert row["disposition"] == "draft_written" and row["technical"] is False
        assert row["technical_attempt"] is None and row["rerun"] is False and row["continued"] is False
        assert row["prompt_version"] == "1.0.0" and row["context_hash"] is None
        # nyc-airlines is a 0/0 fixture at head; planes shares two names,
        # five first-class fields each (the unchanged scorer).
        planes = row["label"] == "silver-cleanup-nyc-planes"
        assert row["checked"] == (10 if planes else 0) and 0 <= row["agree"] <= row["checked"]
        assert row["shared_columns"] == (2 if planes else 0) and row["fields"] == 5
        assert row["oracle_columns"] == (10 if planes else 3)
        assert row["grain_set_equal"] in (True, False) and row["empty_descriptions"] is None  # cleanup carries rationales, no descriptions
        assert row["input_tokens"] == 100 and row["output_tokens"] == 50
        assert row["cost_usd"] == 0.0007
        evidence = root / row["evidence_dir"]
        assert row["evidence_dir"].startswith("runs/baseline/")
        assert sorted(p.name for p in evidence.iterdir()) == [
            "agreement.json", "draft.odcs.yaml", "proposal.json", "record.json",
        ]
        record = json.loads((evidence / "record.json").read_text(encoding="utf-8"))
        assert record["profile_path"].startswith("profiles/")  # relativized
        assert not any(str(root) in str(v) for v in (record["profile_path"], record["prompt_path"], record["draft_path"]))
        assert record["inputs"][0]["path"].startswith("profiles/")
    assert e3.ledger_total(rows) == 0.0028


def test_a_mapping_fixture_records_its_oracle_and_shared_counts(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    arms = _arms(root, baseline={"fixtures": ["mapping-propose-flights"]})
    client = RoutingClient(_queues())
    code, text = _run(root, "baseline", client, arms=arms, repeats=1)
    assert code == 0, text
    row = _rows(root)[0]
    # The Arc 6 reading: 131 of 132 over 33 shared fields times four.
    assert (row["agree"], row["checked"], row["mismatches"]) == (131, 132, 3)
    assert row["fields"] == 4 and row["oracle_columns"] == 33 and row["shared_columns"] == 33
    assert row["grain_set_equal"] is None  # the mapping scorer carries no grain tuple
    assert "agreement=131/132 shared=33 " in text
    out = io.StringIO()
    scores = e3.score(root, out=out, ledger=root / "ledger.jsonl")
    cell = scores["cells"]["baseline|claude-sonnet-5|mapping-propose-flights"]
    assert cell["normalized_median"] == round(131 / (4 * 33), 4) and cell["shared_median"] == 33


def test_a_second_run_of_the_same_batch_skips_every_result_and_calls_nothing(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    arms = _arms(root, baseline={"fixtures": ["silver-cleanup-nyc-airlines"]})
    client = RoutingClient(_queues())
    assert _run(root, "baseline", client, arms=arms, repeats=2)[0] == 0
    before = (root / "ledger.jsonl").read_bytes()
    code, text = _run(root, "baseline", client, arms=arms, repeats=2)
    assert code == 0
    assert len(client.calls) == 2
    assert "BATCH baseline claude-sonnet-5: runs=0 written=0 failed=0 technical=0 lost=0 skipped=2 cost=0.0000 USD; ledger total 0.0014 USD" in text
    assert (root / "ledger.jsonl").read_bytes() == before
    # A larger repeat count runs only the attempts the ledger lacks.
    code, text = _run(root, "baseline", client, arms=arms, repeats=3)
    assert code == 0 and len(client.calls) == 3
    assert "runs=1 written=1" in text and "skipped=2" in text
    assert [r["attempt"] for r in _rows(root)] == [1, 2, 3]


def test_the_bound_is_checked_before_every_call_against_the_ledger(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    arms = _arms(root, baseline={"fixtures": ["silver-cleanup-nyc-airlines"]}, spend_bound_usd=0.0365)
    client = RoutingClient(_queues())
    # The first estimate (0.0363) fits; the second (0.0007 spent + 0.0363) does not.
    code, text = _run(root, "baseline", client, arms=arms, repeats=2)
    assert code == 3
    assert len(client.calls) == 1
    assert "BOUND-STOP ledger total 0.0007 USD plus the next run's estimate 0.0363 USD would pass the bound 0.04 USD; nothing called" in text
    assert "BATCH " not in text
    assert len(_rows(root)) == 1
    # Nothing fits: the stop comes before the first call.
    root2 = mirrored_root(tmp_path, "two")
    client2 = RoutingClient(_queues())
    arms2 = _arms(root2, baseline={"fixtures": ["silver-cleanup-nyc-airlines"]}, spend_bound_usd=0.01)
    code, text = _run(root2, "baseline", client2, arms=arms2, repeats=1)
    assert code == 3 and client2.calls == [] and not (root2 / "ledger.jsonl").exists()
    assert text.splitlines()[0].startswith("SPEND-BOUND 0.01 USD; ledger total 0.0000 USD;")
    assert text.splitlines()[1].startswith("BOUND-STOP ledger total 0.0000 USD plus the next run's estimate 0.0363 USD")


def test_a_fail_closed_result_loses_the_fixtures_remaining_attempts_until_a_person_continues(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    arms = _arms(root, baseline={"fixtures": ["silver-cleanup-nyc-airlines", "silver-cleanup-nyc-planes"]})
    queues = _queues()
    queues["nyc_airlines"] = ["{not json"]  # every attempt fails: the retry budget is spent
    client = RoutingClient(queues)
    code, text = _run(root, "baseline", client, arms=arms, repeats=3)
    assert code == 0  # the batch completes; the loss is reported, not a stop
    assert len(client.calls) == 3 + 3  # one failed run of three attempts, then planes three times
    lines = text.splitlines()
    assert lines[1].startswith(
        "RUN baseline silver-cleanup-nyc-airlines a01 failed_closed attempts=3 lint@1=no grounded@1=no "
        "machine@1=0 judgment@1=0 agreement=- shared=-"
    )
    assert lines[2] == "LOST baseline silver-cleanup-nyc-airlines: failed closed at a01; its remaining attempts are not run unattended (D-10 Amendment G)"
    assert "BATCH baseline claude-sonnet-5: runs=4 written=3 failed=1 technical=0 lost=1 skipped=0" in text
    rows = _rows(root)
    assert [(r["label"], r["attempt"], r["disposition"]) for r in rows] == [
        ("silver-cleanup-nyc-airlines", 1, "failed_closed"),
        ("silver-cleanup-nyc-planes", 1, "draft_written"),
        ("silver-cleanup-nyc-planes", 2, "draft_written"),
        ("silver-cleanup-nyc-planes", 3, "draft_written"),
    ]
    failed = rows[0]
    assert failed["technical"] is False and failed["technical_attempt"] is None and failed["structural_at_1"] == 1
    assert failed["agree"] is None and failed["checked"] is None
    evidence = root / failed["evidence_dir"]
    assert sorted(p.name for p in evidence.iterdir()) == ["raw_response.txt", "record.json"]
    # The next run never re-invokes the lost fixture, with or without the technical flag.
    queues["nyc_airlines"] = [recorded("silver-cleanup-nyc-airlines")]
    client = RoutingClient(queues)
    code, text = _run(root, "baseline", client, arms=arms, repeats=3, rerun_technical=True)
    assert code == 0 and client.calls == []
    assert "LOST baseline silver-cleanup-nyc-airlines: its latest result failed closed; never re-invoked unattended (D-10 Amendment G)" in text
    assert "lost=1 skipped=3" in text
    # A person continues it by name: the remaining attempts run, the failed
    # row stays, and the continued rows say so.
    code, text = _run(root, "baseline", client, arms=arms, repeats=3, continue_lost="silver-cleanup-nyc-airlines")
    assert code == 0 and len(client.calls) == 2
    assert "CONTINUE baseline silver-cleanup-nyc-airlines: its latest result failed closed; re-invoked on a person's instruction after the record was read (D-10 Amendment G)" in text
    assert "runs=2 written=2 failed=0 technical=0 lost=0 skipped=4" in text
    rows = _rows(root)
    airlines = [r for r in rows if r["label"] == "silver-cleanup-nyc-airlines"]
    assert [(r["attempt"], r["disposition"], r["continued"]) for r in airlines] == [
        (1, "failed_closed", False), (2, "draft_written", True), (3, "draft_written", True),
    ]
    # Its latest result is a draft: the next plain run skips it like any result.
    code, text = _run(root, "baseline", client, arms=arms, repeats=3)
    assert code == 0 and len(client.calls) == 2 and "LOST" not in text and "skipped=6" in text
    # The flag names only a fixture the arm runs.
    out = io.StringIO()
    assert e3.run_arm(root, "baseline", client=client, lint_runner=lint_ok, out=out, arms=arms,
                      ledger=root / "ledger.jsonl", evidence_dir=root / "runs", continue_lost="mapping-propose-flights") == 1


def test_a_technical_failure_at_attempt_one_is_rerun_only_once_by_the_flag(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    arms = _arms(root, baseline={"fixtures": ["silver-cleanup-nyc-airlines"]})
    queues = _queues()
    queues["nyc_airlines"] = [connection_error(), recorded("silver-cleanup-nyc-airlines")]
    client = RoutingClient(queues)
    code, text = _run(root, "baseline", client, arms=arms, repeats=2)
    assert code == 0
    assert len(client.calls) == 2
    lines = text.splitlines()
    assert lines[1].startswith("RUN baseline silver-cleanup-nyc-airlines a01 failed_closed technical@1 attempts=1 ")
    assert lines[2].startswith("RUN baseline silver-cleanup-nyc-airlines a02 draft_written attempts=1 ")
    assert "LOST" not in text
    assert "runs=2 written=1 failed=0 technical=1 lost=0 skipped=0" in text
    rows = _rows(root)
    assert rows[0]["technical"] is True and rows[0]["technical_attempt"] == 1 and rows[0]["disposition"] == "failed_closed"
    assert rows[0]["cost_usd"] == 0.0 and rows[0]["input_tokens"] == 0
    assert sorted(p.name for p in (root / rows[0]["evidence_dir"]).iterdir()) == ["record.json"]
    # Without the flag the technical attempt is skipped like a result.
    client = RoutingClient({"nyc_airlines": [recorded("silver-cleanup-nyc-airlines")]})
    code, text = _run(root, "baseline", client, arms=arms, repeats=2)
    assert code == 0 and client.calls == [] and "skipped=2" in text
    # With the flag it is re-invoked once, and the ledger keeps both rows.
    code, text = _run(root, "baseline", client, arms=arms, repeats=2, rerun_technical=True)
    assert code == 0 and len(client.calls) == 1
    assert "RERUN baseline silver-cleanup-nyc-airlines a01: the ledger marks it technical; re-invoked once by a person" in text
    assert "runs=1 written=1 failed=0 technical=0 lost=0 skipped=1" in text
    rows = _rows(root)
    assert [(r["attempt"], r["technical"], r["disposition"], r["rerun"]) for r in rows] == [
        (1, True, "failed_closed", False), (2, False, "draft_written", False), (1, False, "draft_written", True),
    ]
    # The re-run's result now stands; a further flagged run re-invokes nothing.
    code, text = _run(root, "baseline", client, arms=arms, repeats=2, rerun_technical=True)
    assert code == 0 and len(client.calls) == 1 and "skipped=2" in text
    # A re-run that is itself technical is never re-run again.
    root2 = mirrored_root(tmp_path, "two")
    client2 = RoutingClient({"nyc_airlines": [connection_error()]})
    assert _run(root2, "baseline", client2, arms=_arms(root2, baseline={"fixtures": ["silver-cleanup-nyc-airlines"]}), repeats=1)[0] == 0
    assert _run(root2, "baseline", client2, arms=_arms(root2, baseline={"fixtures": ["silver-cleanup-nyc-airlines"]}), repeats=1, rerun_technical=True)[0] == 0
    assert len(client2.calls) == 2
    code, text = _run(root2, "baseline", client2, arms=_arms(root2, baseline={"fixtures": ["silver-cleanup-nyc-airlines"]}), repeats=1, rerun_technical=True)
    assert code == 0 and len(client2.calls) == 2 and "skipped=1" in text
    assert [r["rerun"] for r in _rows(root2)] == [False, True]


def test_a_transport_failure_on_a_retry_turn_keeps_attempt_one_as_a_result(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    arms = _arms(root, baseline={"fixtures": ["silver-cleanup-nyc-airlines"]})
    queues = _queues()
    queues["nyc_airlines"] = ["{not json", connection_error(), recorded("silver-cleanup-nyc-airlines")]
    client = RoutingClient(queues)
    code, text = _run(root, "baseline", client, arms=arms, repeats=2)
    assert code == 0 and len(client.calls) == 3  # a1: answer, then the raise; a2: an answer
    lines = text.splitlines()
    assert lines[1].startswith("RUN baseline silver-cleanup-nyc-airlines a01 failed_closed technical@2 attempts=2 lint@1=no grounded@1=no machine@1=0 judgment@1=0 ")
    assert "LOST" not in text and "technical=0" in text and "failed=1" in text
    rows = _rows(root)
    first = rows[0]
    assert first["technical"] is False and first["technical_attempt"] == 2 and first["structural_at_1"] == 1
    assert first["disposition"] == "failed_closed" and first["agree"] is None
    # Neither re-run by the flag nor lost: a result for the first-attempt rates.
    client = RoutingClient({"nyc_airlines": [recorded("silver-cleanup-nyc-airlines")]})
    code, text = _run(root, "baseline", client, arms=arms, repeats=2, rerun_technical=True)
    assert code == 0 and client.calls == [] and "skipped=2" in text and "LOST" not in text


def test_a_precondition_refusal_stops_the_batch_without_a_ledger_row(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    arms = _arms(root, baseline={"fixtures": ["silver-cleanup-nyc-airlines"]})
    e3.fixtures_by_label(arms)["silver-cleanup-nyc-airlines"]["profile"] = "profiles/bronze.nyc_airlines/v9999.json"
    client = RoutingClient(_queues())
    code, text = _run(root, "baseline", client, arms=arms, repeats=3)
    assert code == 1 and client.calls == []
    assert "REFUSED baseline silver-cleanup-nyc-airlines a01: the harness refused before any call (exit 1); the batch stops; nothing recorded" in text
    assert not (root / "ledger.jsonl").exists()


def test_arm_a_records_the_context_hash_and_the_context_verbatim(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    arms = _arms(root, A={"fixtures": ["silver-cleanup-nyc-airlines"]}, A1={"fixtures": ["silver-cleanup-nyc-airlines"]})
    client = RoutingClient(_queues())
    code, text = _run(root, "A", client, arms=arms, repeats=1)
    assert code == 0, text
    row = _rows(root)[0]
    context_file = root / "docs/experiments/e3/contexts/silver-cleanup-nyc-airlines.md"
    expected_hash = "sha256:" + hashlib.sha256(context_file.read_bytes()).hexdigest()
    assert row["context_hash"] == expected_hash
    assert row["prompt_version"] == "1.1.0"
    assert row["evidence_dir"].startswith("runs/A/")
    record = json.loads((root / row["evidence_dir"] / "record.json").read_text(encoding="utf-8"))
    assert record["context"] == context_file.read_bytes().decode("utf-8")
    assert record["context_path"] == "docs/experiments/e3/contexts/silver-cleanup-nyc-airlines.md"
    assert record["inputs"][-1]["kind"] == "operator_context"
    assert record["inputs"][-1]["content_hash"] == expected_hash
    assert record["prompt_path"] == "src/metricmine/agents/prompts/e3/silver_cleanup.md"
    content = client.calls[0]["messages"][0]["content"]
    assert content.endswith("</operator_context>")
    # A1 reads the docs-only text of the same fixture.
    code, text = _run(root, "A1", client, arms=arms, repeats=1)
    assert code == 0, text
    row = _rows(root)[1]
    docs_only = root / "docs/experiments/e3/contexts/docs-only/silver-cleanup-nyc-airlines.md"
    assert row["arm"] == "A1" and row["context_hash"] == "sha256:" + hashlib.sha256(docs_only.read_bytes()).hexdigest()
    assert row["context_hash"] != expected_hash


def test_arm_b_runs_the_skeleton_and_the_b_baseline_runs_heads_describe(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    artifact = profile("profiles/silver.silver_airport_weather/v0001.json")
    committed = yaml.safe_load(
        (root / "docs/experiments/e3/fixtures/silver_invoice_lines@1.2.0.odcs.yaml").read_text(encoding="utf-8")
    )
    judgment_schema_digest = e3._schema_digest(root / "docs/spec/agent-layer/e3/table-contract-judgment.schema.json")
    proposal_schema_digest = e3._schema_digest(root / "docs/spec/agent-layer/table-contract-proposal.schema.json")
    fixtures = ["describe-silver-airport-weather", "amend-silver-invoice-lines-f28"]
    arms = _arms(root, B={"fixtures": fixtures}, **{"B-baseline": {"fixtures": fixtures}})

    # Arm B: the model answers with a judgment; code writes the machine half.
    judgment = describe_judgment(artifact)
    client = RoutingClient({
        ("stance: describe (judgment form)", "silver_airport_weather"): [json.dumps(judgment)],
        ("stance: amend (judgment form)", "silver_invoice_lines"): [
            (root / "docs/spec/agent-layer/e3/example-amend-judgment.json").read_text(encoding="utf-8")
        ],
    })
    code, text = _run(root, "B", client, arms=arms, repeats=1)
    assert code == 0, text
    rows = _rows(root)
    assert [r["label"] for r in rows] == fixtures
    for row in rows:
        assert row["disposition"] == "draft_written" and row["attempts"] == 1
        assert row["schema_digest"] == judgment_schema_digest
        assert row["prompt_version"] == "1.1.0"
        assert row["machine_errors_at_1"] == 0 and row["judgment_errors_at_1"] == 0
        assert row["checked"] > 0 and row["empty_descriptions"] == 0
        evidence = root / row["evidence_dir"]
        assert "judgment.json" in {p.name for p in evidence.iterdir()}
        record = json.loads((evidence / "record.json").read_text(encoding="utf-8"))
        assert record["skeleton"] is True
    describe_row, amend_row = rows
    assert describe_row["stance"] == "describe" and amend_row["stance"] == "amend"
    assert describe_row["grain_set_equal"] in (True, False) and describe_row["oracle_columns"] == 18
    amend_record = json.loads((root / amend_row["evidence_dir"] / "record.json").read_text(encoding="utf-8"))
    assert [i["kind"] for i in amend_record["inputs"]] == ["profile_artifact", "committed_contract", "operator_intent"]
    assert amend_record["inputs"][1]["path"] == "docs/experiments/e3/fixtures/silver_invoice_lines@1.2.0.odcs.yaml"
    amend_draft = yaml.safe_load((root / amend_row["evidence_dir"] / "draft.odcs.yaml").read_text(encoding="utf-8"))
    assert str(amend_draft["version"]) == "1.3.0"
    assert amend_draft["customProperties"] and any(
        p["property"] == "amendsContract" and str(p["value"]).startswith("silver_invoice_lines@1.2.0#sha256:")
        for p in amend_draft["customProperties"]
    )
    assert amend_row["agree"] == amend_row["checked"]  # the oracle is the 1.3.0 the arc landed
    assert amend_row["grain_set_equal"] is True

    # B-baseline: head's prompt and schema, the model emits the whole proposal.
    client = RoutingClient({
        ("stance: describe\n", "silver_airport_weather"): [json.dumps(describe_proposal(artifact, judgment))],
        ("stance: amend\n", "silver_invoice_lines"): [json.dumps(amend_proposal(committed))],
    })
    code, text = _run(root, "B-baseline", client, arms=arms, repeats=1)
    assert code == 0, text
    rows = _rows(root)[2:]
    assert [r["arm"] for r in rows] == ["B-baseline", "B-baseline"]
    for row in rows:
        assert row["schema_digest"] == proposal_schema_digest and row["prompt_version"] == "1.0.0"
        assert row["disposition"] == "draft_written"
        evidence = root / row["evidence_dir"]
        assert "judgment.json" not in {p.name for p in evidence.iterdir()}
        assert json.loads((evidence / "record.json").read_text(encoding="utf-8"))["skeleton"] is False
    # The same judgment through both arms renders the same draft bytes
    # apart from the stamp lines: the skeleton adds nothing of its own.
    b_draft = (root / _rows(root)[0]["evidence_dir"] / "draft.odcs.yaml").read_text(encoding="utf-8")
    bb_draft = (root / rows[0]["evidence_dir"] / "draft.odcs.yaml").read_text(encoding="utf-8")

    def strip(text: str) -> list[str]:
        kept: list[str] = []
        skip_next = False
        for line in text.splitlines():
            if skip_next:
                skip_next = False
                continue
            if "promptVersion" in line or "proposedAt" in line:
                skip_next = True  # the property line and its value line
                continue
            if "Draft proposed by" in line:
                continue
            kept.append(line)
        return kept

    assert strip(b_draft) == strip(bb_draft)
    # The retry message names what the model emits.
    assert "The judgment failed validation" not in text  # no retry happened here
    bad = describe_judgment(artifact)
    bad["column_prose"][0]["name"] = "ghost"
    client = RoutingClient({("judgment form", "silver_airport_weather"): [json.dumps(bad), json.dumps(judgment)]})
    code, _ = _run(mirrored_root(tmp_path, "two"), "B", client, arms=_arms(root, B={"fixtures": [fixtures[0]]}), repeats=1)
    assert code == 0
    assert client.calls[1]["messages"][2]["content"].startswith("The judgment failed validation. Errors:\njudgment: ")
    assert client.calls[1]["messages"][2]["content"].endswith("Emit a corrected judgment.")


def test_a_machine_half_error_under_the_b_baseline_is_classified_machine(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    artifact = profile("profiles/silver.silver_airport_weather/v0001.json")
    arms = _arms(root, **{"B-baseline": {"fixtures": ["describe-silver-airport-weather"]}})
    wrong = describe_proposal(artifact)
    wrong["columns"][0]["required"] = not wrong["columns"][0]["required"]
    right = describe_proposal(artifact)
    client = RoutingClient({"silver_airport_weather": [json.dumps(wrong), json.dumps(right)]})
    code, text = _run(root, "B-baseline", client, arms=arms, repeats=1)
    assert code == 0, text
    row = _rows(root)[0]
    assert row["attempts"] == 2 and row["disposition"] == "draft_written"
    assert row["machine_errors_at_1"] == 1 and row["judgment_errors_at_1"] == 0
    # The required flag is a groundedness check at head: the first attempt
    # fails groundedness and never reaches lint.
    assert row["first_attempt_lint_pass"] is False and row["first_attempt_groundedness_pass"] is False
    assert "machine@1=1 judgment@1=0" in text
    assert client.calls[1]["messages"][2]["content"].startswith("The proposal failed validation. Errors:\n")


def test_the_screen_refuses_the_banned_words_key_material_and_home_paths() -> None:
    assert e3.screen_text("A clean sentence.\n") == ([], 0)
    assert e3.screen_text("one \u2014 two \u2014 three") == ([], 2)
    for word in ("port" + "folio", "HIR" + "ING", "Recr" + "uit", "res" + "ume", "through" + "put", "trusted " + "by"):
        refusals, _ = e3.screen_text(f"x {word}ing y")  # a prefix match, as the website's gate
        assert refusals == [f"employer-safe word {word!r}"], word
    assert e3.screen_text("the " + "SL" + "A holds")[0] == ["service-level claim"]
    assert e3.screen_text("island")[0] == []  # the word boundary
    assert e3.screen_text("sk-" + "ant-" + "abcdefghijklmnop")[0] == ["key material"]
    assert e3.screen_text("ANTHROPIC" + "_API_KEY" + "=abc")[0] == ["key material"]
    assert e3.screen_text("ANTHROPIC" + "_API_KEY lives in the environment")[0] == []
    assert e3.screen_text("at /" + "Users/someone/code/x.yaml")[0] == ["a path under a home directory"]
    assert e3.screen_text("at /" + "home/someone/x")[0] == ["a path under a home directory"]
    assert e3.screen_text("at C:\\Users\\someone\\x")[0] == ["a path under a home directory"]
    assert e3.screen_text("profiles/silver.silver_flights/v0001.json")[0] == []


def test_a_screen_refusal_stops_the_batch_after_the_ledger_row(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    arms = _arms(root, baseline={"fixtures": ["silver-cleanup-nyc-airlines"]})
    planted = json.loads(recorded("silver-cleanup-nyc-airlines"))
    planted["purpose"] = planted["purpose"] + " Trus" + "ted " + "by everyone \u2014 really."
    client = RoutingClient({"nyc_airlines": [json.dumps(planted)]})
    code, text = _run(root, "baseline", client, arms=arms, repeats=2)
    assert code == 3
    assert len(client.calls) == 1
    assert "SCREEN-STOP baseline silver-cleanup-nyc-airlines a01: screen refused " in text
    assert "employer-safe word 'Trus" + "ted by'" in text and "the attempt stays in the outbox only" in text
    rows = _rows(root)
    assert len(rows) == 1 and rows[0]["disposition"] == "draft_written"
    assert not (root / rows[0]["evidence_dir"]).exists()
    assert list((root / "proposals").rglob("draft.odcs.yaml"))
    # An em dash alone is reported, never refused.
    root2 = mirrored_root(tmp_path, "two")
    dashed = json.loads(recorded("silver-cleanup-nyc-airlines"))
    dashed["purpose"] = dashed["purpose"] + " One \u2014 two."
    client = RoutingClient({"nyc_airlines": [json.dumps(dashed)]})
    code, text = _run(root2, "baseline", client, arms=_arms(root2, baseline={"fixtures": ["silver-cleanup-nyc-airlines"]}), repeats=1)
    assert code == 0
    assert "(screen: 0 refusal(s), 3 em dash(es) reported)" in text  # the proposal, the draft, and the agreement record each carry it


def test_copy_evidence_relativizes_the_record_and_copies_nothing_on_a_refusal(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    run_dir = root / "proposals" / "x" / "run"
    run_dir.mkdir(parents=True)
    record = {
        "profile_path": str(root / "profiles/p.json"), "inputs": [{"path": str(root / "a.yaml")}],
        "errors": [f"staleness: input operator_context at {root / 'c.md'} moved"], "other": "text",
    }
    (run_dir / "record.json").write_text(json.dumps(record), encoding="utf-8")
    (run_dir / "proposal.json").write_text('{"purpose": "fine \u2014 fine"}', encoding="utf-8")
    dest = tmp_path / "evidence" / "a01"
    assert e3.copy_evidence(root, run_dir, dest) == (2, 1)
    copied = json.loads((dest / "record.json").read_text(encoding="utf-8"))
    assert copied == {
        "profile_path": "profiles/p.json", "inputs": [{"path": "a.yaml"}],
        "errors": ["staleness: input operator_context at c.md moved"], "other": "text",
    }
    assert (dest / "record.json").read_bytes().endswith(b"\n")
    (run_dir / "proposal.json").write_text('{"purpose": "res' + 'ume"}', encoding="utf-8")
    dest2 = tmp_path / "evidence" / "a02"
    with pytest.raises(e3.E3Error, match="screen refused proposal.json: employer-safe word"):
        e3.copy_evidence(root, run_dir, dest2)
    assert not dest2.exists()


def _row(arm: str, label: str, attempt: int, *, stance: str = "cleanup", model: str = "claude-sonnet-5",
         disposition: str = "draft_written", agree: int | None = 5, checked: int | None = 5,
         oracle_columns: int = 10, fields: int = 5, shared: int | None = None,
         lint: bool = True, grounded: bool = True, machine: int = 0, judgment: int = 0,
         technical: bool = False, technical_attempt: int | None = None, attempts: int = 1,
         out_tokens: int = 1000, grain: bool = True, empty: int = 0) -> dict:
    row = dict.fromkeys(e3.LEDGER_FIELDS)
    if shared is None and checked is not None:
        shared = checked // fields
    row.update(
        arm=arm, model=model, label=label, attempt=attempt, stance=stance, disposition=disposition,
        attempts=attempts, first_attempt_lint_pass=lint, first_attempt_groundedness_pass=grounded,
        machine_errors_at_1=machine, judgment_errors_at_1=judgment, structural_at_1=0,
        agree=agree, checked=checked, mismatches=(checked - agree) if checked is not None and agree is not None else None,
        oracle_columns=oracle_columns if checked is not None else None, shared_columns=shared,
        draft_columns=oracle_columns if checked is not None else None, fields=fields,
        grain_set_equal=grain if disposition == "draft_written" else None, grain_order_equal=grain if disposition == "draft_written" else None,
        empty_descriptions=empty, input_tokens=100, output_tokens=out_tokens, cost_usd=0.01, prompt_version="1.0.0",
        schema_digest="sha256:x", context_hash=None, technical=technical, technical_attempt=technical_attempt,
        rerun=False, continued=False, created_at="2026-10-24T00:00:00+00:00",
        evidence_dir=f"runs/{arm}/{label}/a{attempt:02d}",
    )
    return row


def _write_ledger(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def _score(root: Path, rows: list[dict]) -> tuple[dict, str]:
    ledger = root / "ledger.jsonl"
    _write_ledger(ledger, rows)
    out = io.StringIO()
    scores = e3.score(root, out=out, ledger=ledger)
    return scores, out.getvalue()


def test_the_scorer_reports_not_measured_until_every_cell_is_present_and_resolved(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    scores, text = _score(root, [])
    assert text.splitlines() == ["VERDICT E3a: not measured", "VERDICT E3b: not measured",
                                 "SCORES 0 cell(s) over 0 ledger row(s); ledger total 0.0000 USD"]
    assert scores["verdict"]["E3a"]["measured"] is False and scores["verdict"]["E3b"]["measured"] is False
    assert (root / "scores.json").exists() and (root / "scores.md").exists()
    arms = e3.load_arms(root)
    rows = [_row("baseline", lab, 1) for lab in arms["arms"]["baseline"]["fixtures"]]
    scores, text = _score(root, rows)
    assert "VERDICT E3a: not measured" in text
    assert len(scores["cells"]) == 11
    assert all(c["unresolved"] for c in scores["cells"].values())
    # Every cell present but one below the floor: still not measured, and named.
    rows = _full_study(root)
    rows = [r for r in rows if not (r["arm"] == "A" and r["label"] == "silver-cleanup-nyc-planes" and r["attempt"] > 2)]
    scores, text = _score(root, rows)
    assert "VERDICT E3a: not measured" in text and "VERDICT E3b: earned" in text
    assert scores["verdict"]["E3a"]["unresolved_cells"] == ["A|claude-sonnet-5|silver-cleanup-nyc-planes"]
    assert scores["cells"]["A|claude-sonnet-5|silver-cleanup-nyc-planes"]["n"] == 2


def _full_study(root: Path, *, repeats: int = 5, a_agree: int = 30, a_zero_checked: int = 3,
                b_machine: int = 0, b_judgment_runs: int = 0, b_agree: int = 40, b_out: int = 400,
                with_a0: bool = True) -> list[dict]:
    """A ledger that meets every rule: baseline 30 of 50 on the five
    comparable A fixtures, A at `a_agree` of 50; the three 0/0 fixtures at
    0/0 under the baseline and at `a_zero_checked` shared fields under A;
    A0 at 0/0; B-baseline with one machine and one judgment error per run
    at 40 of 50; B clean at `b_agree` of 50 with fewer output tokens."""
    arms = e3.load_arms(root)
    by_label = e3.fixtures_by_label(arms)
    zero = set(arms["zero_fixtures"])
    rows = []
    for lab in arms["arms"]["baseline"]["fixtures"]:
        for attempt in range(1, repeats + 1):
            if lab in zero:
                rows.append(_row("baseline", lab, attempt, agree=0, checked=0))
            else:
                rows.append(_row("baseline", lab, attempt, agree=30, checked=50))
    for lab in arms["arms"]["A"]["fixtures"]:
        for attempt in range(1, repeats + 1):
            if lab in zero:
                rows.append(_row("A", lab, attempt, agree=a_zero_checked, checked=a_zero_checked, shared=1 if a_zero_checked else 0))
            else:
                rows.append(_row("A", lab, attempt, agree=a_agree, checked=50))
    if with_a0:
        for lab in arms["arms"]["A0"]["fixtures"]:
            for attempt in range(1, repeats + 1):
                rows.append(_row("A0", lab, attempt, agree=0, checked=0))
    for lab in arms["arms"]["B"]["fixtures"]:
        stance = by_label[lab]["stance"]
        for attempt in range(1, repeats + 1):
            rows.append(_row("B-baseline", lab, attempt, stance=stance, agree=40, checked=50, machine=1, judgment=1, out_tokens=1000))
            rows.append(_row("B", lab, attempt, stance=stance, agree=b_agree, checked=50,
                             machine=b_machine, judgment=1 if attempt <= b_judgment_runs else 0, out_tokens=b_out))
    return rows


def test_the_scorer_earns_both_verdicts_on_a_ledger_that_meets_every_rule(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    scores, text = _score(root, _full_study(root))
    assert "VERDICT E3a: earned" in text and "VERDICT E3b: earned" in text
    e3a, e3b = scores["verdict"]["E3a"], scores["verdict"]["E3b"]
    assert e3a["rule1_fixtures_off_zero"] == ["silver-cleanup-nyc-flights", "silver-cleanup-nyc-weather", "silver-cleanup-nyc-airlines"]
    assert e3a["rule1_shared_median"]["silver-cleanup-nyc-flights"] == 1
    assert e3a["rule2_fixtures_below_baseline"] == [] and e3a["rule3"] is True
    assert sorted(e3a["rule2_compared"]) == sorted(
        lab for lab in e3.load_arms(root)["arms"]["A"]["fixtures"] if lab not in e3.load_arms(root)["zero_fixtures"]
    )
    assert e3a["rule4_a0_alone_satisfies_rule1"] is False and e3a["rule4"] is True
    assert e3a["a1_docs_only_checked_median"]["silver-cleanup-nyc-flights"] is None  # A1 is reported, never a condition
    assert e3b["rule1_machine_errors_B"] == 0 and e3b["rule1_machine_errors_B_baseline"] == 15
    assert e3b["rule1_machine_runs_B_baseline"] == 15
    assert e3b["rule2"] is True and e3b["rule3_fixtures_below_B_baseline"] == []
    assert all(v["output_token_saving"] == 0.6 for v in e3b["rule4_token_split"].values())
    assert all(v["structure_share_chars_median"] is None for v in e3b["rule4_token_split"].values())  # no evidence files here
    cell = scores["cells"]["A|claude-sonnet-5|silver-cleanup-nyc-flights"]
    assert cell["n"] == 5 and cell["checked_median"] == 3 and cell["fraction_median"] == 1.0 and cell["unresolved"] is False
    assert cell["normalized_median"] == round(3 / 50, 4)
    markdown = (root / "scores.md").read_text(encoding="utf-8")
    assert "| A | claude-sonnet-5 | silver-cleanup-nyc-flights | 5 |" in markdown
    assert "## Verdict" in markdown


def test_each_rule_withholds_its_verdict_on_its_own_with_the_stated_tolerance(tmp_path: Path) -> None:
    root = mirrored_root(tmp_path)
    # E3a rule 1: the 0/0 fixtures stay at zero checked under A.
    scores, text = _score(root, _full_study(root, a_zero_checked=0))
    assert "VERDICT E3a: not earned" in text and scores["verdict"]["E3a"]["rule1"] is False
    # E3a rule 2: a fixture's normalized median falls below the baseline's
    # by more than one field's worth (1/50); one field's worth is tolerated.
    scores, _ = _score(root, _full_study(root, a_agree=28))
    assert scores["verdict"]["E3a"]["rule2"] is False and scores["verdict"]["E3a"]["earned"] is False
    scores, _ = _score(root, _full_study(root, a_agree=29))
    assert scores["verdict"]["E3a"]["rule2"] is True
    # E3a rule 3: one attempt below is within noise; two are not.
    rows = _full_study(root)
    a_rows = [r for r in rows if r["arm"] == "A"]
    a_rows[0]["first_attempt_lint_pass"] = False
    scores, _ = _score(root, rows)
    assert scores["verdict"]["E3a"]["rule3"] is True
    a_rows[1]["first_attempt_lint_pass"] = False
    scores, _ = _score(root, rows)
    assert scores["verdict"]["E3a"]["rule3"] is False
    # E3a rule 4: A0 alone satisfying rule 1 withholds the verdict; A0 absent is not measured.
    rows = _full_study(root)
    for r in rows:
        if r["arm"] == "A0":
            r["agree"] = r["checked"] = 3
            r["shared_columns"] = 1
    scores, _ = _score(root, rows)
    assert scores["verdict"]["E3a"]["rule4"] is False and scores["verdict"]["E3a"]["earned"] is False
    scores, text = _score(root, _full_study(root, with_a0=False))
    assert "VERDICT E3a: not measured" in text
    # E3b rule 1: a machine-half error under B (unreachable by construction; held as a check).
    scores, text = _score(root, _full_study(root, b_machine=1))
    assert "VERDICT E3b: not earned" in text and scores["verdict"]["E3b"]["rule1"] is False
    # E3b rule 2: judgment errors more frequent under B than under B-baseline by more than one attempt.
    scores, _ = _score(root, _full_study(root, b_judgment_runs=5))
    assert scores["verdict"]["E3b"]["rule2"] is True  # equal rates
    rows = _full_study(root, b_judgment_runs=2)
    for row in rows:
        if row["arm"] == "B-baseline":
            row["judgment_errors_at_1"] = 0
    scores, _ = _score(root, rows)
    assert scores["verdict"]["E3b"]["rule2"] is False
    rows = _full_study(root, b_judgment_runs=1)
    for row in rows:
        if row["arm"] == "B-baseline":
            row["judgment_errors_at_1"] = 0
    scores, _ = _score(root, rows)
    assert [list(x) for x in scores["verdict"]["E3b"]["rule2_judgment_runs"]["describe"]] == [[2, 10], [0, 10]]
    assert scores["verdict"]["E3b"]["rule2"] is False  # 2 of 10 is two attempts above 0 of 10
    rows = _full_study(root, b_judgment_runs=1)
    for row in rows:
        if row["arm"] == "B-baseline" and row["stance"] == "amend":
            row["judgment_errors_at_1"] = 0
    scores, _ = _score(root, rows)
    assert [list(x) for x in scores["verdict"]["E3b"]["rule2_judgment_runs"]["amend"]] == [[1, 5], [0, 5]]
    assert scores["verdict"]["E3b"]["rule2"] is True  # one attempt above: within noise
    # E3b rule 3: agreement below the B-baseline on one fixture, past the tolerance.
    scores, _ = _score(root, _full_study(root, b_agree=38))
    assert scores["verdict"]["E3b"]["rule3"] is False
    scores, _ = _score(root, _full_study(root, b_agree=39))
    assert scores["verdict"]["E3b"]["rule3"] is True
    # E3b rule 4: the split is over first-attempt runs only.
    rows = _full_study(root)
    for row in rows:
        if row["arm"] == "B":
            row["attempts"] = 2
    scores, _ = _score(root, rows)
    assert scores["verdict"]["E3b"]["rule4"] is False
    assert scores["cells"]["B|claude-sonnet-5|describe-silver-flights"]["n_first_attempt_only"] == 0
    # A technical row is excluded from every cell's results and counted apart;
    # a transport failure on a retry turn stays a result.
    rows = _full_study(root)
    rows.append(_row("A", "silver-cleanup-nyc-planes", 6, technical=True, technical_attempt=1, disposition="failed_closed", agree=None, checked=None))
    rows.append(_row("A", "silver-cleanup-nyc-planes", 7, technical_attempt=2, attempts=2, disposition="failed_closed", agree=None, checked=None))
    scores, _ = _score(root, rows)
    cell = scores["cells"]["A|claude-sonnet-5|silver-cleanup-nyc-planes"]
    assert cell["n"] == 6 and cell["technical"] == 1 and cell["technical_on_retry"] == 1


def test_classify_errors_sorts_the_validators_own_strings_into_the_classes() -> None:
    # The strings as validate.py and harness.py emit them (the class table,
    # KEY.md Section 9); a staleness or api-error string is counted nowhere.
    machine_describe = [
        "completeness: columns must enumerate the profiled columns in profile order",
        "groundedness: column 'ghost' is not a column of the profiled table",
        "groundedness: column 'a'.physical_type 'X' disagrees with the profiled 'Y'",
        "groundedness: column 'a'.required True disagrees with the profiled null_rate 0.1",
        "completeness: column 'a'.logical_type 'string' must be 'integer' for physical_type 'INTEGER'",
        "completeness: exactly one row_count_positive rule is required",
        "completeness: exactly one grain_unique rule is required",
        "groundedness: target_schema 'x' is not the profiled schema",
        "groundedness: target_table 'x' is not the profiled table",
        "completeness: stance must be 'describe'",
        "completeness: proposed_version 'x' is not a semver",
        "completeness: describe must carry an empty changes list",
        "completeness: table-level rule row_count_positive names a column",
    ]
    for error in machine_describe:
        assert e3.classify_errors("describe", [error]) == (1, 0, 0), error
    machine_amend = [
        "completeness: 'a' re-emits physical_type 'X' against the committed 'Y' with no declared retype_column",
        "completeness: 'a' re-emits required False against the committed True with no declared required_change",
        "completeness: 'a' is absent from columns[] with no declared drop_column",
        "completeness: 'a' is new in columns[] with no declared add_column",
        "completeness: grain_keys differ from the committed grain with no declared grain_change",
        "completeness: drop_column 'a' still appears in columns[]",
        "completeness: grain_change after 'a' disagrees with grain_keys ['b']",
        "completeness: added column 'a' must enter required false (F-28)",
        "completeness: proposed_version '9.9.9' must be '1.3.0': the committed '1.2.0' bumped 'minor'",
    ]
    for error in machine_amend:
        assert e3.classify_errors("amend", [error]) == (1, 0, 0), error
    judgment = [
        "completeness: at least one grain key is required",
        "judgment: column_prose names 'ghost', which the skeleton does not carry",
        "groundedness: not_null on 'a' contradicts its nonzero profiled null_rate",
        "relaxation: narrowing change required_change on 'a' needs --allow-relaxation",
        "completeness: rule_change adds 'not_null:a' but no quality_rules[] entry carries its definition",
        "datacontract lint failed:\n...",
        "contract schema: 'x' is a required property",
    ]
    for error in judgment:
        assert e3.classify_errors("describe", [error]) == (0, 1, 0), error
        assert e3.classify_errors("amend", [error]) == (0, 1, 0), error
    structural = [
        "response is not valid JSON: Expecting value",
        "response stopped on 'max_tokens', not end_turn; the proposal is incomplete",
        "proposal schema: 'stance' is a required property",
    ]
    for error in structural:
        assert e3.classify_errors("describe", [error]) == (0, 0, 1), error
    unclassed = [
        "staleness: input operator_context at x moved to y after binding to z",
        "api error: APIConnectionError: Connection error.",
    ]
    for error in unclassed:
        assert e3.classify_errors("describe", [error]) == (0, 0, 0), error
        assert e3.classify_errors("cleanup", [error]) == (0, 0, 0), error
    # The cleanup and propose stances carry no machine half: every error is judgment.
    assert e3.classify_errors("cleanup", ["groundedness: column 'a'.physical_type 'X' disagrees"]) == (0, 1, 0)
    assert e3.classify_errors("propose", ["completeness: proposed_version"]) == (0, 1, 0)
    assert e3.classify_errors("describe", []) == (0, 0, 0)


def test_the_finding_renderer_types_no_number_and_refuses_blanks(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "render_finding", REPO_ROOT / "docs" / "experiments" / "e3" / "render_finding.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    root = mirrored_root(tmp_path)
    # A writable e3 folder beside the linked docs: the renderer reads
    # scores.json and ledger.jsonl from docs/experiments/e3/.
    (root / "docs").unlink()
    (root / "docs").mkdir()
    for child in (REPO_ROOT / "docs").iterdir():
        if child.name != "experiments":
            (root / "docs" / child.name).symlink_to(child, target_is_directory=child.is_dir())
    (root / "docs" / "experiments").mkdir()
    for child in (REPO_ROOT / "docs" / "experiments").iterdir():
        if child.name != "e3":
            (root / "docs" / "experiments" / child.name).symlink_to(child, target_is_directory=child.is_dir())
    e3_dir = root / "docs" / "experiments" / "e3"
    e3_dir.mkdir()
    for child in (REPO_ROOT / "docs" / "experiments" / "e3").iterdir():
        if child.name not in ("ledger.jsonl", "scores.json", "scores.md", "runs"):
            (e3_dir / child.name).symlink_to(child, target_is_directory=child.is_dir())
    bounds = tmp_path / "bounds.md"
    possible = tmp_path / "possible.md"
    out = tmp_path / "finding.md"
    bounds.write_text("What it bounds.\n", encoding="utf-8")
    possible.write_text("What remains.\n", encoding="utf-8")
    args = ["--key-commit", "abc1234", "--bounds", str(bounds), "--possible", str(possible),
            "--out", str(out), "--repo", str(root), "--today", "2026-10-24"]
    # No scores yet: refused.
    with pytest.raises(SystemExit, match="scores.json"):
        module.main(args)
    rows = _full_study(root)
    _write_ledger(e3_dir / "ledger.jsonl", rows)
    e3.score(root, out=io.StringIO())
    assert module.main(args) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# E3, the skeleton and the context channel: measured (2026-10-24)")
    for heading in ("## The question", "## The rule", "## What was measured", "## The result, as measured",
                    "### E3a by the rule", "### E3b by the rule", "## What the result bounds",
                    "## What remains possible", "## Status"):
        assert heading in text, heading
    assert "**E3a: earned.**" in text and "**E3b: earned.**" in text
    assert "What it bounds." in text and "What remains." in text
    assert f"ledger total\n${e3.ledger_total(rows):.4f} against the bound $200.00" in text
    assert "| `A` | `claude-sonnet-5` | 40 | 40 | 0 | 0 |" in text
    assert "| `A1` " not in text.split("## The result, as measured")[0]  # not run: no row
    assert "No ledger row for `A1`" in text
    assert "`abc1234`" in text
    assert "\u2014" not in text
    # An empty narrative file is refused; an unmeasured question is refused unless named.
    possible.write_text("\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="is empty"):
        module.main(args)
    possible.write_text("What remains.\n", encoding="utf-8")
    _write_ledger(e3_dir / "ledger.jsonl", [r for r in rows if r["arm"] not in ("B", "B-baseline")])
    e3.score(root, out=io.StringIO())
    with pytest.raises(SystemExit, match="E3b is not measured"):
        module.main(args)
    assert module.main(args + ["--allow-unmeasured", "E3b"]) == 0
    assert "Not measured: the ledger lacks arm B" in out.read_text(encoding="utf-8")
