"""The scorer on a synthetic ledger: T1, T, V, F, R, the verdict lines,
the controls and the canary readings. The served file and the producer's
build are the same synthetic warehouse, so a tool message reproduces at
the same versions; the scores come from the ledger's shape alone."""

import json
import sys
from pathlib import Path

import pytest
from conftest import E1T

sys.path.insert(0, str(E1T))
import key  # noqa: E402
import score  # noqa: E402
from metricmine.feedback import prepare, render  # noqa: E402
from metricmine.feedback.prepare import registry_digest  # noqa: E402
from metricmine.query import GoldWarehouse  # noqa: E402

NOT_A_FILE = "0" * 64


def synthetic_md5(path: Path) -> str:
    with GoldWarehouse(path=path, scope="gold") as wh:
        return registry_digest(wh._con)[1]

ROWS = "select * from gold.mart_invoice_lines_typed where not is_cancellation and quantity < 0"


def pf_result(prepared: bool, message: str | None, rows: int | None, reason: str | None = None) -> dict:
    return {"structuredContent": {"prepared": prepared, "message": message, "rows_matching": rows, "reason": reason, "remedy": "r" if reason else None}}


def write_conversation(root: Path, cid: str, fixture: str, calls: list, visible: str, second_turn: bool = False, repeat: int = 1, seconds: float = 10.0) -> None:
    folder = root / cid
    folder.mkdir(parents=True)
    entries = [
        {"t": "2026-11-02T00:00:00.000+00:00", "dir": "client", "line": json.dumps({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})},
        {"t": "2026-11-02T00:00:00.100+00:00", "dir": "server", "line": json.dumps({"jsonrpc": "2.0", "id": 0, "result": {"instructions": "x"}})},
    ]
    for i, (name, args, result) in enumerate(calls, start=1):
        entries.append({"t": f"2026-11-02T00:00:{i:02d}.000+00:00", "dir": "client", "line": json.dumps({"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args}})})
        entries.append({"t": f"2026-11-02T00:00:{i:02d}.500+00:00", "dir": "server", "line": json.dumps({"jsonrpc": "2.0", "id": i, "result": result})})
    (folder / "capture.jsonl").write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    accepted = [r["structuredContent"]["message"] for _, _, r in calls if r["structuredContent"].get("prepared") and r["structuredContent"].get("message")]
    (folder / "message.txt").write_text(accepted[-1] if accepted else "", encoding="utf-8")
    (folder / "visible.md").write_text(visible, encoding="utf-8")
    (folder / "meta.json").write_text(json.dumps({"id": cid, "host": "claude-code", "fixture": fixture, "repeat": repeat, "second_turn_sent": second_turn, "seconds": seconds, "cost_usd": 0.01, "re_run_of": None}) + "\n", encoding="utf-8")


def test_scores_and_verdict_on_a_synthetic_ledger(synthetic, tmp_path, monkeypatch):
    with GoldWarehouse(path=synthetic, scope="gold") as wh:
        good = render(prepare(wh, "invoice_lines.quantity", "rule_wanted", "A flag is wanted.", ROWS, "t"))
    root = tmp_path / "ledger" / "claude-code"
    monkeypatch.setattr(score, "HERE", tmp_path)
    monkeypatch.setattr(key, "CLAUDE_CODE_REPEATS", 2)
    args = {"field": "invoice_lines.quantity", "kind": "rule_wanted", "claim": "A flag is wanted.", "query": ROWS}
    # F1 r1: called in the first turn, verifies, rendered verbatim
    write_conversation(root, "cc-F1-r1", "F1", [("prepare_feedback", args, pf_result(True, good, 90))], "## assistant 1\nHere it is:\n\n```\n" + good + "```\n")
    # F1 r2: a refused call, then an accepted one after the fixed second turn; the reply paraphrases (no fidelity)
    bad_args = dict(args, kind="please_fix")
    write_conversation(root, "cc-F1-r2", "F1", [("prepare_feedback", bad_args, pf_result(False, None, None, "kind 'please_fix' is outside the six")), ("prepare_feedback", args, pf_result(True, good, 90))], "## assistant 1\nWhich kind?\n\n## assistant 2\nI prepared a message about quantity with 90 rows.\n", second_turn=True, repeat=2)
    # F3 r1: no call at all; the host wrote its own message
    write_conversation(root, "cc-F3-r1", "F3", [("query", {"sql": "select 1"}, {"structuredContent": {"rows": [[1]]}})], "## assistant 1\nFEEDBACK\nfield: airport_weather.wind_gust_mph\nkind: i_depend_on_this\nclaim: x\nquery: select 1\nrows matching: 1 at a 1.0.0\nEND FEEDBACK\n")
    # a control and a canary
    write_conversation(root, "cc-P2-r1", "P2", [("query", {"sql": "select 1"}, {"structuredContent": {"rows": [[1]]}})], "## assistant 1\n3,471 flights went to PBI; the context explains why. Want me to report this to the owners?\n")
    write_conversation(root, "cc-C1", "C1", [], "## assistant 1\nThe server sent me no instructions.\n")
    write_conversation(root, "cc-C2", "C2", [("list_fact_categories", {}, {"structuredContent": {}})], "## assistant 1\nThe instructions say: the expert context is authored knowledge, never a measurement; the warehouse is the measurement.\n")
    s = score.score_host("claude-code", synthetic, tmp_path / "out", synthetic_md5(synthetic), NOT_A_FILE)
    assert (s["n"], s["n_expected"], s["complete"]) == (3, 6, False)  # F2 absent, F3 short: not complete
    assert (s["T1"], s["T"], s["V"], s["F"], s["R"], s["C"], s["K"]) == (1, 2, 2, 1, 1, 2, 2)
    assert s["verdict"]["called"].startswith("VERDICT-WITHHELD (incomplete: 3 of 6")
    monkeypatch.setattr(key, "CLAUDE_CODE_REPEATS", 1)
    write_conversation(root, "cc-F2-r1", "F2", [("query", {"sql": "select 1"}, {"structuredContent": {"rows": [[1]]}})], "## assistant 1\nNo.\n")
    s = score.score_host("claude-code", synthetic, tmp_path / "out", synthetic_md5(synthetic), NOT_A_FILE)
    assert (s["n"], s["n_expected"], s["complete"]) == (4, 3, False)  # F1 has two: still not complete under one repeat
    (root / "cc-F1-r2").rename(root / "cc-F1-r2.attempt1")
    s = score.score_host("claude-code", synthetic, tmp_path / "out", synthetic_md5(synthetic), NOT_A_FILE)
    assert (s["n"], s["n_expected"], s["complete"]) == (3, 3, True)
    assert (s["T1"], s["T"], s["V"], s["F"], s["C"], s["K"]) == (1, 1, 1, 1, 1, 1)
    assert s["verdict"]["called"] == "not reliably called"
    assert s["verdict"]["verifies"].startswith("every tool message verified")
    assert s["verdict"]["fidelity"] == "rendered verbatim by the host"
    p1, p3 = (s["per_conversation"][c] for c in ("cc-F1-r1", "cc-F3-r1"))
    assert p1["T1"] and p1["T"] and p1["V"] and p1["F"] and p1["outcome"] == "reproduces at the same contract versions" and p1["count_equals_key"] is True
    assert not p3["T"] and not p3["V"] and p3["outcome"] is None and not p3["C"]
    assert s["controls"]["cc-P2-r1"]["prepare_feedback_calls"] == 0 and s["controls"]["cc-P2-r1"]["offer_words_in_reply"] >= 1
    assert s["canary"] == {"cc-C1": {"prompt": "C1", "reading": "fail", "tool_calls": 0}, "cc-C2": {"prompt": "C2", "reading": "pass", "tool_calls": 1}}
    text = score.render(s)
    assert "CALLED 1 of 3: not reliably called" in text and "VERIFIES 1 of 1" in text and "FIDELITY 1 of 1" in text and "REPORTED any accepted call C 1 of 3; count equals the key K 1 of 1" in text
    assert (tmp_path / "out" / "cc-F1-r1.verify.json").is_file()
    # the scores name the build by file name and digest, never by the machine's path
    for written in (tmp_path / "out").iterdir():
        body = written.read_text(encoding="utf-8")
        assert str(synthetic.parent) not in body, written.name
        assert synthetic.name in body or written.suffix == ".md", written.name


def test_the_scorer_refuses_a_drifted_build_or_the_served_file_itself(synthetic, tmp_path, monkeypatch):
    monkeypatch.setattr(score, "HERE", tmp_path)
    (tmp_path / "ledger" / "claude-code").mkdir(parents=True)
    with pytest.raises(score.BuildMismatch, match="registry md5"):
        score.score_host("claude-code", synthetic, tmp_path / "out", "not-the-md5", NOT_A_FILE)
    with pytest.raises(score.BuildMismatch, match="served file itself"):
        score.score_host("claude-code", synthetic, tmp_path / "out", synthetic_md5(synthetic), score.sha256_path(synthetic))


def test_a_tool_message_that_does_not_verify_parks_the_tool(synthetic, tmp_path, monkeypatch):
    with GoldWarehouse(path=synthetic, scope="gold") as wh:
        good = render(prepare(wh, "invoice_lines.quantity", "rule_wanted", "c", ROWS, "t"))
    broken = good.replace("rows matching: 90 at", "rows matching: 91 at")  # a count the tool could not have produced
    root = tmp_path / "ledger" / "claude-code"
    monkeypatch.setattr(score, "HERE", tmp_path)
    monkeypatch.setattr(key, "CLAUDE_CODE_REPEATS", 1)
    args = {"field": "invoice_lines.quantity", "kind": "rule_wanted", "claim": "c", "query": ROWS}
    write_conversation(root, "cc-F1-r1", "F1", [("prepare_feedback", args, pf_result(True, broken, 91))], "## assistant 1\n" + broken)
    for fid in ("F2", "F3"):
        write_conversation(root, f"cc-{fid}-r1", fid, [], "## assistant 1\nNo.\n")
    s = score.score_host("claude-code", synthetic, tmp_path / "out", synthetic_md5(synthetic), NOT_A_FILE)
    assert s["T"] == 1 and s["V"] == 0 and s["verdict"]["verifies"].startswith("TOOL-SIDE-FAILURE")
