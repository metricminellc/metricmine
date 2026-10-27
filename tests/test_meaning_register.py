"""The governed meaning registers (D-44): held to their contracts, the
contracts' own quality rules run over the rows at the severity they
declare (D-28), a declarer, a binder, or an owner is a person, an
intent travels with its hash, the digests are the probe transcript's,
and the committed registers conform with every binding in sync.

Keyless, no network. Every date is fixed.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from metricmine.documents.register import RegisterError, is_person
from metricmine.meaning import register as reg
from metricmine.meaning.register import GLOSSARY, ONTOLOGY, concept_digest, load_all, load_register, register_digest, run_rules, term_digest
from metricmine.meaning.states import derive
from meaning_fixtures import (
    BY,
    CONCEPTS,
    DAY,
    GLOSSARY_BINDINGS,
    ONTOLOGY_BINDINGS,
    REPO,
    TERMS,
    concept_row,
    glossary_binding,
    ontology_binding,
    term_row,
    write_registers,
    write_repo,
)

TODAY = DAY

# The Prep H probe transcript's 5b digests (first sixteen hex characters),
# the record this slice reproduces.
TERM_DIGESTS = {
    "departure_delay": "8ff9e9b055c486cd",
    "arrival_delay": "85b954443b102d00",
    "carrier": "7d6e9dea41c2c3fc",
    "tail_number": "f56be72c72ab5213",
    "airport_ident": "82b455f40c84f95f",
    "cancellation": "843d321eb15b8b0a",
}
CONCEPT_DIGESTS = {
    "flight": "a823432585c99871",
    "airport": "e84fcf210a1f1cc9",
    "aircraft": "f93608439910fb22",
    "weather_observation": "627e4b05f6d0ce3f",
    "delay": "6604406820f9083f",
    "departure_delay": "a7d358dd8614e954",
    "arrival_delay": "ebcd58599770af3e",
}


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return write_repo(tmp_path)


# ---------------------------------------------------------------- the contracts and conformance


def test_the_two_contracts_declare_their_tables_and_rules(repo: Path) -> None:
    glossary = reg.load_register_contract(repo, GLOSSARY)
    ontology = reg.load_register_contract(repo, ONTOLOGY)
    assert (glossary.id, glossary.version) == ("glossary_register", "1.0.0")
    assert (ontology.id, ontology.version) == ("ontology_register", "1.0.0")
    assert set(glossary.columns) == {"glossary_terms", "glossary_bindings"}
    assert set(ontology.columns) == {"ontology_concepts", "ontology_bindings"}
    assert [c.name for c in glossary.columns["glossary_terms"]] == [
        "term_id", "term", "definition", "synonyms", "owner", "status", "superseded_by", "declared_by", "declared_on", "review_by",
    ]
    assert [c.name for c in ontology.columns["ontology_concepts"]] == [
        "concept_id", "label", "parent_id", "definition", "owner", "status", "superseded_by", "declared_by", "declared_on", "review_by",
    ]
    assert [c.name for c in glossary.columns["glossary_bindings"]] == [
        "term_id", "contract_id", "column_name", "term_sha256", "intent", "intent_sha256", "bound_by", "bound_on",
    ]
    assert [c.name for c in ontology.columns["ontology_bindings"]] == [
        "concept_id", "contract_id", "column_name", "concept_sha256", "intent", "intent_sha256", "bound_by", "bound_on",
    ]
    # The rules D-44 names: ten for the glossary, eleven for the ontology
    # (the label, the digest, and the review date hold for both registers;
    # the id's form is a closed field).
    assert len(glossary.rules) == 10 and len(ontology.rules) == 11
    assert [r.severity for r in glossary.rules].count("warn") == 1
    assert [r.severity for r in ontology.rules].count("warn") == 1
    assert "The parent graph has no cycle." in [r.description for r in ontology.rules]


def test_a_conforming_register_loads_with_dates_parsed(repo: Path) -> None:
    registers = load_all(repo)
    glossary, ontology = registers["glossary"], registers["ontology"]
    assert len(glossary.rows) == 6 and len(glossary.bindings) == 7
    assert len(ontology.rows) == 7 and len(ontology.bindings) == 4
    assert glossary.rows[0]["declared_on"] == TODAY
    assert glossary.row("carrier")["term"] == "Carrier"
    assert [b["column_name"] for b in glossary.bindings_for("departure_delay")] == ["dep_delay_minutes", "dep_delay_minutes"]
    assert ontology.row("missing") is None


def test_an_empty_register_loads_and_passes_every_rule(tmp_path: Path) -> None:
    write_repo(tmp_path, terms=[], glossary_bindings=[], concepts=[], ontology_bindings=[])
    registers = load_all(tmp_path)
    for register in registers.values():
        assert register.rows == [] and register.bindings == []
        assert all(r.passed for r in run_rules(register, TODAY))


def test_rows_files_may_be_absent_when_the_contracts_stand(tmp_path: Path) -> None:
    # The window after the contracts' pull request and before the rows: an
    # adopter adds the contracts first and the registers read as empty.
    from meaning_fixtures import write_contracts

    write_contracts(tmp_path)
    registers = load_all(tmp_path)
    assert all(r.rows == [] and r.bindings == [] for r in registers.values())


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"colour": "blue"}, "terms.yaml row 1: columns not in the contract: colour"),
        ({"definition": None}, "terms.yaml row 1: required column definition is missing"),
        ({"declared_on": "yesterday"}, "terms.yaml row 1.declared_on: not a date"),
        ({"owner": 3}, "terms.yaml row 1.owner: expected text, got int"),
    ],
)
def test_a_term_row_that_does_not_conform_is_refused_by_file_row_and_column(repo: Path, change: dict, message: str) -> None:
    row = term_row(**{k: v for k, v in change.items() if v is not None})
    for key, value in change.items():
        if value is None:
            row.pop(key)
    write_registers(repo, terms=[row], glossary_bindings=[])
    with pytest.raises(RegisterError, match=message):
        load_register(repo, GLOSSARY)


def test_a_column_the_contract_declares_as_required_and_no_row_carries_is_refused(repo: Path) -> None:
    # Red: a required column added to the contract that no committed row
    # carries is refused by file, row, and column; green again once the
    # column is optional or the rows carry it.
    path = repo / "contracts" / "ontology_register.odcs.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["schema"][0]["properties"].append({"name": "domain", "logicalType": "string", "physicalType": "VARCHAR", "required": True})
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    with pytest.raises(RegisterError, match="concepts.yaml row 1: required column domain is missing"):
        load_register(repo, ONTOLOGY)
    doc["schema"][0]["properties"][-1]["required"] = False
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    assert len(load_register(repo, ONTOLOGY).rows) == 7


def test_a_binding_row_with_a_column_no_contract_carries_is_refused(repo: Path) -> None:
    write_registers(repo, ontology_bindings=[ontology_binding("flight", "silver_flights", "", "x", served="yes")])
    with pytest.raises(RegisterError, match="bindings.yaml row 1: columns not in the contract: served"):
        load_register(repo, ONTOLOGY)


def test_malformed_yaml_and_a_missing_contract_are_named_never_a_traceback(repo: Path) -> None:
    (repo / "meaning" / "glossary" / "terms.yaml").write_text("terms: [unclosed\n", encoding="utf-8")
    with pytest.raises(RegisterError, match="terms.yaml: not valid YAML"):
        load_register(repo, GLOSSARY)
    write_registers(repo)
    (repo / "contracts" / "ontology_register.odcs.yaml").unlink()
    with pytest.raises(RegisterError, match="no register contract at contracts/ontology_register.odcs.yaml"):
        load_all(repo)


def test_a_flow_mapping_definition_is_read_whole(repo: Path) -> None:
    # The probe's first fixture defect: a YAML flow mapping splits a
    # definition on its commas unless quoted. The loader reads what YAML
    # gives it; the dumper writes block style, so a rendered row never
    # takes the flow form, and a hand-typed flow row still conforms.
    (repo / "meaning" / "glossary" / "terms.yaml").write_text(
        "terms:\n- {term_id: x, term: X, definition: 'one, two', owner: a.person, status: active,"
        " declared_by: a.person, declared_on: 2026-10-26, review_by: 2027-10-26}\n",
        encoding="utf-8",
    )
    (repo / "meaning" / "glossary" / "bindings.yaml").write_text("bindings: []\n", encoding="utf-8")
    assert load_register(repo, GLOSSARY).rows[0]["definition"] == "one, two"


# ---------------------------------------------------------------- persons and intents


@pytest.mark.parametrize("column", ["declared_by", "owner"])
def test_a_term_declared_or_owned_by_an_agent_or_model_is_refused(repo: Path, column: str) -> None:
    write_registers(repo, terms=[term_row(**{column: "claude-sonnet-5"})], glossary_bindings=[])
    with pytest.raises(RegisterError, match=f"terms.yaml departure_delay: {column} 'claude-sonnet-5' is not a person"):
        load_register(repo, GLOSSARY)


@pytest.mark.parametrize("name", ["claude-sonnet-5", "oscar", "silver-cleanup-proposer"])
def test_a_binder_that_is_not_a_person_is_refused_and_a_person_is_not(repo: Path, name: str) -> None:
    assert not is_person(name) and is_person(BY)
    write_registers(repo, ontology_bindings=[ontology_binding("flight", "silver_flights", "", "x", bound_by=name)])
    with pytest.raises(RegisterError, match=f"bindings.yaml \\('flight', 'silver_flights', ''\\): bound_by '{name}' is not a person"):
        load_register(repo, ONTOLOGY)


def test_an_intent_edited_after_the_fact_fails_its_hash(repo: Path) -> None:
    drifted = glossary_binding("carrier", "silver_flights", "carrier_code", "the words")
    drifted["intent"] = "other words"
    write_registers(repo, glossary_bindings=[drifted])
    with pytest.raises(RegisterError, match="intent_sha256 does not match the intent"):
        load_register(repo, GLOSSARY)


def test_a_team_is_an_owner_by_attestation(repo: Path) -> None:
    assert load_register(repo, GLOSSARY).row("carrier")["owner"] == "aviation stewards"


# ---------------------------------------------------------------- the digests


def test_the_term_digests_are_the_probe_transcripts(repo: Path) -> None:
    register = load_register(repo, GLOSSARY)
    assert {row_id: digest[:16] for row_id, digest in register.digests().items()} == TERM_DIGESTS
    assert all(len(d) == 64 for d in register.digests().values())


def test_the_concept_digests_are_the_probe_transcripts(repo: Path) -> None:
    register = load_register(repo, ONTOLOGY)
    assert {row_id: digest[:16] for row_id, digest in register.digests().items()} == CONCEPT_DIGESTS


def test_a_one_word_edit_moves_a_term_digest_and_a_rewrap_does_not() -> None:
    base = term_row()
    edited = term_row(definition=base["definition"].replace("scheduled departure", "published departure"))
    rewrapped = term_row(definition="Minutes  between the actual and\nthe scheduled departure of a ﬂight. Negative when the flight left early. Absent when the flight was cancelled.")
    assert term_digest(edited) != term_digest(base)
    assert term_digest(rewrapped) == term_digest(base)  # NFKC folds the ligature; whitespace collapses


def test_a_synonym_never_moves_a_term_digest_and_a_label_does() -> None:
    base = term_row()
    assert term_digest(term_row(synonyms="dep delay; dep_delay; departure delay minutes")) == term_digest(base)
    assert term_digest(term_row(synonyms=None)) == term_digest(base)
    assert term_digest(term_row(term="Departure delay (minutes)")) != term_digest(base)
    assert term_digest(term_row(status="deprecated", superseded_by="x", owner="other")) == term_digest(base)


def test_a_concept_digest_is_a_node_digest() -> None:
    rows = {r["concept_id"]: r for r in CONCEPTS}
    moved = concept_row(**{**rows["delay"], "parent_id": "aircraft"})
    assert concept_digest(moved) != concept_digest(rows["delay"])
    # A grandparent's move does not re-ask a grandchild: departure_delay's
    # digest reads its own parent id, not the path above it.
    moved_rows = {**rows, "delay": moved}
    assert concept_digest(moved_rows["departure_delay"]) == concept_digest(rows["departure_delay"])
    assert concept_digest(rows["departure_delay"]).startswith(CONCEPT_DIGESTS["departure_delay"])
    assert concept_digest(concept_row(**{**rows["departure_delay"], "label": "Departure lateness"})) != concept_digest(rows["departure_delay"])
    assert concept_digest(concept_row(**{**rows["flight"], "parent_id": None})) == concept_digest(rows["flight"])
    assert concept_digest(concept_row(**{**rows["flight"], "parent_id": ""})) == concept_digest(rows["flight"])


# ---------------------------------------------------------------- the contracts' rules


def test_every_rule_passes_on_the_certified_fixture(repo: Path) -> None:
    registers = load_all(repo)
    results = run_rules(registers["glossary"], TODAY) + run_rules(registers["ontology"], TODAY)
    assert len(results) == 21 and all(r.passed for r in results)


def _fires(repo: Path, spec, description: str, actual: int | None = None, severity: str = "error") -> None:
    results = {r.description: r for r in run_rules(load_register(repo, spec), TODAY)}
    result = results[description]
    assert not result.passed and result.severity == severity, (description, result)
    if actual is not None:
        assert result.actual == actual


def test_a_removed_term_fires_the_binding_rule(repo: Path) -> None:
    write_registers(repo, terms=[t for t in TERMS if t["term_id"] != "arrival_delay"])
    _fires(repo, GLOSSARY, "Every binding names a term the register carries.", 1)


def test_an_active_term_naming_a_successor_fires_and_a_deprecated_one_passes(repo: Path) -> None:
    terms = [term_row(superseded_by="carrier")] + TERMS[1:]
    write_registers(repo, terms=terms)
    _fires(repo, GLOSSARY, "A superseding term exists in the register, and only a deprecated term names one.", 1)
    terms = [term_row(status="deprecated", superseded_by="carrier")] + TERMS[1:]
    write_registers(repo, terms=terms)
    assert all(r.passed for r in run_rules(load_register(repo, GLOSSARY), TODAY))
    terms = [term_row(status="deprecated", superseded_by="nope")] + TERMS[1:]
    write_registers(repo, terms=terms)
    _fires(repo, GLOSSARY, "A superseding term exists in the register, and only a deprecated term names one.", 1)


def test_a_synonym_owned_by_two_terms_fires_the_synonym_rule(repo: Path) -> None:
    terms = TERMS[:2] + [dict(TERMS[2], synonyms="airline code; dep_delay")] + TERMS[3:]
    write_registers(repo, terms=terms)
    _fires(repo, GLOSSARY, "A synonym is owned by one term and never equals a term's label.", 1)


def test_two_terms_with_one_label_fire_the_label_rule_under_its_own_name(repo: Path) -> None:
    terms = TERMS[:1] + [dict(TERMS[1], term="departure delay")] + TERMS[2:]
    write_registers(repo, terms=terms)
    _fires(repo, GLOSSARY, "A term's label is unique.", 1)
    _fires(repo, GLOSSARY, "A synonym is owned by one term and never equals a term's label.", 1)


def test_a_closed_status_a_duplicate_id_and_a_short_digest_fire(repo: Path) -> None:
    write_registers(repo, terms=[term_row(status="retired")] + TERMS[1:])
    _fires(repo, GLOSSARY, "Status is a closed field.", 1)
    write_registers(repo, terms=TERMS + [term_row(term="Departure delay 2")])
    _fires(repo, GLOSSARY, "A term id is unique.", 1)
    write_registers(repo, terms=[term_row(term_id="Departure-Delay")] + TERMS[1:], glossary_bindings=[])
    _fires(repo, GLOSSARY, "A term id is lowercase letters, digits, and underscores.", 1)
    write_registers(repo, concepts=[dict(CONCEPTS[0], concept_id="Flight")] + CONCEPTS[1:], ontology_bindings=[])
    _fires(repo, ONTOLOGY, "A concept id is lowercase letters, digits, and underscores.", 1)
    write_registers(repo, glossary_bindings=[glossary_binding("carrier", "silver_flights", "carrier_code", "x", term_sha256="abc")])
    _fires(repo, GLOSSARY, "A binding carries the term's digest.", 1)
    write_registers(repo, glossary_bindings=GLOSSARY_BINDINGS + [GLOSSARY_BINDINGS[2]])
    _fires(repo, GLOSSARY, "A binding is unique per term and element.", 1)


def test_a_past_review_date_fires_the_warn_rule_and_the_calendar_is_a_parameter(repo: Path) -> None:
    results = {r.description: r for r in run_rules(load_register(repo, GLOSSARY), date(2028, 1, 1))}
    result = results["No term is past its review date."]
    assert result.severity == "warn" and result.actual == 6 and not result.passed
    assert all(r.passed for r in run_rules(load_register(repo, GLOSSARY), TODAY))
    assert all(r.passed for r in run_rules(load_register(repo, GLOSSARY), None))  # no calendar, no review rule
    results = {r.description: r for r in run_rules(load_register(repo, ONTOLOGY), date(2028, 1, 1))}
    assert results["No concept is past its review date."].actual == 7


def test_a_removed_concept_fires_the_parent_rule_and_the_binding_rule(repo: Path) -> None:
    write_registers(repo, concepts=[c for c in CONCEPTS if c["concept_id"] != "flight"])
    _fires(repo, ONTOLOGY, "A parent is a concept the register carries, and never the concept itself.", 1)
    _fires(repo, ONTOLOGY, "Every binding names a concept the register carries.", 1)


def test_a_concept_that_is_its_own_parent_fires(repo: Path) -> None:
    write_registers(repo, concepts=[dict(c, parent_id="flight") if c["concept_id"] == "flight" else c for c in CONCEPTS])
    _fires(repo, ONTOLOGY, "A parent is a concept the register carries, and never the concept itself.", 1)


def test_a_two_step_and_a_three_step_parent_cycle_fire_the_cycle_rule(repo: Path) -> None:
    two = [dict(c, parent_id="delay") if c["concept_id"] == "flight" else c for c in CONCEPTS]
    write_registers(repo, concepts=two)
    _fires(repo, ONTOLOGY, "The parent graph has no cycle.", 2)
    three = [
        dict(c, parent_id="aircraft") if c["concept_id"] == "airport"
        else dict(c, parent_id="weather_observation") if c["concept_id"] == "aircraft"
        else c
        for c in CONCEPTS
    ]
    write_registers(repo, concepts=three)
    _fires(repo, ONTOLOGY, "The parent graph has no cycle.", 3)


def test_a_second_concept_on_one_element_fires(repo: Path) -> None:
    write_registers(repo, ontology_bindings=ONTOLOGY_BINDINGS + [ontology_binding("delay", "silver_flights", "dep_delay_minutes", "x")])
    _fires(repo, ONTOLOGY, "An element carries one concept.", 1)


def test_two_concepts_with_one_label_and_a_short_concept_digest_fire(repo: Path) -> None:
    write_registers(repo, concepts=CONCEPTS[:1] + [dict(CONCEPTS[1], label="flight")] + CONCEPTS[2:])
    _fires(repo, ONTOLOGY, "A concept's label is unique.", 1)
    write_registers(repo, ontology_bindings=[ontology_binding("flight", "silver_flights", "", "x", concept_sha256="")])
    _fires(repo, ONTOLOGY, "A binding carries the concept's digest.", 1)


def test_a_deprecated_concept_with_no_successor_passes_and_an_active_one_naming_one_fires(repo: Path) -> None:
    write_registers(repo, concepts=[dict(c, status="deprecated") if c["concept_id"] == "aircraft" else c for c in CONCEPTS])
    assert all(r.passed for r in run_rules(load_register(repo, ONTOLOGY), TODAY))
    write_registers(repo, concepts=[dict(c, superseded_by="flight") if c["concept_id"] == "aircraft" else c for c in CONCEPTS])
    _fires(repo, ONTOLOGY, "A superseding concept exists in the register, and only a deprecated concept names one.", 1)


# ---------------------------------------------------------------- the committed registers


def test_the_committed_registers_conform_and_every_binding_is_in_sync() -> None:
    # The gate of record (Amendment AC): the registers on main conform,
    # every rule at error severity passes, every binding reads in_sync (or
    # the deprecation D-44 orders before a drop, reported as declared)
    # with no flag for a fixed day, and no review date is past it.
    registers = load_all(REPO)
    for register in registers.values():
        assert register.rows, f"the committed {register.spec.kind} register carries rows"
        for result in run_rules(register, TODAY):
            assert result.passed, (register.spec.kind, result)
        for report in derive(REPO, register, TODAY):
            assert report.state in ("in_sync", f"{register.spec.noun}_deprecated"), (report.register, report.row_id, report.element, report.state, report.detail)
            assert report.flags == [], (report.row_id, report.flags)
        for row in register.rows:
            assert row["review_by"] > TODAY, (register.spec.kind, row[register.spec.id_field])


def test_the_demo_registers_are_the_probe_fixture_less_the_invoice_line() -> None:
    # The demo's vocabulary comes from the two public sources D-44 names;
    # the probe fixture's invoice line (the retail sample's entity type)
    # is not committed, so every owner is the aviation stewards.
    registers = load_all(REPO)
    assert "invoice_line" not in registers["ontology"].digests()
    assert {t["owner"] for t in registers["glossary"].rows} == {"aviation stewards"}
    assert {c["owner"] for c in registers["ontology"].rows} == {"aviation stewards"}


def test_the_demo_registers_are_the_probe_fixture() -> None:
    registers = load_all(REPO)
    glossary, ontology = registers["glossary"], registers["ontology"]
    assert [t["term_id"] for t in glossary.rows] == [t["term_id"] for t in TERMS]
    assert [c["concept_id"] for c in ontology.rows] == [c["concept_id"] for c in CONCEPTS]
    assert {row_id: d[:16] for row_id, d in glossary.digests().items()} == TERM_DIGESTS
    assert {row_id: d[:16] for row_id, d in ontology.digests().items()} == CONCEPT_DIGESTS
    assert [(b["contract_id"], b["column_name"]) for b in glossary.bindings] == [
        ("silver_flights", "dep_delay_minutes"),
        ("silver_flights", "arr_delay_minutes"),
        ("silver_flights", "carrier_code"),
        ("silver_flights", "tail_number"),
        ("silver_flights", ""),
        ("silver_nyc_flights", "dep_delay_minutes"),
        ("silver_ourairports_airports", "airport_ident"),
    ]
    assert [(b["concept_id"], b["contract_id"], b["column_name"]) for b in ontology.bindings] == [
        ("flight", "silver_flights", ""),
        ("weather_observation", "silver_airport_weather", ""),
        ("departure_delay", "silver_flights", "dep_delay_minutes"),
        ("airport", "silver_ourairports_airports", ""),
    ]
    assert all(b["bound_by"] == BY for b in glossary.bindings + ontology.bindings)


def test_the_committed_glossary_register_digest_as_cut() -> None:
    # The glossary register's digest as the Prep H probe printed it
    # (REGISTER-DIGEST glossary 994ccc515b8b8191): the committed rows are
    # the probe's rows, intents included. This pin is the slice's first
    # cut; the first merged change set moves it, and the maintainer who
    # merges it re-pins the value here in the same pull request.
    assert register_digest(load_all(REPO)["glossary"]).startswith("994ccc515b8b8191")


def test_the_committed_register_files_are_plain_yaml_in_the_dumpers_form() -> None:
    for folder, file in (("glossary", "terms.yaml"), ("glossary", "bindings.yaml"), ("ontology", "concepts.yaml"), ("ontology", "bindings.yaml")):
        text = (REPO / "meaning" / folder / file).read_text(encoding="utf-8")
        assert "&id" not in text and "*id" not in text and text.startswith("# The governed ")
        yaml.safe_load(text)
