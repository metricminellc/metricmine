"""The producer commands (D-44): `find` with its derived carried-by list,
`show`, `verify` with the four exit causes Amendment AC names, and the
CLI through the path a person or a coding host takes. Keyless, no
network, no MCP tool; every date is fixed.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path, PurePosixPath

import pytest

from metricmine.meaning import __main__ as cli
from metricmine.meaning import commands
from metricmine.meaning.commands import CommandError, find, show, verify
from metricmine.meaning.register import load_all
from meaning_fixtures import (
    BY,
    CONCEPTS,
    DAY,
    GLOSSARY_BINDINGS,
    REPO,
    TERMS,
    glossary_binding,
    ontology_binding,
    write_change_set,
    write_registers,
    write_repo,
)

TODAY = DAY


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return write_repo(tmp_path)


# ---------------------------------------------------------------- find and show


def test_find_lists_terms_and_concepts_by_text_with_a_derived_carried_by_list(repo: Path) -> None:
    hits = find(load_all(repo), "delay")
    assert [(h.register, h.row_id) for h in hits] == [
        ("glossary", "departure_delay"), ("glossary", "arrival_delay"), ("glossary", "cancellation"),
        ("ontology", "delay"), ("ontology", "departure_delay"), ("ontology", "arrival_delay"),
    ]
    assert hits[0].carried_by == ("silver_flights.dep_delay_minutes", "silver_nyc_flights.dep_delay_minutes")
    assert hits[3].carried_by == ()  # derived from the bindings, never authored
    assert "(synonyms: dep delay; dep_delay)" in hits[0].text and "(parent: delay)" in hits[4].text
    text = commands.render_find(hits, "delay")
    assert text.startswith("find 'delay': 6 hit(s) across the glossary and the ontology\n")
    assert "  glossary | departure_delay | Departure delay | active | carried by silver_flights.dep_delay_minutes, silver_nyc_flights.dep_delay_minutes\n" in text
    assert "carried by nothing (no binding)" in text
    assert len(find(load_all(repo), "")) == 13  # every row
    assert [h.row_id for h in find(load_all(repo), "TAILNUM")] == ["tail_number"]  # a synonym, case-insensitive


def test_show_prints_one_row_with_its_bindings_and_states_and_reads_no_calendar(repo: Path) -> None:
    text = show(repo, load_all(repo), "departure_delay")
    assert text.startswith("glossary term: departure_delay\n  term_id: departure_delay\n  term: Departure delay\n")
    assert "  bindings: 2\n    silver_flights.dep_delay_minutes | in_sync | digest unchanged" in text
    assert "ontology concept: departure_delay\n" in text  # the id exists in both registers; both print
    assert "  digest: 8ff9e9b055c486cd" in text
    assert "review_overdue" not in show(repo, load_all(repo), "carrier")
    with pytest.raises(CommandError, match="no term or concept with id 'nope' in either register"):
        show(repo, load_all(repo), "nope")


# ---------------------------------------------------------------- verify


def test_verify_is_ok_on_the_fixture_and_reports_every_rule_and_binding(repo: Path) -> None:
    v = verify(repo, TODAY)
    assert v.exit_code == 0 and v.failures == []
    assert len(v.rules["glossary"]) == 10 and len(v.rules["ontology"]) == 11 and len(v.reports) == 11
    text = commands.render_verify(v, TODAY)
    assert text.startswith("meaning verify (today 2026-10-26)\n  glossary: conforms to glossary_register@1.0.0 (6 term(s), 7 binding(s))\n  rules: 10\n")
    assert "  ontology: conforms to ontology_register@1.0.0 (7 concept(s), 4 binding(s))\n  rules: 11\n" in text
    assert text.endswith("  result: OK\n")
    assert text.count("    pass [") == 21


def test_verify_exits_one_on_a_nonconforming_register(repo: Path) -> None:
    write_registers(repo, terms=[dict(TERMS[0], declared_by="gold-mapping-proposer")] + TERMS[1:])
    v = verify(repo, TODAY)
    assert v.exit_code == 1 and v.failures == ["register does not conform: terms.yaml departure_delay: declared_by 'gold-mapping-proposer' is not a person"]
    assert commands.render_verify(v, TODAY) == (
        "meaning verify (today 2026-10-26)\n  FAIL register does not conform: terms.yaml departure_delay: declared_by 'gold-mapping-proposer' is not a person\n"
    )
    (repo / "contracts" / "glossary_register.odcs.yaml").unlink()
    assert verify(repo, TODAY).failures == ["register does not conform: no register contract at contracts/glossary_register.odcs.yaml"]


def test_verify_exits_one_on_a_failing_error_rule(repo: Path) -> None:
    write_registers(repo, concepts=[dict(c, parent_id="delay") if c["concept_id"] == "flight" else c for c in CONCEPTS])
    v = verify(repo, TODAY)
    assert v.exit_code == 1
    assert v.failures[0] == "ontology: rule failed: The parent graph has no cycle. (2 rows, expected 0)"
    assert v.failures[1].startswith("ontology: flight on silver_flights (table): concept_changed")  # the parent move moved the digest
    assert "    FAIL [error] ontology_concepts: The parent graph has no cycle. (2 rows, expected 0)" in commands.render_verify(v, TODAY)


def test_verify_exits_one_on_a_changed_or_missing_row_under_a_standing_binding(repo: Path) -> None:
    write_registers(repo, terms=[dict(TERMS[0], definition="Edited by hand.")] + TERMS[2:])
    v = verify(repo, TODAY)
    assert v.exit_code == 1
    assert v.failures[0] == "glossary: rule failed: Every binding names a term the register carries. (1 rows, expected 0)"
    assert [f.split(":")[2].strip() for f in v.failures[1:]] == ["term_changed", "term_missing", "term_changed"]
    assert v.failures[2].startswith("glossary: arrival_delay on silver_flights.arr_delay_minutes: term_missing")


def test_verify_exits_one_on_a_broken_binding(repo: Path) -> None:
    write_registers(repo, ontology_bindings=[ontology_binding("flight", "silver_nope", "", "x")])
    v = verify(repo, TODAY)
    assert v.exit_code == 1 and v.failures == ["ontology: flight on silver_nope (table): binding_broken: no committed contract silver_nope"]


def test_verify_reports_a_deprecation_and_an_overdue_review_without_blocking(repo: Path) -> None:
    write_registers(repo, terms=[dict(TERMS[0], status="deprecated", superseded_by="carrier")] + TERMS[1:])
    v = verify(repo, date(2028, 1, 1))
    assert v.exit_code == 0 and v.failures == []
    text = commands.render_verify(v, date(2028, 1, 1))
    assert "    WARN [warn] glossary_terms: No term is past its review date. (6 rows, expected 0)" in text
    assert "    WARN [warn] ontology_concepts: No concept is past its review date. (7 rows, expected 0)" in text
    assert "    glossary | departure_delay | silver_flights.dep_delay_minutes | term_deprecated | flags: review_overdue (review_by 2027-10-26)" in text
    assert text.endswith("  result: OK\n")


# ---------------------------------------------------------------- the CLI


def test_cli_verify_find_and_show(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--repo", str(repo), "verify", "--today", "2026-10-26"]) == 0
    assert capsys.readouterr().out.endswith("  result: OK\n")
    assert cli.main(["--repo", str(repo), "find", "carrier"]) == 0
    assert "carried by silver_flights.carrier_code" in capsys.readouterr().out
    assert cli.main(["--repo", str(repo), "show", "weather_observation"]) == 0
    assert capsys.readouterr().out.startswith("ontology concept: weather_observation\n")
    assert cli.main(["--repo", str(repo), "show", "nope"]) == 2
    assert capsys.readouterr().err == "refused: no term or concept with id 'nope' in either register\n"


def test_cli_verify_exits_one_and_two(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_registers(repo, glossary_bindings=GLOSSARY_BINDINGS + [glossary_binding("carrier", "silver_nope", "x", "x")])
    assert cli.main(["--repo", str(repo), "verify", "--today", "2026-10-26"]) == 1
    assert "binding_broken" in capsys.readouterr().out
    (repo / "meaning" / "glossary" / "terms.yaml").write_text("terms: [\n", encoding="utf-8")
    assert cli.main(["--repo", str(repo), "find", "x"]) == 2
    assert capsys.readouterr().err.startswith("refused: terms.yaml: not valid YAML")


def test_cli_propose_prints_the_summary_and_the_wrote_line(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = write_change_set(repo, "cli", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "operator", "rationale": "r"}])
    assert cli.main(["--repo", str(repo), "propose", str(path), "--today", "2026-10-26"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# Governed meaning: a change set, rendered (D-44)\n")
    assert out.endswith("wrote proposals/meaning/cli/ (glossary/, ontology/, record.json, summary.md); meaning/ and contracts/ are unchanged\n")
    record = json.loads((repo / "proposals" / "meaning" / "cli" / "record.json").read_text(encoding="utf-8"))
    assert record["day"] == "2026-10-26" and record["by"] == BY
    assert cli.main(["--repo", str(repo), "propose", str(path), "--today", "2026-10-26", "--outbox", str(repo / "meaning" / "glossary")]) == 2
    assert "is outside proposals/meaning/" in capsys.readouterr().err
    bad = write_change_set(repo, "bad", [{"kind": "drop_term", "term_id": "carrier", "rationale": "r"}])
    assert cli.main(["--repo", str(repo), "propose", str(bad), "--today", "2026-10-26"]) == 2
    assert capsys.readouterr().err == "refused: change 1 (drop_term): carrier is not deprecated; deprecate it first (HW-35, deprecate then drop)\n"
    assert not (repo / "proposals" / "meaning" / "bad").exists()


def test_cli_a_bad_today_is_a_usage_error_and_the_default_is_the_utc_day(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--repo", str(repo), "verify", "--today", "yesterday"])
    assert exc.value.code == 2
    assert "not a date (YYYY-MM-DD): 'yesterday'" in capsys.readouterr().err
    assert cli._today(date(2026, 1, 1)) == date(2026, 1, 1)
    measured = cli._today(None)
    from datetime import datetime, timezone

    assert abs((measured - datetime.now(timezone.utc).date()).days) <= 1


def test_the_makefile_targets_are_one_uv_run_line_each() -> None:
    text = (REPO / "Makefile").read_text(encoding="utf-8")
    for target, line in (
        ("meaning-find", 'uv run python -m metricmine.meaning find "$(QUERY)"'),
        ("meaning-show", 'uv run python -m metricmine.meaning show "$(ID)"'),
        ("meaning-propose", 'uv run python -m metricmine.meaning propose "$(CHANGES)"'),
        ("meaning-verify", "uv run python -m metricmine.meaning verify"),
    ):
        block = text.split(f"\n{target}:\n", 1)[1].split("\n\n", 1)[0]
        assert block.strip("\n").splitlines() == [f"\t{line}"], (target, block)
    assert "mm meaning" not in text  # the mm entry point is not widened (D-42)


def test_the_outbox_and_the_registers_are_posix_paths_in_the_summary(repo: Path) -> None:
    path = write_change_set(repo, "posix", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "operator", "rationale": "r"}])
    _, _, out = commands.propose(repo, load_all(repo), path, TODAY)
    summary = (out / "summary.md").read_text(encoding="utf-8")
    expected = PurePosixPath("proposals") / "meaning" / "posix"
    assert f"    cp {expected.as_posix()}/glossary/*.yaml meaning/glossary/" in summary
