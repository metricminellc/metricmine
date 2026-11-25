"""prepare: the governed message rendered by code (E1T). Every case runs
on the tiny synthetic gold warehouse of tests/feedback_fixtures.py, so
the lane is keyless and needs no built star. The refusal matrix is the
host plan's stage 2 list plus the seven P-K defects, each with its remedy
named; the stamp is computed, never read from a manifest, and changes
when the served content changes; nothing is written.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

from metricmine.feedback import FENCE_CLOSE, FENCE_OPEN, KINDS, FeedbackRefused, extract_block, parse_block, prepare, render
from metricmine.feedback.prepare import CLAIM_CAP, COUNT_CAP, canonical_sql, query_literals, volatile_calls
from metricmine.query import GoldWarehouse

from feedback_fixtures import build_gold

ROWS = "select * from gold.mart_invoice_lines_typed where not is_cancellation and quantity < 0"
CLAIM = "A flag that marks stock-adjustment lines is wanted."


@pytest.fixture
def gold(tmp_path: Path) -> Path:
    return build_gold(tmp_path / "star.duckdb")


def _prepare(path: Path, **kw):
    args = dict(field="invoice_lines.quantity", kind="rule_wanted", claim=CLAIM, query=ROWS)
    args.update(kw)
    with GoldWarehouse(path=path, scope="gold") as wh:
        return prepare(wh, args["field"], args["kind"], args["claim"], args["query"], "0.0.0-test")


def _refusal(path: Path, **kw) -> FeedbackRefused:
    with pytest.raises(FeedbackRefused) as info:
        _prepare(path, **kw)
    assert info.value.remedy, "every refusal names its remedy"
    return info.value


def test_an_accepted_call_renders_the_five_parts_then_the_stamp(gold):
    p = _prepare(gold)
    text = render(p)
    lines = text.splitlines()
    assert lines[0] == FENCE_OPEN and lines[-1] == FENCE_CLOSE
    assert lines[1:6] == [
        "field: invoice_lines.quantity",
        "kind: rule_wanted",
        f"claim: {CLAIM}",
        "query: SELECT * FROM gold.mart_invoice_lines_typed WHERE ((NOT is_cancellation) AND (quantity < 0))",
        "rows matching: 90 at gold_invoice_lines_mapping 1.1.2, silver_invoice_lines 1.3.0, gold_unified_event_star 1.6.0",
    ]
    assert lines[6].startswith("served file: sha256 ") and "registry 2 rows md5 " in lines[6] and lines[6].endswith("server 0.0.0-test")
    assert lines[7] == "query literals: 0"
    assert lines[8].startswith("caller supplied: claim and query")
    r = parse_block(extract_block(text))
    assert r.ok and r.message.rows_matching == 90 and r.extra_parts == ["served file", "query literals", "caller supplied"]


def test_comments_are_stripped_and_the_query_is_one_line(gold):
    p = _prepare(gold, query="select *\nfrom gold.mart_invoice_lines_typed -- trailing\nwhere quantity < 0 /* block */")
    assert "\n" not in p.query and "--" not in p.query and "/*" not in p.query
    assert p.rows_matching == 100


def test_literals_are_listed_by_code_and_a_comment_value_is_not_among_them(gold):
    with GoldWarehouse(path=gold, scope="gold") as wh:
        con = wh._con
        sql = "select * from gold.mart_invoice_lines_typed where stock_code = 'sc' and quantity < -0 -- secret 42"
        assert query_literals(con, sql) == ["'sc'", "0"]
        assert "42" not in canonical_sql(con, sql)


def test_literals_keep_their_scale_quotes_and_casts(gold):
    with GoldWarehouse(path=gold, scope="gold") as wh:
        con = wh._con
        sql = (
            "select * from gold.mart_invoice_lines_typed where unit_price = 2.5 or unit_price = 100.00 or stock_code = 'o''brien'"
            " or is_cancellation = true or invoice_id is null or quantity = -7 or stock_code = date '2013-01-01'::varchar"
        )
        lits = query_literals(con, sql)
        assert lits[:5] == ["2.5", "100.00", "'o''brien'", "CAST('t' AS BOOLEAN)", "-7"]
        assert "CAST('2013-01-01' AS DATE)" in lits[5]
        assert volatile_calls(con, "select * from gold.mart_invoice_lines_typed where quantity < random()") == ["random"]
        assert volatile_calls(con, "select * from gold.mart_invoice_lines_typed") == []


def test_the_refusal_matrix(gold):
    assert "statement type DELETE" in _refusal(gold, query="delete from gold.mart_invoice_lines_typed").reason
    assert "2 statements" in _refusal(gold, query="select 1; select 2").reason
    assert "outside the six" in _refusal(gold, kind="please_fix").reason
    assert "claim is empty" in _refusal(gold, claim="  \n ").reason
    assert "@ sign" in _refusal(gold, claim="ping @claude").reason
    assert f"over {CLAIM_CAP}" in _refusal(gold, claim="x " * (CLAIM_CAP // 2 + 50)).reason
    assert _prepare(gold, claim="y" * CLAIM_CAP).claim == "y" * CLAIM_CAP  # at most 2,000 passes
    assert "not a typed column" in _refusal(gold, field="invoice_lines.nope").reason
    assert "no served category" in _refusal(gold, field="nope.quantity").reason
    assert "not <category>.<column>" in _refusal(gold, field="Invoice Lines.quantity").reason
    assert "names a column that exists" in _refusal(gold, kind="missing_field").reason
    assert "aggregate call(s)" in _refusal(gold, query="select count(*) from gold.mart_invoice_lines_typed").reason
    assert "GROUP BY" in _refusal(gold, query="select quantity from gold.mart_invoice_lines_typed group by 1").reason
    assert "aggregate call(s)" in _refusal(gold, query="select count(*) from gold.mart_invoice_lines_typed union all select count(*) from gold.mart_invoice_lines_typed").reason
    assert "names none of invoice_lines's tables" in _refusal(gold, query="select 1 as x").reason
    assert "names none of invoice_lines's tables" in _refusal(gold, query="select * from gold.context_registry").reason
    for volatile in ("random() < 0.5", "invoiced_at < now()", "invoiced_at < current_date", "uuid() is not null"):
        exc = _refusal(gold, query=f"select * from gold.mart_invoice_lines_typed where {volatile}")
        assert "changes between runs" in exc.reason, volatile
    assert "outside the gold schema" in _refusal(gold, query="select * from silver.silver_invoice_lines").reason
    assert "failed to run" in _refusal(gold, query="select nope from gold.mart_invoice_lines_typed").reason
    assert "parse error" in _refusal(gold, query="select * from").reason


def test_missing_field_names_a_column_that_does_not_exist(gold):
    p = _prepare(gold, field="invoice_lines.stock_adjustment_flag", kind="missing_field", claim="A flag is missing.")
    assert p.field == "invoice_lines.stock_adjustment_flag" and p.rows_matching == 90


def test_a_subquery_aggregate_is_rows_and_a_trailing_comment_is_accepted(gold):
    p = _prepare(gold, query="select * from gold.mart_invoice_lines_typed where quantity < (select min(quantity) + 1 from gold.mart_invoice_lines_typed) -- ok")
    assert p.rows_matching == 10


def test_the_count_is_capped_and_a_query_over_the_cap_is_refused(gold, monkeypatch):
    # The package exports the function `prepare`, so the module is reached by name.
    monkeypatch.setattr(importlib.import_module("metricmine.feedback.prepare"), "COUNT_CAP", 50)
    exc = _refusal(gold, query="select * from gold.mart_invoice_lines_typed")
    assert "more than 50 rows" in exc.reason
    assert COUNT_CAP == 1_000_000


def test_every_kind_but_missing_field_takes_an_existing_column(gold):
    for kind in KINDS:
        if kind == "missing_field":
            continue
        assert _prepare(gold, kind=kind).kind == kind


def test_the_stamp_is_computed_and_changes_with_the_served_content(gold, tmp_path):
    a = _prepare(gold)
    other = build_gold(tmp_path / "other.duckdb", mapping_version="1.1.3", negatives=91)
    b = _prepare(other)
    assert a.served_file_sha256 != b.served_file_sha256
    assert a.registry_md5 != b.registry_md5
    assert (a.rows_matching, b.rows_matching) == (90, 91)
    assert b.contracts["gold_invoice_lines_mapping"] == "1.1.3"
    assert len(a.served_file_sha256) == 64 and a.served_file_bytes == gold.stat().st_size


def test_prepare_writes_nothing(gold, tmp_path):
    before = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in tmp_path.rglob("*") if p.is_file()}
    cwd_before = sorted(os.listdir(os.getcwd()))
    _prepare(gold)
    after = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after
    assert sorted(os.listdir(os.getcwd())) == cwd_before
