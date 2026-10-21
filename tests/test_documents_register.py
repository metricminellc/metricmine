"""The governed documents register (D-43): held to its contract, the
contract's own quality rules run over the rows at the severity they
declare (D-28), a declarer or binder is a person, an intent travels with
its hash, and the committed register is in sync with the committed
document under the running extractor.

Keyless, no network. Every date is fixed.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from metricmine.agents import mapping_proposer, silver_proposer
from metricmine.agents import models as agent_models
from metricmine.documents import register as reg
from metricmine.documents.extract import EXTRACTOR_ID, extract_path
from metricmine.documents.register import RegisterError, integrity_problems, is_person, load_register, run_rules
from metricmine.documents.states import derive
from documents_fixtures import POLICY_MD, binding_row, policy_digest, standing_row, write_register, write_repo

REPO = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 17)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return write_repo(
        tmp_path,
        standing=[standing_row(text_sha256=policy_digest())],
        bindings=[binding_row()],
        documents={"docs/policy.md": POLICY_MD},
    )


# ---------------------------------------------------------------- the contract and conformance


def test_the_contract_declares_the_two_tables_and_their_rules(repo: Path) -> None:
    contract = reg.load_contract(repo)
    assert contract.id == "documents_register" and contract.version == "1.0.0"
    assert set(contract.columns) == {"documents_standing", "documents_bindings"}
    assert [c.name for c in contract.columns["documents_bindings"]][:3] == ["document_id", "contract_id", "column_name"]
    assert len(contract.rules) == 9
    assert {r.severity for r in contract.rules} == {"error", "warn"}


def test_a_conforming_register_loads_with_dates_parsed(repo: Path) -> None:
    register = load_register(repo)
    assert len(register.standing) == 1 and len(register.bindings) == 1
    assert register.standing[0]["declared_on"] == TODAY
    assert register.bindings_for("policy")[0]["column_name"] == "delay_minutes"
    assert register.standing_row("missing") is None


def test_an_empty_register_loads(tmp_path: Path) -> None:
    write_repo(tmp_path, standing=[], bindings=[])
    register = load_register(tmp_path)
    assert register.standing == [] and register.bindings == []
    assert all(r.passed for r in run_rules(register, TODAY))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"colour": "blue"}, "columns not in the contract: colour"),
        ({"title": None}, "required column title is missing"),
        ({"declared_on": "yesterday"}, "not a date"),
        ({"governance": 3}, "expected text, got int"),
    ],
)
def test_a_row_that_does_not_conform_is_refused_by_file_row_and_column(repo: Path, change: dict, message: str) -> None:
    row = standing_row(text_sha256=policy_digest(), **{k: v for k, v in change.items() if v is not None})
    for key, value in change.items():
        if value is None:
            row.pop(key)
    write_register(repo, [row], [binding_row()])
    with pytest.raises(RegisterError) as info:
        load_register(repo)
    assert "standing.yaml row 1" in str(info.value) and message in str(info.value)


def test_rows_must_be_a_list_of_mappings(repo: Path) -> None:
    (repo / "documents" / "register" / "bindings.yaml").write_text("bindings: not-a-list\n", encoding="utf-8")
    with pytest.raises(RegisterError, match="must be a list of rows"):
        load_register(repo)


def test_malformed_yaml_and_a_timestamp_are_refused_by_name_never_a_traceback(repo: Path) -> None:
    standing = repo / "documents" / "register" / "standing.yaml"
    good = standing.read_text(encoding="utf-8")
    standing.write_text("documents: [unclosed\n", encoding="utf-8")
    with pytest.raises(RegisterError, match="standing.yaml: not valid YAML"):
        load_register(repo)
    standing.write_text("- a list, not a mapping\n", encoding="utf-8")
    with pytest.raises(RegisterError, match="expected a mapping at the top level"):
        load_register(repo)
    standing.write_text(good.replace("review_by: 2027-10-17", "review_by: 2027-10-17T00:00:00"), encoding="utf-8")
    with pytest.raises(RegisterError, match="a timestamp where a date belongs"):
        load_register(repo)


# ---------------------------------------------------------------- persons


@pytest.mark.parametrize("name", ["silver-cleanup-proposer", "gold-mapping-proposer", "claude-sonnet-5", "claude-opus-5", "claude-fable-5", "claude-anything", "oscar", "Oscar", "", "  "])
def test_known_agent_model_and_tool_names_are_not_persons(name: str) -> None:
    assert not is_person(name)


@pytest.mark.parametrize("name", ["justinrgoff", "a.person", "Maria Steward"])
def test_other_names_are_persons_by_attestation(name: str) -> None:
    assert is_person(name)


def test_the_refused_tool_name_is_the_repository_subagent() -> None:
    assert reg.KNOWN_TOOL_NAMES == ("oscar",)
    assert (REPO / ".claude" / "agents" / "oscar.md").is_file()


def test_the_refused_names_are_held_to_the_agents_package() -> None:
    # The two proposers' names (D-10) and the D-34 allow-list, as the code
    # carries them: a new model or a renamed agent moves this tuple too.
    assert set(reg.KNOWN_MODEL_IDS) == set(agent_models.MODELS)
    assert set(reg.KNOWN_AGENT_NAMES) == {silver_proposer.NAME, mapping_proposer.NAME}
    assert len(reg.KNOWN_AGENT_NAMES) == 2  # exactly two agents (D-10)


def test_a_declarer_or_binder_that_is_not_a_person_is_refused(repo: Path) -> None:
    write_register(repo, [standing_row(text_sha256=policy_digest(), declared_by="claude-sonnet-5")], [binding_row()])
    with pytest.raises(RegisterError, match="declared_by 'claude-sonnet-5' is not a person"):
        load_register(repo)
    write_register(repo, [standing_row(text_sha256=policy_digest())], [binding_row(bound_by="gold-mapping-proposer")])
    with pytest.raises(RegisterError, match="bound_by 'gold-mapping-proposer' is not a person"):
        load_register(repo)


# ---------------------------------------------------------------- integrity


def test_duplicate_ids_orphans_duplicates_and_a_drifted_intent_are_named(repo: Path) -> None:
    register = load_register(repo)
    register.standing.append(dict(register.standing[0]))
    register.bindings.append(dict(register.bindings[0]))
    register.bindings.append(binding_row(document_id="ghost"))
    register.bindings.append(binding_row(column_name="carrier", intent_sha256="0" * 64))
    problems = integrity_problems(register)
    assert any("document_id is not unique" in p for p in problems)
    assert any("duplicate binding" in p for p in problems)
    assert any("no standing row for ghost" in p for p in problems)
    assert any("intent_sha256 does not match the intent" in p for p in problems)


# ---------------------------------------------------------------- the contract's rules in DuckDB


def _rule(results, fragment: str):
    (result,) = [r for r in results if fragment in r.description]
    return result


def test_the_rules_pass_on_a_conforming_register(repo: Path) -> None:
    results = run_rules(load_register(repo), TODAY)
    assert len(results) == 9 and all(r.passed for r in results)


def test_each_closed_set_rule_turns_red_at_error_severity(repo: Path) -> None:
    register = load_register(repo)
    register.standing[0]["governance"] = "wiki"
    register.standing[0]["access"] = "ftp"
    register.standing[0]["certification_source"] = "vibes"
    register.standing[0]["gate_strength"] = "wiki"
    register.standing[0]["verified_against"] = "a_guess"
    results = run_rules(register, TODAY)
    for fragment in (
        "Governance is one of", "Access is one of", "certification source is a closed field",
        "gate's strength is a closed field", "verified against is a closed field",
    ):
        r = _rule(results, fragment)
        assert not r.passed and r.severity == "error" and r.actual == 1


def test_a_read_document_without_a_measured_digest_is_an_error(repo: Path) -> None:
    register = load_register(repo)
    register.standing[0]["text_sha256"] = None
    r = _rule(run_rules(register, TODAY), "measured text digest")
    assert not r.passed and r.severity == "error"


def test_an_overdue_review_is_a_warning_and_the_calendar_is_a_parameter(repo: Path) -> None:
    register = load_register(repo)
    on_time = _rule(run_rules(register, TODAY), "past its review date")
    assert on_time.passed and on_time.severity == "warn"
    overdue = _rule(run_rules(register, date(2027, 10, 18)), "past its review date")
    assert not overdue.passed and overdue.severity == "warn" and overdue.actual == 1


def test_the_binding_rules_catch_an_orphan_and_an_empty_anchor(repo: Path) -> None:
    register = load_register(repo)
    register.bindings.append(binding_row(document_id="ghost"))
    register.bindings.append(binding_row(column_name="carrier", anchor="   "))
    results = run_rules(register, TODAY)
    assert _rule(results, "rests on a standing row").actual == 1
    assert _rule(results, "anchor is never empty").actual == 1


# ---------------------------------------------------------------- the committed register


def test_the_committed_register_conforms_and_every_row_is_in_sync() -> None:
    # Every in_repo row's recorded digest matches the committed text under the
    # running extractor, so the pull request that edits a committed document
    # refreshes its standing row (docs/documents.md, "The states"). Loops over
    # the rows, so the next binding needs no change here.
    register = load_register(REPO)
    assert register.standing, "the committed register carries at least the demo's row"
    assert all(r.passed for r in run_rules(register, TODAY))
    reports = {r.document_id: r for r in derive(REPO, register, TODAY)}
    for row in register.standing:
        report = reports[row["document_id"]]
        if row["access"] == "in_repo":
            assert report.state == "in_sync", (row["document_id"], report.state, report.detail)
            assert report.flags == [], (row["document_id"], report.flags)
            assert report.text_sha256_now == row["text_sha256"]
            assert row["extractor"] == EXTRACTOR_ID
        assert register.bindings_for(row["document_id"]), f"{row['document_id']} binds no column"


def test_the_demo_row_is_the_nycflights13_help_page() -> None:
    register = load_register(REPO)
    row = register.standing_row("nycflights13-flights-rd")
    assert row is not None
    assert (row["governance"], row["access"], row["format"]) == ("in_repo", "in_repo", "text")
    assert row["certification_source"] == "git_merge" and row["gate_strength"] == "publication_gate"
    assert row["declared_by"] == "justinrgoff"
    assert row["upstream_url"].startswith("https://raw.githubusercontent.com/tidyverse/nycflights13/df98ef215aa8216fe0838a0b8ac5bada646d814c/")
    assert row["license"].startswith("CC0")
    # Two bindings on the one anchor: the level-zero column, and the mapped
    # unified table's column that restates it (F-62), which is the column
    # the compiled context serves (Amendment AA).
    bindings = register.bindings_for("nycflights13-flights-rd")
    assert [(b["contract_id"], b["column_name"]) for b in bindings] == [
        ("silver_nyc_flights", "dep_delay_minutes"),
        ("silver_flights", "dep_delay_minutes"),
    ]
    for binding in bindings:
        assert binding["anchor"] == "Departure and arrival delays, in minutes. Negative times represent early departures/arrivals."
        assert binding["bound_by"] == "justinrgoff"


def test_every_committed_copy_matches_its_recorded_upstream_digest() -> None:
    import hashlib

    register = load_register(REPO)
    copies = [row for row in register.standing if row.get("upstream_sha256")]
    assert copies, "the demo's row records its upstream digest"
    for row in copies:
        raw = (REPO / row["location"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row["upstream_sha256"], row["document_id"]
        assert b"\r" not in raw  # LF only; .gitattributes keeps the bytes verbatim
        assert extract_path(REPO / row["location"], str(row["format"])).text_sha256 == row["text_sha256"]


def test_the_committed_register_files_are_plain_yaml() -> None:
    for name in ("standing.yaml", "bindings.yaml"):
        text = (REPO / "documents" / "register" / name).read_text(encoding="utf-8")
        assert "&id" not in text and "*id" not in text  # no anchors or aliases
        yaml.safe_load(text)
