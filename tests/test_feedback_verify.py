"""verify: the producer's re-measurement, four outcomes (E1T; HW-39a).
Each outcome is produced on the synthetic gold warehouse: the same
build reproduces at the same versions; a build whose mapping contract
moved reports the move; a build with a different count does not
reproduce; a message without the five parts does not parse. The
quoted-sentence check of a meaning kind compares exact text after
whitespace folding and interprets nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from metricmine.feedback import OUTCOME_MOVED, OUTCOME_NO, OUTCOME_PARSE, OUTCOME_SAME, prepare, render, verify
from metricmine.feedback.__main__ import main as cli
from metricmine.query import GoldWarehouse

from feedback_fixtures import MEANING_NEW, MEANING_OLD, build_gold

ROWS = "select * from gold.mart_invoice_lines_typed where not is_cancellation and quantity < 0"


@pytest.fixture
def served(tmp_path: Path) -> Path:
    return build_gold(tmp_path / "served.duckdb")


def _message(path: Path, kind="rule_wanted", claim="A flag is wanted.") -> str:
    with GoldWarehouse(path=path, scope="gold") as wh:
        return render(prepare(wh, "invoice_lines.quantity", kind, claim, ROWS, "0.0.0-test"))


def test_reproduces_at_the_same_versions_on_the_same_build(served):
    r = verify(served, _message(served), "invoice_lines.quantity", "rule_wanted", 90)
    assert r["outcome"] == OUTCOME_SAME and r["verifies"] is True
    assert r["rows_matching_recounted"] == 90 and r["count_equals_key"] is True
    assert r["extra_parts"] == ["served file", "query literals", "caller supplied"]


def test_reproduces_and_the_contract_has_moved_on_a_later_build(served, tmp_path):
    later = build_gold(tmp_path / "later.duckdb", mapping_version="1.1.3")
    r = verify(later, _message(served), "invoice_lines.quantity", "rule_wanted", 90)
    assert r["outcome"] == OUTCOME_MOVED and r["verifies"] is False
    assert r["contracts_moved"] == {"gold_invoice_lines_mapping": {"stated": "1.1.2", "build": "1.1.3"}}


def test_does_not_reproduce_when_the_count_differs(served, tmp_path):
    other = build_gold(tmp_path / "other.duckdb", negatives=91)
    r = verify(other, _message(served))
    assert r["outcome"] == OUTCOME_NO and r["verifies"] is False
    assert (r["rows_matching_stated"], r["rows_matching_recounted"]) == (90, 91)


def test_does_not_parse_without_the_five_parts(served):
    r = verify(served, "I would send this to the owners: quantity looks wrong.")
    assert r["outcome"] == OUTCOME_PARSE and r["verifies"] is False
    broken = _message(served).replace("kind: rule_wanted\n", "")
    r2 = verify(served, broken)
    assert r2["outcome"] == OUTCOME_PARSE and "missing part(s): kind" in r2["reason"]


def test_a_key_mismatch_never_verifies_even_when_it_reproduces(served):
    r = verify(served, _message(served), "invoice_lines.unit_price", "rule_wanted")
    assert r["outcome"] == OUTCOME_SAME and r["verifies"] is False and r["field_matches_key"] is False


def test_the_quoted_sentence_check_of_a_meaning_kind(served, tmp_path):
    claim = f'The meaning "{MEANING_NEW}" is unclear about the price.'
    r = verify(served, _message(served, "meaning_unclear", claim))
    assert r["quoted_sentences"] == [{"quoted": MEANING_NEW, "still_served": True, "found_in_served_context": True}]
    older = build_gold(tmp_path / "older.duckdb", mapping_version="1.1.1", meaning=MEANING_OLD)
    r2 = verify(older, _message(served, "meaning_unclear", claim))
    assert r2["quoted_sentences"][0]["still_served"] is False and r2["quoted_sentences"][0]["found_in_served_context"] is False
    assert r2["outcome"] == OUTCOME_MOVED
    assert r["volatile_calls"] == []


def test_the_command_door_prepares_and_verifies_the_same_message(served, tmp_path, capsys):
    out = tmp_path / "m.txt"
    code = cli(["prepare", "--field", "invoice_lines.quantity", "--kind", "rule_wanted", "--claim", "A flag is wanted.", "--query", ROWS, "--db", str(served), "--out", str(out)])
    assert code == 0 and out.read_text(encoding="utf-8").startswith("FEEDBACK\n")
    code = cli(["verify", "--build", str(served), "--message", str(out), "--key-field", "invoice_lines.quantity", "--key-kind", "rule_wanted", "--key-count", "90", "--json", str(tmp_path / "r.json")])
    printed = capsys.readouterr().out
    assert code == 0 and "OUTCOME: reproduces at the same contract versions" in printed and "VERIFIES: yes" in printed
    assert (tmp_path / "r.json").is_file()
    code = cli(["prepare", "--field", "invoice_lines.quantity", "--kind", "rule_wanted", "--claim", "x", "--query", "delete from gold.mart_invoice_lines_typed", "--db", str(served)])
    assert code == 2 and "REFUSED: query refused" in capsys.readouterr().out


# The twelve messages Prep D wrote for verify-feedback (October 21, 2026),
# each read against a build whose mapping contract is v1.1.1 with the old
# quantity sentence, the state the v1.1.1 asset served. Each file name
# says what the message is; the outcome column says what the command
# reports for it.
TWELVE = {
    "m01_warranted.txt": (OUTCOME_SAME, True),
    "m02_in_chat.md": (OUTCOME_SAME, True),
    "m03_missing_part.txt": (OUTCOME_PARSE, False),
    "m04_out_of_order.txt": (OUTCOME_PARSE, False),
    "m05_aggregate.txt": (OUTCOME_NO, False),
    "m06_two_statements.txt": (OUTCOME_NO, False),
    "m07_write.txt": (OUTCOME_NO, False),
    "m08_outside_gold.txt": (OUTCOME_NO, False),
    "m09_moved.txt": (OUTCOME_MOVED, False),
    "m10_wrong_count.txt": (OUTCOME_NO, False),
    "m11_other_field.txt": (OUTCOME_NO, False),
    "m12_no_block.txt": (OUTCOME_PARSE, False),
}


@pytest.mark.parametrize("name", sorted(TWELVE))
def test_the_twelve_messages_of_prep_d_report_their_outcomes(name, tmp_path):
    old = build_gold(tmp_path / "old.duckdb", mapping_version="1.1.1", meaning=MEANING_OLD)
    text = (Path(__file__).resolve().parent / "fixtures" / "feedback_messages" / name).read_text(encoding="utf-8")
    r = verify(old, text, "invoice_lines.quantity", "meaning_wrong", 90)
    assert (r["outcome"], r["verifies"]) == TWELVE[name], name
