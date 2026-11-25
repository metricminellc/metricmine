"""verify: the producer's re-measurement of a feedback message. A
command, never an agent (HW-39a; the governed host plan, Sections 2.3
and 6).

Reads one message (the five parts, strictly; anything else is reported
and ignored), re-runs its query through the serving module's own
statement and scope gates on the producer's build, recounts the rows,
and reports one of four outcomes:

    reproduces at the same contract versions
    reproduces, and the contract has moved since
    does not reproduce
    does not parse

plus the build's registry digest and, for a meaning kind, whether each
sentence the claim quotes is still the served meaning. The free text is
never interpreted. Against a key (E1T), a message VERIFIES when the
five parts parse, the field and the kind match the key, the recounted
rows equal the stated rows matching, and the contract versions match;
whether the count equals the key's count is reported, never required.

Every printed line is a measurement. The exit status is 0 whenever the
command ran; the printed OUTCOME and VERIFIES lines are what a reader
checks. No model, no network, no write.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from metricmine.query import SCOPE_GOLD, GoldWarehouse, QueryRefused, gate, scope_gate

from .layout import MEANING_KINDS, extract_block, fold, parse_block, quoted_spans
from .prepare import aggregate_reasons, contracts_from_entries, registry_digest, volatile_calls

OUTCOME_SAME = "reproduces at the same contract versions"
OUTCOME_MOVED = "reproduces, and the contract has moved since"
OUTCOME_NO = "does not reproduce"
OUTCOME_PARSE = "does not parse"


def served_entries(wh: GoldWarehouse, category: str) -> dict:
    cats = {c["category"]: c for c in wh.list_fact_categories()["categories"]}
    if category not in cats:
        return {}
    return {role: wh.get_context(key) for role, key in cats[category]["context_keys"].items()}


def build_contracts(entries: dict) -> dict[str, str]:
    """contract name -> version on the build, from the category's entries
    (the same function prepare stamps with, so the two never disagree)."""
    return contracts_from_entries(entries)


def served_meaning(entries: dict, column: str) -> str | None:
    for ctx in entries.values():
        fields = ((ctx.get("compiled_context") or {}).get("expert_context") or {}).get("fields") or {}
        if column in fields and fields[column].get("meaning"):
            return str(fields[column]["meaning"])
    return None


def served_texts(entries: dict, column: str) -> list[str]:
    """The served sentences a meaning claim may quote: the field's meaning
    and source_meaning, and the entry's authored texts (how_to_read,
    limitations, subject, purpose, usage, vintage, lineage, decisions)."""
    texts: list[str] = []
    for ctx in entries.values():
        expert = ((ctx.get("compiled_context") or {}).get("expert_context") or {})
        field = (expert.get("fields") or {}).get(column) or {}
        for key in ("meaning", "source_meaning"):
            if field.get(key):
                texts.append(str(field[key]))
        for key in ("how_to_read", "limitations", "subject", "category_purpose", "category_usage", "category_limitations", "vintage", "lineage"):
            if expert.get(key):
                texts.append(str(expert[key]))
        decisions = expert.get("decisions") or {}
        if isinstance(decisions, dict):
            texts.extend(str(v) for v in decisions.values())
    return texts


def verify(build: Path, text: str, key_field: str | None = None, key_kind: str | None = None, key_count: int | None = None) -> dict:
    # The build is recorded by its file name and, below, its registry digest,
    # never by its path: a report is committed evidence and names no machine.
    report: dict = {"build": Path(build).name, "key_field": key_field, "key_kind": key_kind, "key_count": key_count}
    block = extract_block(text)
    if block is None:
        report.update(parse_ok=False, reason="no FEEDBACK block (the extraction rule found no fence pair)", outcome=OUTCOME_PARSE, verifies=False)
        return report
    parsed = parse_block(block)
    report["extra_parts"] = parsed.extra_parts
    if not parsed.ok:
        report.update(parse_ok=False, reason=parsed.reason, outcome=OUTCOME_PARSE, verifies=False)
        return report
    m = parsed.message
    assert m is not None
    report.update(
        parse_ok=True,
        field=m.field,
        kind=m.kind,
        claim_chars=len(m.claim),
        query=m.query,
        rows_matching_stated=m.rows_matching,
        contracts_stated=m.contracts,
    )
    category, _, column = m.field.partition(".")
    reasons: list[str] = []
    unknown: list[str] = []
    moved: dict = {}
    with GoldWarehouse(path=build, scope=SCOPE_GOLD) as wh:
        con = wh._con  # the hardened session the gates run on
        rows, digest = registry_digest(con)
        report["registry"] = {"rows": rows, "digest": digest}
        report["query_refused"] = None
        try:
            gate(m.query)
            scope_gate(con, m.query, SCOPE_GOLD)
        except QueryRefused as exc:
            report["query_refused"] = str(exc)
        volatile: list[str] = []
        if report["query_refused"] is None:
            try:
                reasons = aggregate_reasons(con, m.query)
                volatile = volatile_calls(con, m.query)
            except Exception as exc:  # a FeedbackRefused on an unparsable query
                report["query_refused"] = str(exc)
        report["aggregate_reasons"] = reasons
        report["volatile_calls"] = volatile
        if report["query_refused"] is None:
            try:
                recount = wh.query(f"select count(*) from (\n{m.query.rstrip().rstrip(';')}\n) as mm_rows", 1)["rows"][0][0]
                report["rows_matching_recounted"] = int(recount)
            except QueryRefused as exc:
                report["rows_matching_recounted"] = None
                report["query_refused"] = str(exc)
            except duckdb.Error as exc:
                report["rows_matching_recounted"] = None
                report["query_refused"] = f"the query failed to run: {type(exc).__name__}: {exc}"
        else:
            report["rows_matching_recounted"] = None
        entries = served_entries(wh, category)
        versions = build_contracts(entries)
        report["contracts_on_build"] = versions
        unknown = sorted(n for n in m.contracts if n not in versions)
        moved = {n: {"stated": v, "build": versions[n]} for n, v in m.contracts.items() if n in versions and versions[n] != v}
        report["contracts_unknown"] = unknown
        report["contracts_moved"] = moved
        if m.kind in MEANING_KINDS:
            meaning = served_meaning(entries, column)
            texts = [fold(t) for t in served_texts(entries, column)]
            spans = quoted_spans(m.claim)
            report["served_meaning"] = meaning
            report["quoted_sentences"] = [
                {
                    "quoted": s,
                    "still_served": (meaning is not None and fold(meaning) == s),
                    "found_in_served_context": any(s in t for t in texts),
                }
                for s in spans
            ]
    reproduces = report["rows_matching_recounted"] is not None and report["rows_matching_recounted"] == m.rows_matching and not reasons
    versions_match = not unknown and not moved and bool(m.contracts)
    if not reproduces:
        outcome = OUTCOME_NO
    elif versions_match:
        outcome = OUTCOME_SAME
    else:
        outcome = OUTCOME_MOVED
    report["outcome"] = outcome
    report["field_matches_key"] = None if key_field is None else (m.field == key_field)
    report["kind_matches_key"] = None if key_kind is None else (m.kind == key_kind)
    report["count_equals_key"] = None if key_count is None else (m.rows_matching == key_count)
    key_ok = (report["field_matches_key"] is not False) and (report["kind_matches_key"] is not False)
    report["verifies"] = bool(reproduces and versions_match and key_ok)
    return report


def print_report(r: dict) -> None:
    print(f"build: {r['build']}")
    if not r.get("parse_ok"):
        print(f"PARSE: fail ({r['reason']})")
        if r.get("extra_parts"):
            print(f"extra parts reported and ignored: {r['extra_parts']}")
        print(f"OUTCOME: {r['outcome']}")
        print("VERIFIES: no (the five parts did not parse)")
        return
    print(f"PARSE: ok; field {r['field']}; kind {r['kind']}; claim {r['claim_chars']} characters")
    if r["extra_parts"]:
        print(f"extra parts reported and ignored: {r['extra_parts']}")
    if r["aggregate_reasons"]:
        print(f"query is not the rows in question: {'; '.join(r['aggregate_reasons'])}")
    if r["query_refused"]:
        print(f"query refused or failed: {r['query_refused']}")
    print(f"rows matching: stated {r['rows_matching_stated']}, recounted {r['rows_matching_recounted']}")
    print(f"contracts stated: {r['contracts_stated']}")
    print(f"contracts on the build: {r['contracts_on_build']}")
    if r["contracts_unknown"]:
        print(f"contracts unknown on the build: {r['contracts_unknown']}")
    if r["contracts_moved"]:
        print(f"contracts moved: {r['contracts_moved']}")
    print(f"registry digest on the build: rows {r['registry']['rows']}, md5 {r['registry']['digest']}")
    if "quoted_sentences" in r:
        if not r["quoted_sentences"]:
            print("quoted sentence: none in the claim")
        for q in r["quoted_sentences"]:
            print(
                f"quoted sentence still the served meaning: {'yes' if q['still_served'] else 'no'}; "
                f"found in the served context: {'yes' if q['found_in_served_context'] else 'no'} ({q['quoted'][:80]!r})"
            )
    if r.get("volatile_calls"):
        print(f"query calls a function whose result changes between runs (a non-reproduction is the caller's): {', '.join(r['volatile_calls'])}")
    print(f"OUTCOME: {r['outcome']}")
    key_bits = ""
    if r["key_field"] is not None or r["key_kind"] is not None:
        key_bits = f" field matches key: {r['field_matches_key']}; kind matches key: {r['kind_matches_key']};"
    print(
        f"VERIFIES: {'yes' if r['verifies'] else 'no'} ({key_bits.strip()}"
        f"{' ' if key_bits else ''}reproduces: {r['outcome'] != OUTCOME_NO}; versions match: {not r['contracts_moved'] and not r['contracts_unknown']})"
    )
    if r["key_count"] is not None:
        print(f"count equals the key's {r['key_count']}: {'yes' if r['count_equals_key'] else 'no'} (reported, never required)")


def report_json(r: dict) -> str:
    return json.dumps(r, indent=1, sort_keys=True) + "\n"
