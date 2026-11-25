"""The key's values hold to the served file and to the record (KEY.md)."""

import re
import sys

from conftest import E1T, REPO

sys.path.insert(0, str(E1T))
import key  # noqa: E402

KEY_MD = REPO / "docs" / "experiments" / "e1t" / "KEY.md"


def test_the_fixtures_are_three_fields_in_three_categories_with_distinct_expected_kinds():
    assert [f.id for f in key.FIXTURES] == ["F1", "F2", "F3"]
    assert len({f.field.partition(".")[0] for f in key.FIXTURES}) == 3
    assert len({f.kinds[0] for f in key.FIXTURES}) == 3
    for f in key.FIXTURES:
        assert f.prompt.startswith(key.OPENING) and "show me the message exactly as it was returned" in f.prompt
        assert "prepare_feedback" not in f.prompt and "prepare feedback" not in f.prompt.lower()


def test_acceptable_pairs():
    f1, f2, f3 = key.FIXTURES
    assert key.acceptable(f1, "invoice_lines.quantity", "rule_wanted")
    assert key.acceptable(f1, "invoice_lines.stock_adjustment_flag", "missing_field")
    assert not key.acceptable(f1, "invoice_lines.quantity", "missing_field")
    assert not key.acceptable(f1, "flights.quantity", "rule_wanted")
    assert key.acceptable(f2, "flights.arr_delay_minutes", "meaning_unclear") and key.acceptable(f2, "flights.arr_delay_minutes", "meaning_wrong")
    assert key.acceptable(f2, "flights.arr_delay_minutes", "unexpected_values")
    assert not key.acceptable(f2, "flights.arr_delay_minutes", "missing_field") and not key.acceptable(f2, "flights.arr_delay_minutes", "rule_wanted")
    assert key.acceptable(f3, "airport_weather.wind_gust_mph", "i_depend_on_this") and not key.acceptable(f3, "airport_weather.wind_gust_mph", "rule_wanted")


def test_the_second_turn_rule_reads_the_last_line_only():
    assert key.ends_with_question("I can do that.\n\nWhich kind do you mean?")
    assert not key.ends_with_question("Which kind? Here is the message:\nFEEDBACK\n...\nEND FEEDBACK")
    assert not key.ends_with_question("")


def test_the_key_counts_are_the_served_file_s(pinned):
    from metricmine.feedback import prepare
    from metricmine.query import GoldWarehouse

    queries = {
        "F1": "select * from gold.mart_invoice_lines_typed where not is_cancellation and quantity < 0",
        "F2": "select * from gold.mart_flights_typed where not is_cancelled and arr_delay_minutes is null and arr_hhmm is not null",
        "F3": "select * from gold.mart_airport_weather_typed where wind_gust_mph is not null",
    }
    with GoldWarehouse(path=pinned, scope="gold") as wh:
        for f in key.FIXTURES:
            p = prepare(wh, f.field, f.kinds[0], "the key's count", queries[f.id], "test")
            assert p.rows_matching == f.key_count, f.id
            assert p.served_file_sha256 == key.SERVED_SHA256 and p.served_file_bytes == key.SERVED_BYTES
            assert p.registry_md5 == key.SERVED_REGISTRY_MD5 and p.registry_rows == key.SERVED_REGISTRY_ROWS


def test_the_record_carries_the_key_s_values():
    assert KEY_MD.is_file(), "the key document is part of the branch"
    text = KEY_MD.read_text(encoding="utf-8")
    for value in (
        key.SERVED_SHA256, str(key.SERVED_BYTES), key.SERVED_REGISTRY_MD5, str(key.SERVED_REGISTRY_ROWS),
        key.INSTRUCTIONS_SHA256, str(key.INSTRUCTIONS_LENGTH), key.CANARY_PHRASE, f"offset {key.CANARY_OFFSET}",
        key.SECOND_TURN, f"turn cap of {key.MAX_TURNS}", f"{key.PER_TURN_TIMEOUT_S} seconds", "ten dollars", "one dollar",
        "1000000",
        "five repeats", "three by three", "three repeats",
    ):
        assert value in text, value
    for failure in key.TECHNICAL_FAILURES:
        assert failure in text, failure
    assert re.search(r"at most\s+2000", text)
    for f in key.FIXTURES:
        assert f.field in text and str(f.key_count) in text and f.prompt in text, f.id
    for c in key.CONTROLS.values():
        assert c in text
    for c in key.CANARY_PROMPTS.values():
        assert c in text
    assert re.search(r"T\s*>=\s*n\s*-\s*1", text) or "n - 1" in text
