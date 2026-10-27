"""The change set and the `propose` command (D-44): one test per kind of
the closed vocabulary, one per refusal the decision lists, the re-bind
under the set's intent (the probe's case A2), the record, the summary,
and the outbox fence. Nothing under `meaning/` or `contracts/` is ever
touched, and the tests prove it by digest.

Keyless, no network. Every date is fixed.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date
from pathlib import Path

import pytest

from metricmine.documents.register import sha256_text
from metricmine.meaning import changes as cs
from metricmine.meaning.changes import ChangeError, VOCABULARY, draft_name, load_change_set, propose, write_proposal
from metricmine.meaning.register import GLOSSARY, ONTOLOGY, load_all, load_register, run_rules
from metricmine.meaning.states import derive
from meaning_fixtures import (
    BY,
    CONCEPTS,
    DAY,
    GLOSSARY_BINDINGS,
    TERMS,
    glossary_binding,
    load_rendered,
    ontology_binding,
    write_change_set,
    write_registers,
    write_repo,
)

TODAY = DAY
INTENT = "the steward's words, verbatim."


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return write_repo(tmp_path)


def _tree_digest(repo: Path) -> dict[str, str]:
    out = {}
    for folder in ("meaning", "contracts"):
        for path in sorted((repo / folder).rglob("*")):
            if path.is_file():
                out[path.relative_to(repo).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _run(repo: Path, name: str, changes: list[dict], by: str = BY, intent: str = INTENT, today: date = TODAY):
    before = _tree_digest(repo)
    path = write_change_set(repo, name, changes, by, intent)
    change_set = load_change_set(repo, path)
    proposal = propose(repo, load_all(repo), change_set, today)
    out = write_proposal(repo, proposal, change_set, today)
    assert _tree_digest(repo) == before  # nothing under meaning/ or contracts/ moved
    return proposal, change_set, out


def _refused(repo: Path, name: str, changes: list[dict], match: str, by: str = BY, intent: str = INTENT) -> None:
    before = _tree_digest(repo)
    path = write_change_set(repo, name, changes, by, intent)
    with pytest.raises(ChangeError, match=match):
        propose(repo, load_all(repo), load_change_set(repo, path), TODAY)
    assert _tree_digest(repo) == before
    assert not (repo / "proposals" / "meaning" / name).exists()


# ---------------------------------------------------------------- the file


def test_the_vocabulary_is_closed_and_classified() -> None:
    assert set(VOCABULARY) == {
        "add_term", "amend_definition", "rename_term", "add_synonym", "remove_synonym", "deprecate_term", "drop_term", "bind", "unbind",
        "add_concept", "amend_concept", "relabel", "deprecate_concept", "drop_concept", "bind_concept", "unbind_concept",
    }
    assert {k for k, (_, c) in VOCABULARY.items() if c == "additive"} == {"add_term", "add_synonym", "remove_synonym", "bind", "add_concept", "bind_concept"}
    assert {k for k, (_, c) in VOCABULARY.items() if c == "changing"} == {"amend_definition", "rename_term", "amend_concept", "relabel"}
    assert {k for k, (_, c) in VOCABULARY.items() if c == "removing"} == {"deprecate_term", "drop_term", "unbind", "deprecate_concept", "drop_concept", "unbind_concept"}
    assert cs.DOCUMENT_KINDS == ("add_document", "bind_document", "unbind_document", "recertify_document", "retire_document")


def test_a_kind_outside_the_vocabulary_is_refused_by_the_schema(repo: Path) -> None:
    path = write_change_set(repo, "x", [{"kind": "bind_term", "rationale": "r"}])
    with pytest.raises(ChangeError, match="does not match the change-set schema at changes/0/kind: 'bind_term' is not one of"):
        load_change_set(repo, path)


@pytest.mark.parametrize("kind", cs.DOCUMENT_KINDS)
def test_a_document_kind_is_refused_by_name_as_a_later_slice(repo: Path, kind: str) -> None:
    path = write_change_set(repo, "x", [{"kind": kind, "rationale": "r"}])
    with pytest.raises(ChangeError, match=f"change 1: `{kind}` is a document change kind; it rides the slice that serves governed meaning"):
        load_change_set(repo, path)


def test_a_missing_field_an_empty_set_and_a_missing_file_are_refused(repo: Path) -> None:
    path = write_change_set(repo, "x", [{"kind": "add_term", "term_id": "x", "rationale": "r"}])
    with pytest.raises(ChangeError, match="changes/0: 'term' is a required property"):
        load_change_set(repo, path)
    path = write_change_set(repo, "y", [])
    with pytest.raises(ChangeError, match="changes: \\[\\] should be non-empty"):
        load_change_set(repo, path)
    with pytest.raises(ChangeError, match="no change-set file at"):
        load_change_set(repo, repo / "proposals" / "meaning" / "nope.changes.yaml")
    (repo / "proposals" / "meaning" / "bad.changes.yaml").write_text("by: [\n", encoding="utf-8")
    with pytest.raises(ChangeError, match="not valid YAML"):
        load_change_set(repo, repo / "proposals" / "meaning" / "bad.changes.yaml")


def test_by_must_be_a_person_and_intent_non_empty(repo: Path) -> None:
    _refused(repo, "a", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "op", "rationale": "r"}],
             "by 'claude-sonnet-5' is not a person", by="claude-sonnet-5")
    _refused(repo, "b", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "op", "rationale": "r"}],
             "intent is empty", intent="   ")


def test_the_draft_is_named_from_the_file() -> None:
    assert draft_name(Path("proposals/meaning/departure-delay-wording.changes.yaml")) == "departure-delay-wording"
    assert draft_name(Path("x/set.yml")) == "set"
    assert draft_name(Path(".changes.yaml")) == "change-set"


# ---------------------------------------------------------------- the glossary kinds


def test_add_term_is_additive_and_renders_a_row_declared_by_the_author(repo: Path) -> None:
    proposal, _, out = _run(repo, "add", [{
        "kind": "add_term", "term_id": "origin_airport", "term": "Origin airport", "synonyms": "origin; from",
        "definition": "The airport a flight departs from, by its identifier.", "owner": "aviation stewards", "rationale": "r",
    }])
    assert [(a.kind, a.klass, a.target) for a in proposal.applied] == [("add_term", "additive", "origin_airport")]
    row = load_rendered(out, "glossary", "terms.yaml", "terms")[-1]
    assert row["term_id"] == "origin_airport" and row["status"] == "active" and row["superseded_by"] is None
    assert row["declared_by"] == BY and row["declared_on"] == TODAY and row["review_by"] == date(2027, 10, 26)
    assert row["synonyms"] == "origin; from"
    assert proposal.rebound == [] and proposal.before["glossary"] != proposal.after["glossary"]
    assert proposal.before["ontology"] == proposal.after["ontology"]


def test_add_term_refuses_a_taken_id_a_bad_id_an_owned_label_or_synonym_and_a_model_owner(repo: Path) -> None:
    base = {"kind": "add_term", "term": "New term", "definition": "d", "owner": "aviation stewards", "rationale": "r"}
    _refused(repo, "a", [dict(base, term_id="carrier")], "term_id 'carrier' is taken")
    _refused(repo, "b", [dict(base, term_id="New-Term")], "does not match the change-set schema at changes/0/term_id")
    _refused(repo, "c", [dict(base, term_id="x", term="Tail number")], "the label 'Tail number' is owned by tail_number")
    _refused(repo, "d", [dict(base, term_id="x", term="Tailnum")], "the label 'Tailnum' is owned by tail_number \\(as a label or a synonym\\)")
    _refused(repo, "e", [dict(base, term_id="x", synonyms="fresh; Carrier")], "the synonym 'Carrier' is owned by carrier")
    _refused(repo, "f", [dict(base, term_id="x", synonyms="new term")], "repeats the label or another synonym of this term")
    _refused(repo, "g", [dict(base, term_id="x", owner="claude-fable-5")], "owner 'claude-fable-5' is not a person or a team")


def test_amend_definition_is_changing_and_re_binds_every_touched_binding_case_a2(repo: Path) -> None:
    new = "Minutes between the actual and the published scheduled departure of a flight. Negative when the flight left early. Absent when the flight was cancelled."
    proposal, _, out = _run(repo, "amend", [{"kind": "amend_definition", "term_id": "departure_delay", "definition": new, "rationale": "r"}])
    assert [(a.kind, a.klass) for a in proposal.applied] == [("amend_definition", "changing")]
    assert [(r["id"], r["element"]) for r in proposal.rebound] == [
        ("departure_delay", "silver_flights.dep_delay_minutes"),
        ("departure_delay", "silver_nyc_flights.dep_delay_minutes"),
    ]
    bindings = load_rendered(out, "glossary", "bindings.yaml", "bindings")
    rebound = [b for b in bindings if b["term_id"] == "departure_delay"]
    terms = load_rendered(out, "glossary", "terms.yaml", "terms")
    from metricmine.meaning.register import term_digest

    assert all(b["term_sha256"] == term_digest(terms[0]) for b in rebound)
    assert all(b["intent"] == INTENT and b["intent_sha256"] == sha256_text(INTENT) and b["bound_by"] == BY and b["bound_on"] == TODAY for b in rebound)
    untouched = [b for b in bindings if b["term_id"] != "departure_delay"]
    assert all(b["intent"] != INTENT for b in untouched)
    # Applied, every state is in_sync and every rule passes.
    write_registers(repo, terms=terms, glossary_bindings=bindings)
    register = load_register(repo, GLOSSARY)
    assert [r.state for r in derive(repo, register, TODAY)] == ["in_sync"] * 7
    assert all(r.passed for r in run_rules(register, TODAY))


def test_amend_definition_refuses_a_missing_term_and_an_unchanged_text(repo: Path) -> None:
    _refused(repo, "a", [{"kind": "amend_definition", "term_id": "nope", "definition": "d", "rationale": "r"}],
             "the glossary register carries no term 'nope', and this set does not add it earlier")
    _refused(repo, "b", [{"kind": "amend_definition", "term_id": "carrier", "definition": "  " + TERMS[2]["definition"] + " ", "rationale": "r"}],
             "the definition of carrier matches the current text; nothing changes")


def test_rename_term_is_changing_and_the_old_label_may_become_a_synonym_in_the_same_set(repo: Path) -> None:
    proposal, _, out = _run(repo, "rename", [
        {"kind": "rename_term", "term_id": "carrier", "term": "Operating carrier", "rationale": "r"},
        {"kind": "add_synonym", "term_id": "carrier", "synonym": "Carrier", "rationale": "the old label"},
    ])
    assert [(a.kind, a.klass) for a in proposal.applied] == [("rename_term", "changing"), ("add_synonym", "additive")]
    assert [r["element"] for r in proposal.rebound] == ["silver_flights.carrier_code"]
    row = [t for t in load_rendered(out, "glossary", "terms.yaml", "terms") if t["term_id"] == "carrier"][0]
    assert row["term"] == "Operating carrier" and row["synonyms"] == "airline code; carrier code; Carrier"


def test_rename_term_refuses_an_owned_label_its_own_synonym_and_no_change(repo: Path) -> None:
    _refused(repo, "a", [{"kind": "rename_term", "term_id": "carrier", "term": "Tail number", "rationale": "r"}], "the label 'Tail number' is owned by tail_number")
    _refused(repo, "b", [{"kind": "rename_term", "term_id": "carrier", "term": "airline code", "rationale": "r"}], "'airline code' is a synonym of carrier; remove the synonym earlier in this set")
    _refused(repo, "c", [{"kind": "rename_term", "term_id": "carrier", "term": " Carrier ", "rationale": "r"}], "already reads 'Carrier'; nothing changes")
    proposal, _, _ = _run(repo, "case", [{"kind": "rename_term", "term_id": "carrier", "term": "CARRIER", "rationale": "a case-only rename moves the digest"}])
    assert [r["element"] for r in proposal.rebound] == ["silver_flights.carrier_code"]


def test_add_synonym_and_remove_synonym_are_additive_and_move_no_binding_case_b2(repo: Path) -> None:
    proposal, _, out = _run(repo, "syn", [
        {"kind": "add_synonym", "term_id": "departure_delay", "synonym": "departure delay minutes", "rationale": "r"},
        {"kind": "remove_synonym", "term_id": "departure_delay", "synonym": "dep delay", "rationale": "r"},
    ])
    assert [a.klass for a in proposal.applied] == ["additive", "additive"] and proposal.rebound == []
    row = load_rendered(out, "glossary", "terms.yaml", "terms")[0]
    assert row["synonyms"] == "dep_delay; departure delay minutes"
    bindings = load_rendered(out, "glossary", "bindings.yaml", "bindings")
    assert all(b["intent"] != INTENT for b in bindings)  # nothing re-bound


def test_add_synonym_refuses_an_owned_name_and_remove_synonym_a_missing_one(repo: Path) -> None:
    _refused(repo, "a", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "tailnum", "rationale": "r"}], "'tailnum' is owned by tail_number")
    _refused(repo, "b", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "Cancellation", "rationale": "r"}], "'Cancellation' is owned by cancellation")
    _refused(repo, "c", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "airline code", "rationale": "r"}], "already a synonym of carrier")
    _refused(repo, "d", [{"kind": "remove_synonym", "term_id": "carrier", "synonym": "nope", "rationale": "r"}], "'nope' is not a synonym of carrier")


def test_deprecate_term_is_removing_step_one_with_a_successor_the_set_adds_case_d(repo: Path) -> None:
    proposal, _, out = _run(repo, "dep", [
        {"kind": "add_term", "term_id": "departure_delay_minutes", "term": "Departure delay minutes", "definition": "The departure delay in whole minutes.", "owner": "aviation stewards", "rationale": "r"},
        {"kind": "deprecate_term", "term_id": "departure_delay", "superseded_by": "departure_delay_minutes", "rationale": "r"},
    ])
    assert [(a.kind, a.klass) for a in proposal.applied] == [("add_term", "additive"), ("deprecate_term", "removing")]
    assert proposal.rebound == []  # a status change moves no digest
    row = load_rendered(out, "glossary", "terms.yaml", "terms")[0]
    assert (row["status"], row["superseded_by"]) == ("deprecated", "departure_delay_minutes")
    write_registers(repo, terms=load_rendered(out, "glossary", "terms.yaml", "terms"))
    assert [r.state for r in derive(repo, load_register(repo, GLOSSARY), TODAY) if r.row_id == "departure_delay"] == ["term_deprecated"] * 2


def test_deprecate_term_refuses_a_missing_successor_itself_and_a_second_deprecation(repo: Path) -> None:
    _refused(repo, "a", [{"kind": "deprecate_term", "term_id": "carrier", "superseded_by": "nope", "rationale": "r"}],
             "\\(superseded_by\\): the glossary register carries no term 'nope'")
    _refused(repo, "b", [{"kind": "deprecate_term", "term_id": "carrier", "superseded_by": "carrier", "rationale": "r"}], "cannot supersede itself")
    write_registers(repo, terms=[dict(t, status="deprecated") if t["term_id"] == "carrier" else t for t in TERMS])
    _refused(repo, "c", [{"kind": "deprecate_term", "term_id": "carrier", "rationale": "r"}], "carrier is already deprecated")


def test_drop_term_is_removing_step_two_after_a_merged_deprecation_and_no_binding(repo: Path) -> None:
    write_registers(repo, terms=[dict(t, status="deprecated") if t["term_id"] == "tail_number" else t for t in TERMS])
    _refused(repo, "a", [{"kind": "drop_term", "term_id": "tail_number", "rationale": "r"}],
             "a binding stands on tail_number \\(silver_flights.tail_number\\); unbind it first")
    proposal, _, out = _run(repo, "drop", [
        {"kind": "unbind", "term_id": "tail_number", "contract_id": "silver_flights", "column_name": "tail_number", "rationale": "r"},
        {"kind": "drop_term", "term_id": "tail_number", "rationale": "r"},
    ])
    assert [(a.kind, a.klass) for a in proposal.applied] == [("unbind", "removing"), ("drop_term", "removing")]
    assert "tail_number" not in [t["term_id"] for t in load_rendered(out, "glossary", "terms.yaml", "terms")]


def test_drop_term_refuses_an_active_term_and_a_deprecation_in_the_same_set(repo: Path) -> None:
    _refused(repo, "a", [{"kind": "drop_term", "term_id": "carrier", "rationale": "r"}], "carrier is not deprecated; deprecate it first \\(HW-35")
    _refused(repo, "b", [
        {"kind": "unbind", "term_id": "carrier", "contract_id": "silver_flights", "column_name": "carrier_code", "rationale": "r"},
        {"kind": "deprecate_term", "term_id": "carrier", "rationale": "r"},
        {"kind": "drop_term", "term_id": "carrier", "rationale": "r"},
    ], "carrier is deprecated in this set; a drop is its own later set")


def test_bind_is_additive_and_needs_a_committed_element_and_a_term_the_set_knows(repo: Path) -> None:
    proposal, _, out = _run(repo, "bind", [
        {"kind": "add_term", "term_id": "origin_airport", "term": "Origin airport", "definition": "d", "owner": "aviation stewards", "rationale": "r"},
        {"kind": "bind", "term_id": "origin_airport", "contract_id": "silver_flights", "column_name": "origin_airport", "rationale": "r"},
        {"kind": "bind", "term_id": "carrier", "contract_id": "silver_nyc_flights", "column_name": "carrier_code", "rationale": "r"},
        {"kind": "bind", "term_id": "cancellation", "contract_id": "silver_nyc_flights", "rationale": "the table"},
    ])
    assert [(a.kind, a.klass, a.element) for a in proposal.applied][1:] == [
        ("bind", "additive", "silver_flights.origin_airport"),
        ("bind", "additive", "silver_nyc_flights.carrier_code"),
        ("bind", "additive", "silver_nyc_flights (table)"),
    ]
    bindings = load_rendered(out, "glossary", "bindings.yaml", "bindings")
    assert bindings[-1]["column_name"] == "" and bindings[-1]["term_sha256"] == glossary_binding("cancellation", "x", "", "x")["term_sha256"]
    assert all(b["intent"] == INTENT and b["bound_on"] == TODAY for b in bindings[-3:])
    _refused(repo, "a", [{"kind": "bind", "term_id": "carrier", "contract_id": "silver_nope", "rationale": "r"}], "no committed contract with id 'silver_nope'")
    _refused(repo, "b", [{"kind": "bind", "term_id": "carrier", "contract_id": "silver_flights", "column_name": "nope", "rationale": "r"}], "contract silver_flights carries no column 'nope'")
    _refused(repo, "c", [{"kind": "bind", "term_id": "nope", "contract_id": "silver_flights", "rationale": "r"}], "carries no term 'nope'")
    _refused(repo, "d", [{"kind": "bind", "term_id": "carrier", "contract_id": "silver_flights", "column_name": "carrier_code", "rationale": "r"}],
             "silver_flights.carrier_code is already bound to carrier at its current digest; nothing changes")


def test_bind_re_binds_a_standing_binding_whose_term_moved_and_standing_drift_is_reported(repo: Path) -> None:
    # A hand edit moved the digest under two bindings (term_changed); one
    # explicit bind clears one of them, and the other is reported as drift.
    write_registers(repo, terms=[dict(t, definition="Edited by hand.") if t["term_id"] == "departure_delay" else t for t in TERMS])
    proposal, _, out = _run(repo, "rebind", [
        {"kind": "bind", "term_id": "departure_delay", "contract_id": "silver_flights", "column_name": "dep_delay_minutes", "rationale": "r"},
    ])
    assert proposal.applied[0].note.startswith("re-bound at the term's current digest") and proposal.applied[0].klass == "changing"
    assert proposal.rebound == []
    assert [d["element"] for d in proposal.standing_drift] == ["silver_nyc_flights.dep_delay_minutes"]
    assert "silver_nyc_flights.dep_delay_minutes reads changed; add a `bind`" in (out / "summary.md").read_text(encoding="utf-8")
    write_registers(repo, terms=load_rendered(out, "glossary", "terms.yaml", "terms"), glossary_bindings=load_rendered(out, "glossary", "bindings.yaml", "bindings"))
    states = [(r.element, r.state) for r in derive(repo, load_register(repo, GLOSSARY), TODAY) if r.row_id == "departure_delay"]
    assert states == [("silver_flights.dep_delay_minutes", "in_sync"), ("silver_nyc_flights.dep_delay_minutes", "term_changed")]


def test_unbind_is_removing_and_refuses_a_missing_binding(repo: Path) -> None:
    proposal, _, out = _run(repo, "unbind", [{"kind": "unbind", "term_id": "airport_ident", "contract_id": "silver_ourairports_airports", "column_name": "airport_ident", "rationale": "r"}])
    assert [(a.kind, a.klass) for a in proposal.applied] == [("unbind", "removing")]
    assert len(load_rendered(out, "glossary", "bindings.yaml", "bindings")) == 6
    _refused(repo, "a", [{"kind": "unbind", "term_id": "carrier", "contract_id": "silver_nyc_flights", "column_name": "carrier_code", "rationale": "r"}],
             "no binding of carrier on silver_nyc_flights.carrier_code")


# ---------------------------------------------------------------- the ontology kinds


def test_add_concept_is_additive_under_a_parent_the_set_knows(repo: Path) -> None:
    proposal, _, out = _run(repo, "addc", [
        {"kind": "add_concept", "concept_id": "runway", "label": "Runway", "parent_id": "airport", "definition": "A strip an aircraft lands on.", "owner": "aviation stewards", "rationale": "r"},
        {"kind": "add_concept", "concept_id": "taxiway", "label": "Taxiway", "parent_id": "runway", "definition": "A path between runway and gate.", "owner": "aviation stewards", "rationale": "r"},
    ])
    assert [(a.kind, a.klass, a.note) for a in proposal.applied] == [
        ("add_concept", "additive", "added 'Runway' under airport"), ("add_concept", "additive", "added 'Taxiway' under runway"),
    ]
    rows = load_rendered(out, "ontology", "concepts.yaml", "concepts")
    assert (rows[-2]["parent_id"], rows[-1]["parent_id"]) == ("airport", "runway")
    _refused(repo, "a", [{"kind": "add_concept", "concept_id": "flight", "label": "x", "definition": "d", "owner": "o", "rationale": "r"}], "concept_id 'flight' is taken")
    _refused(repo, "b", [{"kind": "add_concept", "concept_id": "x", "label": "Delay", "definition": "d", "owner": "o", "rationale": "r"}], "the label 'Delay' is owned by delay")
    _refused(repo, "c", [{"kind": "add_concept", "concept_id": "x", "label": "X", "parent_id": "nope", "definition": "d", "owner": "o", "rationale": "r"}], "\\(parent_id\\): the ontology register carries no concept 'nope'")
    _refused(repo, "d", [{"kind": "add_concept", "concept_id": "x", "label": "X", "definition": "d", "owner": "oscar", "rationale": "r"}], "owner 'oscar' is not a person or a team")


def test_amend_concept_is_changing_on_the_definition_or_the_parent_and_re_binds_case_j(repo: Path) -> None:
    write_registers(repo, ontology_bindings=[ontology_binding("delay", "silver_flights", "arr_delay_minutes", "x")] + [ontology_binding("departure_delay", "silver_flights", "dep_delay_minutes", "x")])
    proposal, _, out = _run(repo, "amendc", [{"kind": "amend_concept", "concept_id": "delay", "parent_id": "aircraft", "rationale": "r"}])
    assert proposal.applied[0].klass == "changing" and "the parent moved from flight to aircraft" in proposal.applied[0].note
    assert [r["element"] for r in proposal.rebound] == ["silver_flights.arr_delay_minutes"]  # the child's binding is untouched
    proposal, _, out = _run(repo, "amendd", [{"kind": "amend_concept", "concept_id": "flight", "definition": "A scheduled movement of one aircraft between two airports.", "rationale": "r"}])
    assert [r["element"] for r in proposal.rebound] == []  # flight carries no binding in this fixture
    proposal, _, out = _run(repo, "root", [{"kind": "amend_concept", "concept_id": "delay", "parent_id": "", "rationale": "to a root"}])
    assert "the parent moved from flight to a root" in proposal.applied[0].note
    assert [c for c in load_rendered(out, "ontology", "concepts.yaml", "concepts") if c["concept_id"] == "delay"][0]["parent_id"] is None


def test_amend_concept_refuses_a_cycle_itself_a_missing_parent_and_no_change(repo: Path) -> None:
    _refused(repo, "a", [{"kind": "amend_concept", "concept_id": "flight", "parent_id": "departure_delay", "rationale": "r"}],
             "parent departure_delay would close a cycle through flight")
    _refused(repo, "b", [{"kind": "amend_concept", "concept_id": "flight", "parent_id": "flight", "rationale": "r"}], "flight cannot be its own parent")
    _refused(repo, "c", [{"kind": "amend_concept", "concept_id": "flight", "parent_id": "nope", "rationale": "r"}], "carries no concept 'nope'")
    _refused(repo, "d", [{"kind": "amend_concept", "concept_id": "delay", "parent_id": "flight", "definition": CONCEPTS[4]["definition"], "rationale": "r"}],
             "delay already reads as amended; nothing changes")
    _refused(repo, "e", [{"kind": "amend_concept", "concept_id": "delay", "rationale": "r"}], "nothing changes")


def test_relabel_is_changing_and_re_binds_case_j2(repo: Path) -> None:
    proposal, _, out = _run(repo, "relabel", [{"kind": "relabel", "concept_id": "departure_delay", "label": "Departure lateness", "rationale": "r"}])
    assert proposal.applied[0].klass == "changing" and [r["element"] for r in proposal.rebound] == ["silver_flights.dep_delay_minutes"]
    _refused(repo, "a", [{"kind": "relabel", "concept_id": "departure_delay", "label": "Arrival delay", "rationale": "r"}], "the label 'Arrival delay' is owned by arrival_delay")
    _refused(repo, "b", [{"kind": "relabel", "concept_id": "departure_delay", "label": "Departure  delay", "rationale": "r"}], "already reads 'Departure delay'; nothing changes")


def test_deprecate_concept_and_drop_concept_follow_deprecate_then_drop_with_the_child_rule(repo: Path) -> None:
    proposal, _, out = _run(repo, "depc", [{"kind": "deprecate_concept", "concept_id": "flight", "superseded_by": "aircraft", "rationale": "r"}])
    assert proposal.applied[0].klass == "removing" and proposal.rebound == []
    write_registers(repo, concepts=load_rendered(out, "ontology", "concepts.yaml", "concepts"))
    assert [(r.state, r.detail) for r in derive(repo, load_register(repo, ONTOLOGY), TODAY) if r.row_id == "flight"] == [("concept_deprecated", "superseded by aircraft")]
    _refused(repo, "a", [{"kind": "drop_concept", "concept_id": "flight", "rationale": "r"}], "a binding stands on flight \\(silver_flights\\); unbind it first")
    _refused(repo, "b", [
        {"kind": "unbind_concept", "concept_id": "flight", "contract_id": "silver_flights", "rationale": "r"},
        {"kind": "drop_concept", "concept_id": "flight", "rationale": "r"},
    ], "delay names flight as parent; move the children first")
    proposal, _, out = _run(repo, "dropc", [
        {"kind": "unbind_concept", "concept_id": "flight", "contract_id": "silver_flights", "rationale": "r"},
        {"kind": "amend_concept", "concept_id": "delay", "parent_id": "", "rationale": "to a root"},
        {"kind": "drop_concept", "concept_id": "flight", "rationale": "r"},
    ])
    assert [a.kind for a in proposal.applied] == ["unbind_concept", "amend_concept", "drop_concept"]
    assert "flight" not in [c["concept_id"] for c in load_rendered(out, "ontology", "concepts.yaml", "concepts")]
    _refused(repo, "c", [{"kind": "drop_concept", "concept_id": "aircraft", "rationale": "r"}], "aircraft is not deprecated; deprecate it first")


def test_bind_concept_holds_one_concept_per_element_and_unbind_concept_removes(repo: Path) -> None:
    proposal, _, out = _run(repo, "bindc", [{"kind": "bind_concept", "concept_id": "aircraft", "contract_id": "silver_flights", "column_name": "tail_number", "rationale": "r"}])
    assert [(a.kind, a.klass, a.element) for a in proposal.applied] == [("bind_concept", "additive", "silver_flights.tail_number")]
    _refused(repo, "a", [{"kind": "bind_concept", "concept_id": "delay", "contract_id": "silver_flights", "column_name": "dep_delay_minutes", "rationale": "r"}],
             "silver_flights.dep_delay_minutes carries the concept departure_delay; an element carries one concept, so unbind it first")
    _refused(repo, "b", [{"kind": "bind_concept", "concept_id": "flight", "contract_id": "silver_flights", "rationale": "r"}],
             "silver_flights \\(table\\) is already bound to flight at its current digest; nothing changes")
    proposal, _, out = _run(repo, "swap", [
        {"kind": "unbind_concept", "concept_id": "departure_delay", "contract_id": "silver_flights", "column_name": "dep_delay_minutes", "rationale": "r"},
        {"kind": "bind_concept", "concept_id": "delay", "contract_id": "silver_flights", "column_name": "dep_delay_minutes", "rationale": "r"},
    ])
    assert [(a.kind, a.klass) for a in proposal.applied] == [("unbind_concept", "removing"), ("bind_concept", "additive")]
    _refused(repo, "c", [{"kind": "unbind_concept", "concept_id": "delay", "contract_id": "silver_flights", "rationale": "r"}], "no binding of delay on silver_flights \\(table\\)")


# ---------------------------------------------------------------- the rendering


def test_the_rendering_carries_the_four_files_the_record_and_the_summary(repo: Path) -> None:
    proposal, change_set, out = _run(repo, "render", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "operator", "rationale": "the airline's own word"}])
    assert out == repo / "proposals" / "meaning" / "render"
    assert sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()) == [
        "glossary/bindings.yaml", "glossary/terms.yaml", "ontology/bindings.yaml", "ontology/concepts.yaml", "record.json", "summary.md",
    ]
    record = json.loads((out / "record.json").read_text(encoding="utf-8"))
    assert record["module"] == "metricmine.meaning@1.0.0"
    assert record["source"] == "proposals/meaning/render.changes.yaml"
    assert (record["by"], record["intent"], record["intent_sha256"], record["day"]) == (BY, INTENT, sha256_text(INTENT), TODAY.isoformat())
    assert record["change_set"] == change_set.raw
    assert record["changes"] == [{"index": 1, "kind": "add_synonym", "register": "glossary", "class": "additive", "target": "carrier", "element": None,
                                  "note": "added the synonym 'operator'; never hashed, so no binding moves"}]
    assert record["rebound"] == [] and record["standing_drift"] == []
    assert set(record["register_digests"]) == {"glossary", "ontology"}
    assert record["register_digests"]["ontology"]["before"] == record["register_digests"]["ontology"]["after"]
    assert record["register_digests"]["glossary"]["before"] != record["register_digests"]["glossary"]["after"]
    for rel, digest in record["rendered"].items():
        assert hashlib.sha256((out / rel).read_bytes()).hexdigest() == digest
    summary = (out / "summary.md").read_text(encoding="utf-8")
    assert "- changes: 1 (1 additive, 0 changing, 0 removing)" in summary
    assert "cp proposals/meaning/render/glossary/*.yaml meaning/glossary/" in summary
    assert "    uv run python -m metricmine.meaning verify\n    uv run python -m metricmine.adoption scan" in summary
    assert "The merge is\nthe certification" in summary
    # The rendered files load under the contracts and verify clean.
    write_registers(
        repo,
        terms=load_rendered(out, "glossary", "terms.yaml", "terms"), glossary_bindings=load_rendered(out, "glossary", "bindings.yaml", "bindings"),
        concepts=load_rendered(out, "ontology", "concepts.yaml", "concepts"), ontology_bindings=load_rendered(out, "ontology", "bindings.yaml", "bindings"),
    )
    for register in load_all(repo).values():
        assert all(r.passed for r in run_rules(register, TODAY))


def test_an_untouched_register_renders_byte_for_byte_as_committed(repo: Path) -> None:
    _, _, out = _run(repo, "same", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "operator", "rationale": "r"}])
    for file in ("concepts.yaml", "bindings.yaml"):
        assert (out / "ontology" / file).read_bytes() == (repo / "meaning" / "ontology" / file).read_bytes()


def test_a_repeated_draft_overwrites_itself_and_reads_no_clock(repo: Path) -> None:
    _, _, first = _run(repo, "twice", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "operator", "rationale": "r"}])
    stale = first / "glossary" / "stale.txt"
    stale.write_text("x", encoding="utf-8")
    _, _, second = _run(repo, "twice", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "op", "rationale": "r"}])
    assert first == second and stale.exists()
    assert "op" in [t for t in load_rendered(second, "glossary", "terms.yaml", "terms") if t["term_id"] == "carrier"][0]["synonyms"]


def test_the_outbox_is_fenced_to_proposals_meaning(repo: Path, tmp_path: Path) -> None:
    path = write_change_set(repo, "fence", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "operator", "rationale": "r"}])
    change_set = load_change_set(repo, path)
    proposal = propose(repo, load_all(repo), change_set, TODAY)
    before = _tree_digest(repo)
    for outside in (repo / "meaning" / "glossary", repo / "contracts", repo / "proposals" / "documents" / "x", tmp_path / "elsewhere"):
        with pytest.raises(ChangeError, match="is outside proposals/meaning/"):
            write_proposal(repo, proposal, change_set, TODAY, outside)
    with pytest.raises(ChangeError, match="is proposals/meaning/ itself; a draft lands in a directory of its own under it"):
        write_proposal(repo, proposal, change_set, TODAY, repo / "proposals" / "meaning")
    assert _tree_digest(repo) == before
    inside = write_proposal(repo, proposal, change_set, TODAY, repo / "proposals" / "meaning" / "named")
    assert inside.is_dir() and (inside / "record.json").is_file()


def test_the_rendered_registers_are_held_to_the_contracts_error_rules(repo: Path) -> None:
    # The backstop: a set that the per-change checks let through but the
    # contract's rules would refuse is refused whole, nothing written.
    # Dropping a deprecated term that another deprecated term names as its
    # successor leaves that row's superseded_by pointing at nothing.
    write_registers(
        repo,
        terms=[dict(t, status="deprecated", superseded_by="tail_number") if t["term_id"] == "carrier"
               else dict(t, status="deprecated") if t["term_id"] == "tail_number" else t for t in TERMS],
        glossary_bindings=[b for b in GLOSSARY_BINDINGS if b["term_id"] not in ("carrier", "tail_number")],
    )
    _refused(repo, "x", [{"kind": "drop_term", "term_id": "tail_number", "rationale": "r"}],
             "the rendered registers would not pass their contracts: glossary: rule failed: A superseding term exists in the register, and only a deprecated term names one. \(1 rows, expected 0\); the set is refused whole")
    # A set that the per-change checks refuse is refused before the backstop:
    # a synonym equal to a label after NFKC folding.
    _refused(repo, "y", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "ＴＡＩＬ ＮＵＭＢＥＲ", "rationale": "r"}], "is owned by tail_number")


def test_a_committed_register_that_fails_its_rules_is_refused_before_any_change(repo: Path) -> None:
    write_registers(repo, terms=[t for t in TERMS if t["term_id"] != "arrival_delay"])
    _refused(repo, "orphan", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "operator", "rationale": "r"}],
             "the committed glossary register fails its contract's rules \(Every binding names a term the register carries. \(1 rows\)\); fix the register by pull request first")


def test_a_bind_before_a_change_of_the_same_row_is_re_bound_at_the_end(repo: Path) -> None:
    # A bind followed by an amend of the same term in one set: the binding
    # made at the pre-amend digest is re-bound at the end, listed, and the
    # rendered register reads in_sync; the same for bind_concept then relabel.
    proposal, _, out = _run(repo, "bind-then-amend", [
        {"kind": "bind", "term_id": "carrier", "contract_id": "silver_nyc_flights", "column_name": "carrier_code", "rationale": "r"},
        {"kind": "amend_definition", "term_id": "carrier", "definition": "The airline that operates a flight, by its two-letter code.", "rationale": "r"},
    ])
    assert sorted(r["element"] for r in proposal.rebound) == ["silver_flights.carrier_code", "silver_nyc_flights.carrier_code"]
    assert proposal.standing_drift == []
    write_registers(repo, terms=load_rendered(out, "glossary", "terms.yaml", "terms"), glossary_bindings=load_rendered(out, "glossary", "bindings.yaml", "bindings"))
    assert all(r.state == "in_sync" for r in derive(repo, load_register(repo, GLOSSARY), TODAY))
    proposal, _, out = _run(repo, "bindc-then-relabel", [
        {"kind": "bind_concept", "concept_id": "aircraft", "contract_id": "silver_flights", "column_name": "tail_number", "rationale": "r"},
        {"kind": "relabel", "concept_id": "aircraft", "label": "Airframe", "rationale": "r"},
    ])
    assert [r["element"] for r in proposal.rebound] == ["silver_flights.tail_number"]
    write_registers(repo, concepts=load_rendered(out, "ontology", "concepts.yaml", "concepts"), ontology_bindings=load_rendered(out, "ontology", "bindings.yaml", "bindings"))
    assert all(r.state == "in_sync" for r in derive(repo, load_register(repo, ONTOLOGY), TODAY))


def test_a_row_added_and_bound_in_one_set_is_bound_once_and_not_listed_as_re_bound(repo: Path) -> None:
    proposal, _, _ = _run(repo, "add-bind", [
        {"kind": "add_term", "term_id": "origin_airport", "term": "Origin airport", "definition": "d", "owner": "aviation stewards", "rationale": "r"},
        {"kind": "bind", "term_id": "origin_airport", "contract_id": "silver_flights", "column_name": "origin_airport", "rationale": "r"},
    ])
    assert proposal.rebound == [] and proposal.standing_drift == []


def test_review_by_takes_a_bare_date_or_text_and_refuses_an_impossible_one(repo: Path) -> None:
    base = {"kind": "add_term", "term_id": "x", "term": "X", "definition": "d", "owner": "aviation stewards", "rationale": "r"}
    _, _, out = _run(repo, "bare", [dict(base, review_by=date(2030, 1, 1))])
    assert load_rendered(out, "glossary", "terms.yaml", "terms")[-1]["review_by"] == date(2030, 1, 1)
    _, _, out = _run(repo, "text", [dict(base, review_by="2030-02-02")])
    assert load_rendered(out, "glossary", "terms.yaml", "terms")[-1]["review_by"] == date(2030, 2, 2)
    _, _, out = _run(repo, "default", [base])
    assert load_rendered(out, "glossary", "terms.yaml", "terms")[-1]["review_by"] == date(2027, 10, 26)
    _refused(repo, "bad", [dict(base, review_by="2030-13-45")], "review_by '2030-13-45' is not a date \(YYYY-MM-DD\)")


def test_fields_a_kind_does_not_read_are_refused(repo: Path) -> None:
    _refused(repo, "unread", [{"kind": "amend_definition", "term_id": "carrier", "definition": "A new definition.", "term": "Operating carrier", "rationale": "r"}],
             "change 1 \(amend_definition\) carries fields the kind does not read: term")


def test_a_register_contract_is_not_an_element(repo: Path) -> None:
    _refused(repo, "reg", [{"kind": "bind", "term_id": "carrier", "contract_id": "glossary_register", "column_name": "term", "rationale": "r"}],
             "glossary_register is a register, not an element a term or a concept labels")


def test_a_bind_to_a_deprecated_row_carries_a_note(repo: Path) -> None:
    write_registers(repo, terms=[dict(t, status="deprecated", superseded_by="carrier") if t["term_id"] == "tail_number" else t for t in TERMS])
    proposal, _, _ = _run(repo, "depbind", [{"kind": "bind", "term_id": "tail_number", "contract_id": "silver_nyc_flights", "column_name": "carrier_code", "rationale": "r"}])
    assert proposal.applied[0].note.endswith("; the term is deprecated, superseded by carrier")


@pytest.mark.skipif(os.name == "nt", reason="a symbolic link is a POSIX fixture")
def test_a_symbolic_link_in_the_outbox_never_carries_a_write_into_the_registers(repo: Path) -> None:
    # F-74: a link planted in the draft directory is refused before any
    # write, whether it stands at the directory, a folder, or a file.
    path = write_change_set(repo, "link", [{"kind": "add_synonym", "term_id": "carrier", "synonym": "operator", "rationale": "r"}])
    change_set = load_change_set(repo, path)
    proposal = propose(repo, load_all(repo), change_set, TODAY)
    before = _tree_digest(repo)
    out = repo / "proposals" / "meaning" / "link"
    out.mkdir(parents=True)
    (out / "glossary").symlink_to(repo / "meaning" / "glossary", target_is_directory=True)
    with pytest.raises(ChangeError, match="link/glossary is a symbolic link; a draft is written through no link"):
        write_proposal(repo, proposal, change_set, TODAY)
    (out / "glossary").unlink()
    (out / "glossary").mkdir()
    (out / "record.json").symlink_to(repo / "contracts" / "glossary_register.odcs.yaml")
    with pytest.raises(ChangeError, match="record.json is a symbolic link"):
        write_proposal(repo, proposal, change_set, TODAY)
    # A link at a later file is refused before the first write: nothing
    # but the planted link and the empty folders stands in the outbox.
    assert sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if not p.is_dir()) == ["record.json"]
    (out / "record.json").unlink()
    # A directory link is named as a link whether it points out of the
    # outbox or within it, and a plain path out of it is named as outside.
    away = repo / "proposals" / "meaning" / "away"
    away.symlink_to(repo / "meaning", target_is_directory=True)
    with pytest.raises(ChangeError, match="away is a symbolic link; a draft is written through no link"):
        write_proposal(repo, proposal, change_set, TODAY, away)
    with pytest.raises(ChangeError, match="is outside proposals/meaning/"):
        write_proposal(repo, proposal, change_set, TODAY, repo / "proposals" / "meaning" / ".." / ".." / "meaning")
    (repo / "proposals" / "meaning" / "other").mkdir()
    near = repo / "proposals" / "meaning" / "near"
    near.symlink_to(repo / "proposals" / "meaning" / "other", target_is_directory=True)
    with pytest.raises(ChangeError, match="near is a symbolic link; a draft is written through no link"):
        write_proposal(repo, proposal, change_set, TODAY, near)
    assert not list((repo / "proposals" / "meaning" / "other").iterdir())
    assert _tree_digest(repo) == before
