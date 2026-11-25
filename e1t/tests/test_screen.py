"""The screen catches each class it names, reports the rest, reads the
account names from the local file, and passes a clean ledger file."""

import json
import re
from pathlib import Path

import screen
from conftest import E1T, REPO

CLEAN = "## assistant 1\nThe top five countries by revenue are the United Kingdom, Eire, the Netherlands, Germany, and Spain.\n"
NAMES = re.compile("someuser|Some-Machine", re.I)


def run(tmp_path: Path, name: str, text: str, authored: bool = False, names=NAMES):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return screen.screen_file(p, authored, names)


def test_each_blocking_class_is_caught_and_a_clean_file_passes(tmp_path):
    assert run(tmp_path, "a.md", CLEAN) == ({}, {})
    cases = {
        "local path": "the file at /Users/someone/Documents/x.duckdb",
        "account or machine name": "launched by someuser on Some-Machine",
        "email address": "write to someone@example.com",
        "token or key": "Authorization: Bearer abcdefghijklmnop",
        "token or key 2": "ANTHROPIC_API_KEY=sk-ant-xxxx",
        "employer or career language": "this is a portfolio piece for hiring",
    }
    for label, text in cases.items():
        blocks, _ = run(tmp_path, label.replace(" ", "_") + ".md", text)
        assert blocks, label
        assert label.split(" 2")[0] in blocks, (label, blocks)


def test_a_windows_path_is_caught_in_each_encoding_and_an_encoded_newline_is_not(tmp_path):
    caught = {
        "plain": r"the file at C:\Users\someone\x.duckdb",
        "json": json.dumps({"path": r"C:\Users\someone\x.duckdb"}),
        "capture": json.dumps({"line": json.dumps({"path": r"C:\temp\new\x.duckdb"})}),
    }
    for label, text in caught.items():
        blocks, _ = run(tmp_path, f"w_{label}.md", text)
        assert "local path" in blocks, (label, blocks)
    passed = {
        "capture newline": json.dumps({"line": json.dumps({"description": "under the server's scope:\n    the tool"})}),
        "json newline after a lone letter": json.dumps({"text": "option A:\n    the tool"}),
        "json tab": json.dumps({"text": "e.g.:\tfoo"}),
    }
    for label, text in passed.items():
        blocks, _ = run(tmp_path, f"p_{label.replace(' ', '_')}.md", text)
        assert blocks == {}, (label, blocks)


def test_without_the_names_file_no_name_is_screened_and_the_command_refuses(tmp_path, capsys):
    blocks, _ = run(tmp_path, "n.md", "launched by someuser", names=None)
    assert blocks == {}
    (tmp_path / "ok.md").write_text(CLEAN, encoding="utf-8")
    assert screen.main([str(tmp_path / "ok.md"), "--names", str(tmp_path / "absent.txt")]) == 1
    out = capsys.readouterr().out
    assert "SCREEN-NAMES-MISSING" in out and out.strip().endswith("SCREEN-BLOCKED 1 files, names file missing")


def test_the_names_file_is_read_one_name_per_line_and_matched_as_whole_words(tmp_path):
    names_file = tmp_path / "names.txt"
    names_file.write_text("# derived on the Mac\nsomeuser\nSome-Machine\nvm\n", encoding="utf-8")
    rx = screen.load_names(names_file)
    assert rx is not None and rx.search("by SOMEUSER") and rx.search("on some-machine today") and not rx.search("by nobody")
    assert not rx.search("someuserx") and not rx.search("/tmp/e1t-46vjvmzb")  # a whole word, and a short name set aside
    assert screen.read_names(names_file) == (["someuser", "Some-Machine"], ["vm"])


def test_em_dashes_and_document_references_are_reported_not_blocked_in_a_ledger_file(tmp_path):
    blocks, reports = run(tmp_path, "t.md", "A result — with a dash, and a sources list from the document register.\n")
    assert blocks == {} and reports == {"em dash": 1, "document reference": 1}
    blocks, _ = run(tmp_path, "k.md", "An authored line — with a dash.\n", authored=True)
    assert "em dash" in blocks


def test_a_capture_whose_query_names_another_schema_is_blocked(tmp_path):
    good = {"t": "x", "dir": "client", "line": json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "query", "arguments": {"sql": "select * from gold.mart_flights_typed"}}})}
    bad = {"t": "x", "dir": "client", "line": json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "prepare_feedback", "arguments": {"query": "select * from silver.silver_flights", "field": "flights.x", "kind": "rule_wanted", "claim": "c"}}})}
    p = tmp_path / "capture.jsonl"
    p.write_text(json.dumps(good) + "\n" + json.dumps(bad) + "\n", encoding="utf-8")
    blocks, _ = screen.screen_file(p, False, NAMES)
    assert blocks == {"query outside gold": [2]}


def test_the_command_prints_the_summary_line(tmp_path, capsys):
    names_file = tmp_path / "names.txt"
    names_file.write_text("someuser\n", encoding="utf-8")
    (tmp_path / "ok.md").write_text(CLEAN, encoding="utf-8")
    assert screen.main([str(tmp_path / "ok.md"), "--names", str(names_file)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("SCREEN-NAMES 1 name(s) screened as whole words") and out.strip().endswith("SCREEN-CLEAN 1 files")
    (tmp_path / "bad.md").write_text("mail me at a@b.co\n", encoding="utf-8")
    assert screen.main([str(tmp_path / "ok.md"), str(tmp_path / "bad.md"), "--names", str(names_file)]) == 1
    out = capsys.readouterr().out
    assert "SCREEN-BLOCKED 2 files, 1 blocked" in out and "a@b.co" not in out


def test_the_authored_files_of_the_experiment_screen_clean():
    for path in (E1T / "README.md", REPO / "docs" / "experiments" / "e1t" / "KEY.md", E1T / "key.py"):
        if path.is_file():
            blocks, _ = screen.screen_file(path, True, NAMES)
            assert blocks == {}, (path.name, blocks)
