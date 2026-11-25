"""The five-part layout, read strictly (E1T; the governed host plan, 2.3)."""

from metricmine.feedback.layout import extract_block, parse_block, quoted_spans, split_field

GOOD = """FEEDBACK
field: invoice_lines.quantity
kind: meaning_wrong
claim: The sentence "Units on the line; negative only on cancellations." does not hold.
query: select * from gold.mart_invoice_lines_typed
where not is_cancellation and quantity < 0
rows matching: 90 at gold_invoice_lines_mapping v1.1.1, silver_invoice_lines 1.3.0
END FEEDBACK"""


def test_the_five_parts_parse_in_order_with_a_multi_line_query():
    r = parse_block(extract_block(GOOD))
    assert r.ok, r.reason
    m = r.message
    assert (m.field, m.kind, m.rows_matching) == ("invoice_lines.quantity", "meaning_wrong", 90)
    assert m.query.splitlines() == ["select * from gold.mart_invoice_lines_typed", "where not is_cancellation and quantity < 0"]
    assert m.contracts == {"gold_invoice_lines_mapping": "1.1.1", "silver_invoice_lines": "1.3.0"}
    assert quoted_spans(m.claim) == ["Units on the line; negative only on cancellations."]
    assert r.extra_parts == []


def test_the_block_is_extracted_from_chat_text_and_fence_lines_are_dropped():
    text = "Here it is:\n\n```\n" + GOOD + "\n```\n\nAnything else?"
    assert extract_block(text) == "\n".join(GOOD.splitlines()[1:-1])
    assert extract_block("no block here") is None
    assert extract_block("FEEDBACK\nfield: a.b\n") is None  # no closing fence


def test_extra_labeled_parts_are_reported_and_ignored():
    block = GOOD.replace("END FEEDBACK", "served file: sha256 abc\nquery literals: none\nEND FEEDBACK")
    r = parse_block(extract_block(block))
    assert r.ok and r.extra_parts == ["served file", "query literals"]


def test_a_missing_part_does_not_parse():
    block = "\n".join(ln for ln in GOOD.splitlines() if not ln.startswith("kind:"))
    r = parse_block(extract_block(block))
    assert not r.ok and "missing part(s): kind" in r.reason


def test_parts_out_of_order_do_not_parse():
    lines = GOOD.splitlines()
    lines[1], lines[2] = lines[2], lines[1]
    r = parse_block(extract_block("\n".join(lines)))
    assert not r.ok and "out of order" in r.reason


def test_a_kind_outside_the_six_and_a_bad_field_and_a_bad_count_line_do_not_parse():
    assert "outside the six" in parse_block(extract_block(GOOD.replace("meaning_wrong", "please_fix"))).reason
    assert "not <category>.<column>" in parse_block(extract_block(GOOD.replace("invoice_lines.quantity", "quantity"))).reason
    assert "rows matching is not" in parse_block(extract_block(GOOD.replace("90 at", "ninety at"))).reason
    assert "contract item is not" in parse_block(extract_block(GOOD.replace("silver_invoice_lines 1.3.0", "silver_invoice_lines"))).reason


def test_split_field_takes_the_lowercase_dotted_shape_only():
    assert split_field("flights.arr_delay_minutes") == ("flights", "arr_delay_minutes")
    for bad in ("Flights.x", "flights", "flights.a.b", "flights.Arr", "a-b.c"):
        try:
            split_field(bad)
        except ValueError as exc:
            assert "not <category>.<column>" in str(exc)
        else:  # pragma: no cover
            raise AssertionError(bad)
