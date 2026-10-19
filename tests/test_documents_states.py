"""The derived document states (D-43; D-35 as amended by Amendment Z):
every word of the vocabulary produced on a miniature repository, each
flag, the anchor's blind spot as a documented limit, and the two branch
edits of the smallest slice on the committed document: an edit elsewhere
reads `changed_anchors_intact`, an edit to the quoted sentence reads
`anchor_broken`.

Keyless, no network. Every date is fixed; the root is passed in, never
read from the machine's environment.
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from metricmine.documents import states
from metricmine.documents.extract import EXTRACTOR_ID
from metricmine.documents.register import Register, load_register
from metricmine.documents.states import CONTENT_STATES, FLAGS, counts, derive, documents_section, plan_rows, resolve_location
from documents_fixtures import POLICY_MD, binding_row, build_docx, policy_digest, standing_row, write_register, write_repo

REPO = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 17)
ANCHOR = "Delays are measured in minutes."


def _one(repo: Path, today: date = TODAY, root: Path | None = None, copies=None):
    register = load_register(repo)
    reports = derive(repo, register, today, root, copies)
    return reports[0]


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    return write_repo(
        tmp_path,
        standing=[standing_row(text_sha256=policy_digest())],
        bindings=[binding_row()],
        documents={"docs/policy.md": POLICY_MD},
    )


# ---------------------------------------------------------------- the content states


def test_in_sync(repo: Path) -> None:
    r = _one(repo)
    assert (r.state, r.flags, r.verified_against) == ("in_sync", [], "location")
    assert r.next_command == "none"


def test_changed_anchors_intact_names_the_new_digest(repo: Path) -> None:
    (repo / "docs" / "policy.md").write_text(POLICY_MD.replace("is late", "is delayed"), encoding="utf-8")
    r = _one(repo)
    assert r.state == "changed_anchors_intact" and r.flags == []
    assert r.text_sha256_now != policy_digest()
    assert r.detail == f"text digest changed to {r.text_sha256_now}; every anchor present"
    assert r.next_command.startswith("none for the bindings")
    assert "refreshes the standing row" in r.next_command


def test_anchor_broken_names_the_binding(repo: Path) -> None:
    (repo / "docs" / "policy.md").write_text(POLICY_MD.replace("in minutes", "in seconds"), encoding="utf-8")
    r = _one(repo)
    assert r.state == "anchor_broken"
    assert "silver_demo.delay_minutes" in r.detail
    assert "re-anchor with the bind command" in r.next_command


def test_a_punctuation_edit_inside_the_quote_reads_broken(repo: Path) -> None:
    # A false alarm in the safe direction (F-71): the quote is matched verbatim
    # after whitespace and NFKC normalization, and punctuation is part of it.
    (repo / "docs" / "policy.md").write_text(POLICY_MD.replace("in minutes.", "in minutes;"), encoding="utf-8")
    assert _one(repo).state == "anchor_broken"


def test_the_next_command_follows_what_blocks_the_merge(repo: Path) -> None:
    (repo / "docs" / "policy.md").write_text(POLICY_MD.replace("in minutes", "in seconds"), encoding="utf-8")
    write_register(repo, [standing_row(text_sha256=policy_digest(), review_by=date(2020, 1, 1))], [binding_row(), binding_row(column_name="gone")])
    r = _one(repo)
    assert r.state == "anchor_broken"
    assert any(f.startswith("review_overdue") for f in r.flags) and any(f.startswith("binding_broken") for f in r.flags)
    assert r.next_command.startswith("read the pair")  # the anchor first
    (repo / "docs" / "policy.md").write_text(POLICY_MD, encoding="utf-8")
    r = _one(repo)
    assert r.state == "in_sync" and r.next_command.startswith("amend the binding by pull request")  # then the binding


def test_a_rewrapped_document_is_in_sync_under_text_identity(repo: Path) -> None:
    # Whitespace is normalized before the digest, so a re-wrap changes the
    # bytes and neither the identity nor the anchor: in_sync, not even
    # changed_anchors_intact.
    (repo / "docs" / "policy.md").write_text(POLICY_MD.replace("Delays are measured in minutes.", "Delays are\nmeasured   in minutes."), encoding="utf-8")
    assert _one(repo).state == "in_sync"


def test_the_anchors_blind_spot_is_a_documented_limit(repo: Path) -> None:
    # An untouched quote beside a new sentence that contradicts it reads as
    # intact (S37 7.11). The expiry is what forces a whole-document read.
    (repo / "docs" / "policy.md").write_text(POLICY_MD + "Delays are reported in whole hours from 2027.\n", encoding="utf-8")
    assert _one(repo).state == "changed_anchors_intact"


def test_unreachable_when_the_file_is_missing(repo: Path) -> None:
    (repo / "docs" / "policy.md").unlink()
    r = _one(repo)
    assert r.state == "unreachable" and "no file at docs/policy.md" in r.detail
    assert r.text_sha256_now is None and r.verified_against == "none"


def test_unreachable_when_the_root_is_not_mapped_and_blocks_nothing(repo: Path) -> None:
    write_register(repo, [standing_row(access="local_path", governance="pinned", location="${MM_DOCS_ROOT}/policies/policy.md", text_sha256=policy_digest())], [binding_row()])
    r = _one(repo, root=None)
    assert r.state == "unreachable" and "MM_DOCS_ROOT is not mapped" in r.detail
    assert r.next_command.startswith("map MM_DOCS_ROOT")


def test_local_path_reads_under_the_mapped_root(repo: Path, tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "policies").mkdir(parents=True)
    (root / "policies" / "policy.md").write_text(POLICY_MD, encoding="utf-8")
    write_register(repo, [standing_row(access="local_path", governance="pinned", location="${MM_DOCS_ROOT}/policies/policy.md", text_sha256=policy_digest())], [binding_row()])
    assert _one(repo, root=root).state == "in_sync"


def test_a_path_that_escapes_its_root_is_never_opened(repo: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text(POLICY_MD, encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    for access, location in (("in_repo", "../outside.md"), ("local_path", "${MM_DOCS_ROOT}/../outside.md")):
        row = {"access": access, "location": location}
        path, reason = resolve_location(repo, row, root)
        assert path is None and "escapes" in reason


def test_a_local_path_location_must_carry_the_root_token(repo: Path, tmp_path: Path) -> None:
    path, reason = resolve_location(repo, {"access": "local_path", "location": "/Users/someone/policy.md"}, tmp_path)
    assert path is None and "must start with ${MM_DOCS_ROOT}/" in reason


def test_unverified_pointer_for_public_and_pointer_only(repo: Path) -> None:
    for access in ("public", "pointer_only"):
        write_register(
            repo,
            [standing_row(access=access, governance="platform_governed", certification_source="platform_approval",
                          location="https://example.invalid/policies/delay", text_sha256=None)],
            [binding_row()],
        )
        r = _one(repo)
        assert r.state == "unverified_pointer" and r.verified_against == "none"
        assert f"a {access} location is never opened" in r.detail
        assert "reading-copy" in r.next_command


def test_a_reading_copy_verifies_anchors_and_is_named_as_such(repo: Path, tmp_path: Path) -> None:
    write_register(
        repo,
        [standing_row(access="pointer_only", governance="platform_governed", certification_source="platform_approval",
                      location="https://example.invalid/policies/delay", text_sha256=None)],
        [binding_row()],
    )
    copy = tmp_path / "inbox" / "delay.md"
    copy.parent.mkdir()
    copy.write_text(POLICY_MD, encoding="utf-8")
    r = _one(repo, copies={"policy": copy})
    assert r.state == "changed_anchors_intact"  # no digest was ever measured for the pointer
    assert r.detail.startswith("no recorded digest to compare")
    assert r.verified_against == "reading_copy"
    assert r.text_sha256_now == policy_digest()


def test_unsupported_format(repo: Path) -> None:
    (repo / "docs" / "policy.pdf").write_bytes(b"%PDF-1.7")
    write_register(repo, [standing_row(format="pdf", location="docs/policy.pdf", text_sha256="0" * 64)], [binding_row()])
    r = _one(repo)
    assert r.state == "unsupported_format" and "no extractor for 'pdf'" in r.detail


def test_refused_package(repo: Path) -> None:
    (repo / "docs" / "policy.docx").write_bytes(b"not a zip")
    write_register(repo, [standing_row(format="docx", location="docs/policy.docx", text_sha256="0" * 64)], [binding_row()])
    r = _one(repo)
    assert r.state == "refused_package" and "not a zip package" in r.detail


def test_an_os_read_failure_is_unreachable_not_a_crash(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(path, fmt):  # noqa: ANN001
        raise PermissionError(13, "Permission denied", str(path))

    monkeypatch.setattr(states, "extract_path", refuse)
    r = _one(repo)
    assert r.state == "unreachable" and "PermissionError" in r.detail and r.verified_against == "none"


def test_no_text_layer(repo: Path) -> None:
    (repo / "docs" / "empty.docx").write_bytes(build_docx(body=[]))
    write_register(repo, [standing_row(format="docx", location="docs/empty.docx", text_sha256="0" * 64)], [binding_row()])
    r = _one(repo)
    assert r.state == "no_text_layer" and r.text_sha256_now is None
    assert "nothing can be checked" in r.next_command


# ---------------------------------------------------------------- the flags


def test_review_overdue_is_a_flag_with_its_own_next_command(repo: Path) -> None:
    on_time = _one(repo, today=date(2027, 10, 17))
    assert on_time.flags == []
    overdue = _one(repo, today=date(2027, 10, 18))
    assert overdue.state == "in_sync"
    assert overdue.flags == ["review_overdue (review_by 2027-10-17)"]
    assert overdue.next_command.startswith("re-certify by pull request")


def test_binding_broken_for_a_missing_column_or_contract(repo: Path) -> None:
    write_register(repo, [standing_row(text_sha256=policy_digest())], [binding_row(column_name="gone"), binding_row(contract_id="silver_ghost")])
    r = _one(repo)
    assert r.state == "in_sync"
    assert r.flags == ["binding_broken:silver_demo.gone", "binding_broken:silver_ghost.delay_minutes"]
    assert r.next_command.startswith("amend the binding by pull request")


def test_pending_changes_names_what_an_acceptance_would_break(repo: Path) -> None:
    (repo / "docs" / "policy.docx").write_bytes(
        build_docx(redline=("Delays are measured in ", "minutes", "seconds", ". Negative values are early."))
    )
    write_register(repo, [standing_row(format="docx", location="docs/policy.docx", text_sha256="0" * 64)], [binding_row()])
    r = _one(repo)
    assert r.state == "changed_anchors_intact"  # the standing text still carries the quote
    assert r.flags == ["pending_changes (accepting them breaks: silver_demo.delay_minutes)"]


def test_pending_changes_elsewhere_touch_no_anchor(repo: Path) -> None:
    (repo / "docs" / "policy.docx").write_bytes(
        build_docx(body=[ANCHOR], redline=("Colour ", "grey", "gray", " is fine."))
    )
    write_register(repo, [standing_row(format="docx", location="docs/policy.docx", text_sha256="0" * 64)], [binding_row()])
    assert _one(repo).flags == ["pending_changes (no anchor touched)"]


def test_extractor_changed_is_flagged_and_anchors_are_still_checked(repo: Path) -> None:
    write_register(repo, [standing_row(text_sha256=policy_digest(), extractor="metricmine.documents@0.9.0")], [binding_row()])
    r = _one(repo)
    assert r.state == "in_sync"
    assert r.flags == [f"extractor_changed (metricmine.documents@0.9.0 recorded, {EXTRACTOR_ID} running)"]


# ---------------------------------------------------------------- the vocabulary, counts, and the plan shape


def test_the_vocabulary_is_fixed() -> None:
    assert CONTENT_STATES == (
        "in_sync", "changed_anchors_intact", "anchor_broken", "unreachable",
        "unverified_pointer", "unsupported_format", "refused_package", "no_text_layer",
    )
    assert FLAGS == ("review_overdue", "pending_changes", "binding_broken", "extractor_changed")
    assert "document_moved" not in CONTENT_STATES  # EV 8's name is retired: text identity replaces it
    assert set(states._NEXT) == set(CONTENT_STATES)


def test_counts_follow_the_fixed_order_and_drop_zeros(repo: Path) -> None:
    (repo / "docs" / "two.md").write_text("Other text.", encoding="utf-8")
    write_register(
        repo,
        [
            standing_row(text_sha256=policy_digest()),
            standing_row(document_id="two", title="Two", location="docs/two.md", text_sha256="0" * 64, review_by=date(2020, 1, 1)),
            standing_row(document_id="three", title="Three", location="docs/missing.md", text_sha256="0" * 64),
        ],
        [binding_row()],
    )
    reports = derive(repo, load_register(repo), TODAY)
    assert counts(reports) == {"in_sync": 1, "changed_anchors_intact": 1, "unreachable": 1, "review_overdue": 1}
    rows = plan_rows(reports)
    json.dumps(rows)
    assert [row["document_id"] for row in rows] == ["policy", "two", "three"]
    assert set(rows[0]) == {"document_id", "title", "governance", "access", "location", "state", "detail", "flags",
                            "text_sha256_now", "verified_against", "next_command"}


def test_documents_section_reports_and_never_raises(repo: Path, tmp_path: Path) -> None:
    section = documents_section(repo, TODAY)
    assert section["register"] == "conforms" and section["counts"] == {"in_sync": 1}
    assert section["items"][0]["document_id"] == "policy"
    write_register(repo, [standing_row(text_sha256=policy_digest(), declared_by="claude-sonnet-5")], [])
    bad = documents_section(repo, TODAY)
    assert bad["register"] == "nonconforming" and "is not a person" in bad["detail"] and bad["items"] == []
    empty = tmp_path / "bare"
    empty.mkdir()
    absent = documents_section(empty, TODAY)
    assert absent["register"] == "absent" and absent["items"] == []


def test_derive_never_opens_a_public_url(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def refuse(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("the documents module opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    write_register(repo, [standing_row(access="public", governance="pinned", certification_source="none", gate_strength="none",
                                       location="https://raw.githubusercontent.com/x/y/z/README.md", text_sha256=None)], [binding_row()])
    assert _one(repo).state == "unverified_pointer"


# ---------------------------------------------------------------- the smallest slice, on the committed document


def test_the_two_branch_edits_on_the_committed_document(tmp_path: Path) -> None:
    register = load_register(REPO)
    (row,) = register.standing
    source = REPO / row["location"]
    repo = tmp_path
    (repo / "contracts").mkdir()
    for name in ("documents_register.odcs.yaml", "silver_nyc_flights.odcs.yaml"):
        shutil.copy(REPO / "contracts" / name, repo / "contracts" / name)
    shutil.copytree(REPO / "documents", repo / "documents")
    local = repo / row["location"]
    assert derive(repo, load_register(repo), TODAY)[0].state == "in_sync"
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    # An edit elsewhere (line 10, the date line) reads changed_anchors_intact.
    elsewhere = list(lines)
    assert "Date of departure." in elsewhere[9]
    elsewhere[9] = elsewhere[9].replace("Date of departure.", "Date of departure (local).")
    local.write_text("".join(elsewhere), encoding="utf-8")
    assert derive(repo, load_register(repo), TODAY)[0].state == "changed_anchors_intact"
    # An edit to the quoted sentence (line 13) reads anchor_broken.
    sentence = list(lines)
    assert "in minutes" in sentence[12]
    sentence[12] = sentence[12].replace("in minutes", "in seconds")
    local.write_text("".join(sentence), encoding="utf-8")
    broken = derive(repo, load_register(repo), TODAY)[0]
    assert broken.state == "anchor_broken" and "silver_nyc_flights.dep_delay_minutes" in broken.detail


def test_states_module_exports_a_register_free_entry_for_the_scan(repo: Path) -> None:
    # derive() takes any Register-shaped object: the scan and verify share it.
    register = Register(contract=None, standing=load_register(repo).standing, bindings=load_register(repo).bindings)  # type: ignore[arg-type]
    assert derive(repo, register, TODAY)[0].state == "in_sync"
