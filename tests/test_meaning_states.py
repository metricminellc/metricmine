"""The derived meaning states (D-35 as amended by Amendment AC; D-44):
every planted case of the Prep H probe (the transcript's 5b) as a test,
derived from the fixture by code, never stored, and never queued.

Keyless, no network. Every date is fixed.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from metricmine.meaning.register import GLOSSARY, ONTOLOGY, load_register
from metricmine.meaning.states import FLAGS, STATES, counts, derive, meaning_section, plan_rows
from meaning_fixtures import (
    CONCEPTS,
    DAY,
    GLOSSARY_BINDINGS,
    ONTOLOGY_BINDINGS,
    TERMS,
    glossary_binding,
    ontology_binding,
    term_row,
    write_registers,
    write_repo,
)

TODAY = DAY


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return write_repo(tmp_path)


def _states(repo: Path, spec) -> list[tuple[str, str, str]]:
    return [(r.row_id, r.element, r.state) for r in derive(repo, load_register(repo, spec), TODAY)]


def _edit(terms: list[dict], term_id: str, **changes) -> list[dict]:
    return [dict(t, **changes) if t["term_id"] == term_id else t for t in terms]


def _edit_concepts(concepts: list[dict], concept_id: str, **changes) -> list[dict]:
    return [dict(c, **changes) if c["concept_id"] == concept_id else c for c in concepts]


# ---------------------------------------------------------------- as certified


def test_every_binding_is_in_sync_as_certified(repo: Path) -> None:
    assert [s for _, _, s in _states(repo, GLOSSARY)] == ["in_sync"] * 7
    assert [s for _, _, s in _states(repo, ONTOLOGY)] == ["in_sync"] * 4
    assert [e for _, e, _ in _states(repo, GLOSSARY)] == [
        "silver_flights.dep_delay_minutes", "silver_flights.arr_delay_minutes", "silver_flights.carrier_code",
        "silver_flights.tail_number", "silver_flights (table)", "silver_nyc_flights.dep_delay_minutes",
        "silver_ourairports_airports.airport_ident",
    ]
    for report in derive(repo, load_register(repo, GLOSSARY), TODAY):
        assert report.next_command == "none" and report.flags == [] and report.label


# ---------------------------------------------------------------- the glossary cases (A to I2)


def test_case_a_a_one_word_edit_reads_term_changed_on_both_bindings(repo: Path) -> None:
    edited = TERMS[0]["definition"].replace("scheduled departure", "published departure")
    write_registers(repo, terms=_edit(TERMS, "departure_delay", definition=edited))
    states = _states(repo, GLOSSARY)
    assert [(i, e, s) for i, e, s in states if i == "departure_delay"] == [
        ("departure_delay", "silver_flights.dep_delay_minutes", "term_changed"),
        ("departure_delay", "silver_nyc_flights.dep_delay_minutes", "term_changed"),
    ]
    assert [s for i, _, s in states if i != "departure_delay"] == ["in_sync"] * 5
    report = derive(repo, load_register(repo, GLOSSARY), TODAY)[0]
    assert "the binding recorded 8ff9e9b055c4" in report.detail
    assert "`bind` for silver_flights.dep_delay_minutes on departure_delay" in report.next_command
    assert "proposer" not in report.next_command


def test_case_b_a_rewrap_and_an_nfkc_form_stay_in_sync(repo: Path) -> None:
    rewrapped = "Minutes  between the actual and\n the scheduled departure of a ﬂight. Negative when the flight left early. Absent when the flight was cancelled."
    write_registers(repo, terms=_edit(TERMS, "departure_delay", definition=rewrapped))
    assert [s for _, _, s in _states(repo, GLOSSARY)] == ["in_sync"] * 7


def test_case_b2_an_added_synonym_stays_in_sync(repo: Path) -> None:
    write_registers(repo, terms=_edit(TERMS, "departure_delay", synonyms="dep delay; dep_delay; departure delay minutes"))
    assert [s for _, _, s in _states(repo, GLOSSARY)] == ["in_sync"] * 7


def test_case_b3_a_renamed_label_reads_term_changed(repo: Path) -> None:
    write_registers(repo, terms=_edit(TERMS, "carrier", term="Operating carrier"))
    assert ("carrier", "silver_flights.carrier_code", "term_changed") in _states(repo, GLOSSARY)


def test_case_c_a_removed_term_reads_term_missing(repo: Path) -> None:
    write_registers(repo, terms=[t for t in TERMS if t["term_id"] != "arrival_delay"])
    states = _states(repo, GLOSSARY)
    assert ("arrival_delay", "silver_flights.arr_delay_minutes", "term_missing") in states
    report = [r for r in derive(repo, load_register(repo, GLOSSARY), TODAY) if r.row_id == "arrival_delay"][0]
    assert report.detail == "the register carries no term arrival_delay"
    assert report.next_command.startswith("amend the binding by pull request: the register carries no term arrival_delay")


def test_case_d_a_deprecated_term_with_a_successor_reads_term_deprecated(repo: Path) -> None:
    successor = term_row(term_id="departure_delay_minutes", term="Departure delay minutes", synonyms=None,
                         definition="The departure delay, in whole minutes, as the unified table carries it.")
    write_registers(repo, terms=_edit(TERMS, "departure_delay", status="deprecated", superseded_by="departure_delay_minutes") + [successor])
    reports = [r for r in derive(repo, load_register(repo, GLOSSARY), TODAY) if r.row_id == "departure_delay"]
    assert [(r.element, r.state, r.detail) for r in reports] == [
        ("silver_flights.dep_delay_minutes", "term_deprecated", "superseded by departure_delay_minutes"),
        ("silver_nyc_flights.dep_delay_minutes", "term_deprecated", "superseded by departure_delay_minutes"),
    ]
    assert reports[0].next_command.startswith("none required; the term is deprecated")
    write_registers(repo, terms=_edit(TERMS, "departure_delay", status="deprecated"))
    reports = [r for r in derive(repo, load_register(repo, GLOSSARY), TODAY) if r.row_id == "departure_delay"]
    assert reports[0].detail == "no successor named"


def test_case_f_a_binding_to_a_missing_column_or_contract_reads_binding_broken(repo: Path) -> None:
    write_registers(repo, glossary_bindings=[
        glossary_binding("carrier", "silver_flights", "carrier", "x"),
        glossary_binding("carrier", "silver_nope", "carrier_code", "x"),
    ])
    reports = derive(repo, load_register(repo, GLOSSARY), TODAY)
    assert [(r.element, r.state, r.detail) for r in reports] == [
        ("silver_flights.carrier", "binding_broken", "contract silver_flights carries no column carrier"),
        ("silver_nope.carrier_code", "binding_broken", "no committed contract silver_nope"),
    ]
    assert reports[0].next_command.startswith("amend the binding by pull request: the contract or column it names is not committed; `unbind` it")


def test_a_table_level_binding_needs_only_the_contract(repo: Path) -> None:
    write_registers(repo, glossary_bindings=[glossary_binding("cancellation", "silver_flights", "", "x"), glossary_binding("cancellation", "silver_nope", "", "x")])
    assert [s for _, _, s in _states(repo, GLOSSARY)] == ["in_sync", "binding_broken"]


def test_case_i2_the_review_overdue_flag_rides_beside_the_state(repo: Path) -> None:
    register = load_register(repo, GLOSSARY)
    reports = derive(repo, register, date(2028, 1, 1))
    assert all(r.flags == ["review_overdue (review_by 2027-10-26)"] for r in reports)
    assert all(r.state == "in_sync" for r in reports)
    assert reports[0].next_command == "re-certify by pull request: move the term's review_by after a read of its definition"
    assert all(r.flags == [] for r in derive(repo, register, TODAY))
    assert all(r.flags == [] for r in derive(repo, register, None))  # no calendar, no flag
    assert counts(reports) == {"in_sync": 7, "review_overdue": 7}


def test_a_missing_row_outranks_a_broken_element_and_a_moved_digest_outranks_a_deprecation(repo: Path) -> None:
    write_registers(
        repo,
        terms=_edit(TERMS, "carrier", status="deprecated", definition="An airline, by its code."),
        glossary_bindings=[glossary_binding("nope", "silver_nope", "x", "x"), glossary_binding("carrier", "silver_flights", "carrier_code", "x")],
    )
    assert [s for _, _, s in _states(repo, GLOSSARY)] == ["term_missing", "term_changed"]


# ---------------------------------------------------------------- the ontology cases (J to O)


def test_case_j_a_parent_moved_re_asks_the_concept_and_not_its_children(repo: Path) -> None:
    concepts = _edit_concepts(CONCEPTS, "delay", parent_id="aircraft")
    write_registers(repo, concepts=concepts, ontology_bindings=ONTOLOGY_BINDINGS + [ontology_binding("delay", "silver_flights", "arr_delay_minutes", "x")])
    states = _states(repo, ONTOLOGY)
    assert ("delay", "silver_flights.arr_delay_minutes", "concept_changed") in states
    assert ("departure_delay", "silver_flights.dep_delay_minutes", "in_sync") in states  # a node digest


def test_case_j2_a_relabeled_concept_reads_concept_changed(repo: Path) -> None:
    write_registers(repo, concepts=_edit_concepts(CONCEPTS, "departure_delay", label="Departure lateness"))
    assert ("departure_delay", "silver_flights.dep_delay_minutes", "concept_changed") in _states(repo, ONTOLOGY)
    report = [r for r in derive(repo, load_register(repo, ONTOLOGY), TODAY) if r.state == "concept_changed"][0]
    assert "`bind_concept` for silver_flights.dep_delay_minutes on departure_delay" in report.next_command


def test_case_k_a_removed_concept_reads_concept_missing(repo: Path) -> None:
    write_registers(repo, concepts=[c for c in CONCEPTS if c["concept_id"] != "flight"])
    assert ("flight", "silver_flights (table)", "concept_missing") in _states(repo, ONTOLOGY)


def test_case_n2_a_bound_concept_deprecated_reads_concept_deprecated_with_its_successor(repo: Path) -> None:
    write_registers(repo, concepts=_edit_concepts(CONCEPTS, "flight", status="deprecated"))
    reports = [r for r in derive(repo, load_register(repo, ONTOLOGY), TODAY) if r.row_id == "flight"]
    assert [(r.state, r.detail) for r in reports] == [("concept_deprecated", "no successor named")]
    write_registers(repo, concepts=_edit_concepts(CONCEPTS, "flight", status="deprecated", superseded_by="aircraft"))
    reports = [r for r in derive(repo, load_register(repo, ONTOLOGY), TODAY) if r.row_id == "flight"]
    assert [(r.state, r.detail) for r in reports] == [("concept_deprecated", "superseded by aircraft")]
    # Case N: a deprecated concept nobody binds changes no state.
    write_registers(repo, concepts=_edit_concepts(CONCEPTS, "aircraft", status="deprecated"))
    assert [s for _, _, s in _states(repo, ONTOLOGY)] == ["in_sync"] * 4


def test_case_o_an_ontology_binding_to_a_missing_contract_reads_binding_broken(repo: Path) -> None:
    write_registers(repo, ontology_bindings=[ontology_binding("flight", "silver_nope", "", "x")])
    assert _states(repo, ONTOLOGY) == [("flight", "silver_nope (table)", "binding_broken")]


# ---------------------------------------------------------------- the vocabulary, the counts, the section


def test_the_vocabulary_is_fixed() -> None:
    assert STATES == (
        "in_sync", "term_changed", "concept_changed", "term_missing", "concept_missing",
        "term_deprecated", "concept_deprecated", "binding_broken",
    )
    assert FLAGS == ("review_overdue",)
    from metricmine.adoption.scan import ALL_STATES
    from metricmine.documents.states import CONTENT_STATES

    assert set(STATES) & set(ALL_STATES) == {"in_sync"}  # no collision with a scan state but the shared word
    assert set(STATES) & set(CONTENT_STATES) == {"in_sync"}


def test_counts_follow_the_fixed_order_and_drop_zeros(repo: Path) -> None:
    write_registers(
        repo,
        terms=[t for t in TERMS if t["term_id"] != "arrival_delay"],
        glossary_bindings=GLOSSARY_BINDINGS + [glossary_binding("carrier", "silver_nope", "x", "x")],
    )
    reports = derive(repo, load_register(repo, GLOSSARY), date(2028, 1, 1))
    assert list(counts(reports)) == ["in_sync", "term_missing", "binding_broken", "review_overdue"]
    assert counts(reports) == {"in_sync": 6, "term_missing": 1, "binding_broken": 1, "review_overdue": 7}


def test_plan_rows_are_json_shaped(repo: Path) -> None:
    rows = plan_rows(derive(repo, load_register(repo, ONTOLOGY), TODAY))
    assert rows[0] == {
        "register": "ontology", "id": "flight", "label": "Flight", "contract_id": "silver_flights", "column_name": "",
        "state": "in_sync", "detail": "digest unchanged; the element is in a committed contract", "flags": [], "next_command": "none",
    }


def test_meaning_section_reports_and_never_raises(repo: Path, tmp_path: Path) -> None:
    section = meaning_section(repo, TODAY)
    assert section["registers"]["glossary"] == {"register": "conforms", "detail": "glossary_register@1.0.0: 6 term(s), 7 binding(s)"}
    assert section["registers"]["ontology"] == {"register": "conforms", "detail": "ontology_register@1.0.0: 7 concept(s), 4 binding(s)"}
    assert section["counts"] == {"in_sync": 11} and len(section["items"]) == 11
    # One register nonconforming: the other still derives.
    write_registers(repo, terms=[term_row(declared_by="claude-opus-5")] + TERMS[1:])
    section = meaning_section(repo, TODAY)
    assert section["registers"]["glossary"]["register"] == "nonconforming" and "is not a person" in section["registers"]["glossary"]["detail"]
    assert section["registers"]["ontology"]["register"] == "conforms" and section["counts"] == {"in_sync": 4}
    # A failing error rule is nonconforming too, and the items still derive
    # (an orphaned binding reads term_missing beside the rule that names it).
    write_registers(repo, terms=[t for t in TERMS if t["term_id"] != "arrival_delay"])
    section = meaning_section(repo, TODAY)
    assert section["registers"]["glossary"]["register"] == "nonconforming"
    assert section["registers"]["glossary"]["detail"].endswith("; rule failed: Every binding names a term the register carries. (1 rows, expected 0)")
    assert section["counts"] == {"in_sync": 10, "term_missing": 1}
    # A data contract that does not parse: both registers nonconforming, nothing raised.
    write_registers(repo)
    (repo / "contracts" / "silver_flights.odcs.yaml").write_text("schema: [unclosed\n", encoding="utf-8")
    section = meaning_section(repo, TODAY)
    assert section["registers"]["glossary"]["register"] == "nonconforming" and "not valid YAML" in section["registers"]["glossary"]["detail"]
    assert section["registers"]["ontology"]["register"] == "nonconforming" and section["items"] == []
    # No contracts at all: both absent, nothing derived, nothing raised.
    bare = tmp_path / "bare"
    bare.mkdir()
    section = meaning_section(bare, TODAY)
    assert section["registers"]["glossary"] == {"register": "absent", "detail": "no contracts/glossary_register.odcs.yaml in this tree"}
    assert section["registers"]["ontology"]["register"] == "absent" and section["items"] == [] and section["counts"] == {}
