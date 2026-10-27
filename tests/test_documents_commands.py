"""The producer commands (D-43; S37 18.4): `find`, `inspect`, `bind`, and
`verify`, on a miniature repository, through the functions and through
the CLI. Every refusal in `bind` is shown refusing; the draft lands in
the outbox and the register itself never changes; `verify` exits 1 on
what blocks a merge and 0 on what merely reports.

Keyless, no network. Every date is fixed and the root is passed in.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pytest
import yaml

from metricmine.documents import __main__ as cli
from metricmine.documents import commands
from metricmine.documents.commands import CommandError, Target, bind, find, resolve_target, verify, write_draft
from metricmine.documents.register import load_register, sha256_text
from documents_fixtures import POLICY_MD, binding_row, build_docx, policy_digest, standing_row, write_register, write_repo

TODAY = date(2026, 10, 17)
ANCHOR = "Delays are measured in minutes."
INTENT = "delay_minutes rests on the policy's delay sentence."


@pytest.fixture()
def bare(tmp_path: Path) -> Path:
    """The contracts and the document, and an empty register."""
    return write_repo(tmp_path, standing=[], bindings=[], documents={"docs/policy.md": POLICY_MD, "docs/other.md": "Other words.\n"})


@pytest.fixture()
def bound(tmp_path: Path) -> Path:
    """The policy registered and bound."""
    return write_repo(
        tmp_path,
        standing=[standing_row(text_sha256=policy_digest())],
        bindings=[binding_row()],
        documents={"docs/policy.md": POLICY_MD, "docs/other.md": "Other words.\n"},
    )


def _root(tmp_path: Path) -> Path:
    """A mapped root beside the repository, never inside it."""
    root = tmp_path.parent / f"{tmp_path.name}-root"
    root.mkdir(exist_ok=True)
    return root


def _bind(repo: Path, spec: str = "docs/policy.md", **kw) -> commands.Draft:
    register = commands.load_register_or_empty(repo)
    target = resolve_target(repo, register, spec, kw.pop("root", None), kw.pop("fmt", None))
    args = dict(contract_id="silver_demo", column_name="delay_minutes", anchor=ANCHOR, intent=INTENT, by="a.person", today=TODAY, title="Delay policy")
    args.update(kw)
    return bind(repo, register, target, **args)


# ---------------------------------------------------------------- resolution


@pytest.mark.parametrize("spec", ["/etc/hostname", "../outside.md", "~/policy.md", "docs/../../x.md"])
def test_only_repository_paths_rooted_paths_and_ids_are_opened(bare: Path, spec: str) -> None:
    with pytest.raises(CommandError, match="only a repository-relative path"):
        resolve_target(bare, None, spec, None)


def test_a_missing_repository_path_and_an_unmapped_root_are_refused(bare: Path) -> None:
    with pytest.raises(CommandError, match="no file at docs/none.md"):
        resolve_target(bare, None, "docs/none.md", None)
    with pytest.raises(CommandError, match="MM_DOCS_ROOT is not mapped"):
        resolve_target(bare, None, "${MM_DOCS_ROOT}/x.md", None)


def test_a_registered_id_resolves_to_its_location(bound: Path) -> None:
    target = resolve_target(bound, load_register(bound), "policy", None)
    assert target == Target(bound / "docs" / "policy.md", "docs/policy.md", "in_repo", "markdown", "policy")


def test_a_rooted_path_resolves_under_the_mapped_root(bare: Path, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "delay.docx").write_bytes(build_docx(body=[ANCHOR]))
    target = resolve_target(bare, None, "${MM_DOCS_ROOT}/delay.docx", root)
    assert (target.access, target.format, target.location) == ("local_path", "docx", "${MM_DOCS_ROOT}/delay.docx")


def test_an_unknown_suffix_needs_a_format(bare: Path) -> None:
    (bare / "docs" / "notes.rst").write_text("x", encoding="utf-8")
    with pytest.raises(CommandError, match="no extractor for suffix '.rst'"):
        resolve_target(bare, None, "docs/notes.rst", None)
    assert resolve_target(bare, None, "docs/notes.rst", None, "text").format == "text"
    with pytest.raises(CommandError, match="no extractor for format 'pdf'"):
        resolve_target(bare, None, "docs/notes.rst", None, "pdf")


# ---------------------------------------------------------------- find and inspect


def test_find_lists_by_name_with_digests_and_registration(bound: Path) -> None:
    out = find(bound, load_register(bound), "policy")
    assert [c.location for c in out] == ["docs/policy.md"]
    assert out[0].text_sha256 == policy_digest() and out[0].note == "registered as policy"
    everything = find(bound, load_register(bound), "")
    assert [c.location for c in everything] == ["docs/other.md", "docs/policy.md"]
    assert everything[0].note == "not registered"


def test_find_by_text_and_the_same_text_elsewhere(bound: Path) -> None:
    (bound / "docs" / "copy.md").write_text(POLICY_MD, encoding="utf-8")
    hits = find(bound, load_register(bound), "", text="measured in minutes")
    assert [c.location for c in hits] == ["docs/copy.md", "docs/policy.md"]
    assert hits[0].note == "same text as policy (registered elsewhere)"


def test_find_walks_the_mapped_root_and_skips_the_register(bound: Path, tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / "sub").mkdir()
    (root / "sub" / "policy-v2.md").write_text("Delays are measured in hours.", encoding="utf-8")
    out = find(bound, load_register(bound), "policy", root)
    assert [c.location for c in out] == ["docs/policy.md", "${MM_DOCS_ROOT}/sub/policy-v2.md"]
    assert out[1].access == "local_path"
    text = commands.render_find(out, "policy", root)
    assert "2 candidate(s) in the repository and under MM_DOCS_ROOT" in text
    assert "standing.yaml" not in commands.render_find(find(bound, load_register(bound), "yaml"), "yaml", None)


def test_inspect_prints_the_sentences_with_locators_and_context(bound: Path) -> None:
    target = resolve_target(bound, load_register(bound), "policy", None)
    text = commands.render_inspect(target, commands._extract(target), "minutes", context=1)
    assert "registered as: policy" in text and "pending_changes: no" in text
    assert "sentences containing 'minutes': 1" in text
    assert "> text, line 4 | Delays are measured in minutes." in text
    # The title carries no period, so the splitter runs it into the next sentence.
    assert "  text, line 1 | # Delay policy A flight is late when it leaves after its scheduled time." in text
    assert "  text, line 5 | Negative values are early departures." in text


# ---------------------------------------------------------------- bind: refusals


def test_bind_refuses_an_agent_or_model_as_the_binder(bare: Path) -> None:
    for name in ("silver-cleanup-proposer", "claude-sonnet-5", "claude-x"):
        with pytest.raises(CommandError, match="is not a person"):
            _bind(bare, by=name)


def test_bind_refuses_a_missing_contract_or_column(bare: Path) -> None:
    with pytest.raises(CommandError, match="no committed contract with id 'silver_ghost'"):
        _bind(bare, contract_id="silver_ghost")
    with pytest.raises(CommandError, match="carries no column 'delay'"):
        _bind(bare, column_name="delay")


def test_bind_refuses_a_quote_that_is_not_in_the_extraction(bare: Path) -> None:
    with pytest.raises(CommandError, match="the quote is not in the extraction"):
        _bind(bare, anchor="Delays are measured in hours.")


def test_bind_refuses_an_empty_intent_or_anchor_and_a_missing_title(bare: Path) -> None:
    with pytest.raises(CommandError, match="--intent is empty"):
        _bind(bare, intent="  ")
    with pytest.raises(CommandError, match="--anchor is empty"):
        _bind(bare, anchor="")
    with pytest.raises(CommandError, match="--title is required"):
        _bind(bare, title=None)


def test_bind_refuses_the_same_text_under_a_second_location(bound: Path) -> None:
    (bound / "docs" / "copy.md").write_text(POLICY_MD, encoding="utf-8")
    with pytest.raises(CommandError, match="the same text is already registered as policy at docs/policy.md"):
        _bind(bound, "docs/copy.md", column_name="carrier", title="A copy")


def test_bind_warns_on_the_same_title_with_different_text(bound: Path) -> None:
    (bound / "docs" / "v2.md").write_text(POLICY_MD.replace("minutes", "whole minutes"), encoding="utf-8")
    draft = _bind(bound, "docs/v2.md", column_name="carrier", anchor="Delays are measured in whole minutes.", title="Delay policy")
    assert any(note.startswith("warning: policy carries the same title with different text") for note in draft.notes)
    assert draft.new_document and draft.standing_row["document_id"] == "delay-policy"


def test_bind_refuses_a_taken_id_and_a_wrong_id_for_a_registered_location(bound: Path) -> None:
    (bound / "docs" / "v2.md").write_text("Delays are counted in minutes.", encoding="utf-8")
    with pytest.raises(CommandError, match="document_id 'policy' is taken"):
        _bind(bound, "docs/v2.md", anchor="Delays are counted in minutes.", document_id="policy", column_name="carrier")
    with pytest.raises(CommandError, match="is registered as policy, not 'other-id'"):
        _bind(bound, "docs/policy.md", document_id="other-id", column_name="carrier")


def test_bind_refuses_a_document_with_no_text(bare: Path) -> None:
    (bare / "docs" / "empty.docx").write_bytes(build_docx(body=[]))
    with pytest.raises(CommandError, match="no_text_layer"):
        _bind(bare, "docs/empty.docx", title="Empty")


def test_bind_refuses_a_package_the_extractor_refuses(bare: Path) -> None:
    (bare / "docs" / "bad.docx").write_bytes(b"not a zip")
    with pytest.raises(CommandError, match="refused_package"):
        _bind(bare, "docs/bad.docx", title="Bad")


# ---------------------------------------------------------------- bind: the draft


def test_bind_drafts_a_new_document_with_the_in_repo_defaults(bare: Path) -> None:
    draft = _bind(bare)
    s, b = draft.standing_row, draft.binding_row
    assert draft.new_document and not draft.replaced_binding and draft.locator == "text, line 4"
    assert (s["document_id"], s["governance"], s["access"]) == ("delay-policy", "in_repo", "in_repo")
    assert (s["certification_source"], s["gate_strength"]) == ("git_merge", "publication_gate")
    assert s["declared_by"] == "a.person" and s["declared_on"] == TODAY and s["review_by"] == date(2027, 10, 17)
    assert s["text_sha256"] == policy_digest() and s["extractor"] == "metricmine.documents@1.0.0"
    assert (s["verified_against"], s["verified_on"]) == ("location", TODAY)
    assert "upstream_url" not in s and "license" not in s
    assert b["anchor"] == ANCHOR and b["intent"] == INTENT and b["intent_sha256"] == sha256_text(INTENT)
    assert b["bound_by"] == "a.person" and b["bound_on"] == TODAY and b["locator"] == "text, line 4"


def test_bind_under_the_root_defaults_to_pinned_with_a_six_month_review(bare: Path, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "delay.docx").write_bytes(build_docx(body=[ANCHOR]))
    draft = _bind(bare, "${MM_DOCS_ROOT}/delay.docx", root=root, title="Delay (laptop)")
    s = draft.standing_row
    assert (s["governance"], s["access"], s["format"]) == ("pinned", "local_path", "docx")
    assert (s["certification_source"], s["gate_strength"]) == ("none", "none")
    assert s["review_by"] == date(2027, 4, 17)
    assert s["location"] == "${MM_DOCS_ROOT}/delay.docx"


def test_bind_takes_the_explicit_fields(bare: Path) -> None:
    draft = _bind(
        bare, document_id="pol", review_by=date(2028, 1, 1), governance="pinned", certification_source="none",
        gate_strength="none", upstream_url="https://example.invalid/p.md", upstream_sha256="ab" * 32, license="CC0", durable_id="D-1",
    )
    s = draft.standing_row
    assert s["document_id"] == "pol" and s["review_by"] == date(2028, 1, 1) and s["governance"] == "pinned"
    assert s["upstream_url"] == "https://example.invalid/p.md" and s["license"] == "CC0" and s["durable_id"] == "D-1"


def test_bind_to_a_registered_document_adds_a_binding_and_ignores_standing_flags(bound: Path) -> None:
    draft = _bind(bound, "policy", column_name="carrier", anchor="Negative values are early departures.", title="Renamed", review_by=date(2030, 1, 1))
    assert not draft.new_document and len(draft.standing) == 1 and len(draft.bindings) == 2
    assert draft.binding_row["column_name"] == "carrier" and draft.locator == "text, line 5"
    assert "--title ignored" in " ".join(draft.notes) and "--review-by ignored" in " ".join(draft.notes)


def test_bind_re_anchors_an_existing_binding(bound: Path) -> None:
    draft = _bind(bound, "policy", anchor="Negative values are early departures.")
    assert draft.replaced_binding and len(draft.bindings) == 1
    assert draft.bindings[0]["anchor"] == "Negative values are early departures."
    assert any(note.startswith("re-anchored") for note in draft.notes)


def test_bind_notes_a_document_whose_text_moved_since_certification(bound: Path) -> None:
    (bound / "docs" / "policy.md").write_text(POLICY_MD.replace("is late", "is delayed"), encoding="utf-8")
    draft = _bind(bound, "policy", column_name="carrier", anchor="Negative values are early departures.")
    assert any("differs from the standing row's recorded digest" in note for note in draft.notes)


def test_bind_notes_pending_changes_that_would_break_the_anchor(bare: Path) -> None:
    (bare / "docs" / "red.docx").write_bytes(build_docx(redline=("Delays are measured in ", "minutes", "seconds", ".")))
    draft = _bind(bare, "docs/red.docx", anchor="Delays are measured in minutes.", title="Redlined")
    assert draft.notes == ["the document holds pending changes, and accepting them would break this anchor"]


def test_write_draft_lands_in_the_outbox_and_the_register_is_unchanged(bare: Path) -> None:
    before = (bare / "documents" / "register" / "standing.yaml").read_bytes()
    draft = _bind(bare)
    out = write_draft(bare, draft)
    assert out == bare / "proposals" / "documents" / "2026-10-17_delay-policy_silver_demo.delay_minutes"
    assert sorted(p.name for p in out.iterdir()) == ["DRAFT.md", "bindings.yaml", "standing.yaml"]
    assert (bare / "documents" / "register" / "standing.yaml").read_bytes() == before
    standing = (out / "standing.yaml").read_text(encoding="utf-8")
    assert standing.startswith("# The governed documents register, standing rows (D-43)")
    assert "&id" not in standing and "declared_on: 2026-10-17" in standing
    draft_md = (out / "DRAFT.md").read_text(encoding="utf-8")
    assert "cp proposals/documents/2026-10-17_delay-policy_silver_demo.delay_minutes/standing.yaml" in draft_md
    assert f'- anchor: "{ANCHOR}"' in draft_md and f'- intent: "{INTENT}"' in draft_md
    assert "The merge is the certification." in draft_md


def test_an_applied_draft_loads_and_verifies(bare: Path) -> None:
    out = write_draft(bare, _bind(bare))
    for name in ("standing.yaml", "bindings.yaml"):
        (bare / "documents" / "register" / name).write_bytes((out / name).read_bytes())
    register = load_register(bare)
    assert register.standing[0]["document_id"] == "delay-policy"
    result = verify(bare, TODAY)
    assert result.exit_code == 0 and result.failures == []
    assert result.reports[0].state == "in_sync"


def test_the_outbox_is_fenced_to_proposals(bare: Path, tmp_path: Path) -> None:
    before = (bare / "documents" / "register" / "bindings.yaml").read_bytes()
    draft = _bind(bare)
    for bad in (bare / "documents" / "register", bare / "docs", tmp_path.parent / f"{tmp_path.name}-outside"):
        with pytest.raises(CommandError, match="is outside proposals/"):
            write_draft(bare, draft, bad)
    assert (bare / "documents" / "register" / "bindings.yaml").read_bytes() == before
    assert not (bare / "documents" / "register" / "DRAFT.md").exists()
    assert not (tmp_path.parent / f"{tmp_path.name}-outside").exists()
    out = write_draft(bare, draft, bare / "proposals" / "custom")
    assert out == bare / "proposals" / "custom" and (out / "DRAFT.md").is_file()


def test_bind_refuses_a_reading_copy_under_the_inbox(bare: Path) -> None:
    (bare / "documents" / "inbox").mkdir(parents=True)
    (bare / "documents" / "inbox" / "policy.md").write_text(POLICY_MD, encoding="utf-8")
    with pytest.raises(CommandError, match="is a reading copy under documents/inbox/") as info:
        _bind(bare, "documents/inbox/policy.md", title="Inbox copy")
    assert "verify --reading-copy" in str(info.value)
    # inspect still reads it: a reading copy is a discussion aid
    target = resolve_target(bare, None, "documents/inbox/policy.md", None)
    assert commands._extract(target).contains(ANCHOR)


@pytest.mark.skipif(os.name == "nt", reason="a symbolic link is a POSIX fixture")
def test_a_symbolic_link_in_the_outbox_never_carries_a_write_into_the_register(bound: Path) -> None:
    # F-74: before this fix a link planted in the draft directory carried
    # the draft's bindings.yaml into documents/register/bindings.yaml while
    # the command printed that the register was unchanged.
    register = load_register(bound)
    target = resolve_target(bound, register, "docs/policy.md", None)
    draft = bind(bound, register, target, "silver_demo", "carrier", "Delays are measured in minutes.", "words", "a.person", TODAY)
    out = bound / "proposals" / "documents" / "link"
    out.mkdir(parents=True)
    (out / "bindings.yaml").symlink_to(bound / "documents" / "register" / "bindings.yaml")
    before = (bound / "documents" / "register" / "bindings.yaml").read_bytes()
    with pytest.raises(CommandError, match="bindings.yaml is a symbolic link; a draft is written through no link"):
        write_draft(bound, draft, out)
    assert (bound / "documents" / "register" / "bindings.yaml").read_bytes() == before
    # bindings.yaml is the second file written; the link is found before
    # the first, so standing.yaml is not written either.
    assert sorted(p.name for p in out.iterdir()) == ["bindings.yaml"]
    # A directory link is named as a link whether it points out of the
    # outbox or within it, and a plain path out of it is named as outside.
    away = bound / "proposals" / "documents" / "away"
    away.symlink_to(bound / "documents" / "register", target_is_directory=True)
    with pytest.raises(CommandError, match="away is a symbolic link; a draft is written through no link"):
        write_draft(bound, draft, away)
    with pytest.raises(CommandError, match="is outside proposals/"):
        write_draft(bound, draft, bound / "proposals" / "documents" / ".." / ".." / "documents" / "register")
    (bound / "proposals" / "documents" / "other").mkdir()
    near = bound / "proposals" / "documents" / "near"
    near.symlink_to(bound / "proposals" / "documents" / "other", target_is_directory=True)
    with pytest.raises(CommandError, match="near is a symbolic link; a draft is written through no link"):
        write_draft(bound, draft, near)
    assert not list((bound / "proposals" / "documents" / "other").iterdir())
    with pytest.raises(CommandError, match="is proposals/ itself"):
        write_draft(bound, draft, bound / "proposals")
    assert (bound / "documents" / "register" / "bindings.yaml").read_bytes() == before


def test_a_repeated_draft_overwrites_itself(bare: Path) -> None:
    first = write_draft(bare, _bind(bare))
    second = write_draft(bare, _bind(bare))
    assert first == second and len(list((bare / "proposals" / "documents").iterdir())) == 1


# ---------------------------------------------------------------- verify


def test_verify_is_ok_on_the_bound_repository_and_renders(bound: Path) -> None:
    result = verify(bound, TODAY)
    assert result.exit_code == 0
    text = commands.render_verify(result, TODAY, None)
    assert "register: conforms to documents_register@1.0.0 (1 standing row(s), 1 binding(s))" in text
    assert "rules: 9" in text and text.count("    pass [") == 9
    assert "policy | in_sync | flags: none | verified against location" in text
    assert text.rstrip().endswith("result: OK")


def test_verify_fails_on_a_broken_anchor_in_the_repository(bound: Path) -> None:
    (bound / "docs" / "policy.md").write_text(POLICY_MD.replace("in minutes", "in seconds"), encoding="utf-8")
    result = verify(bound, TODAY)
    assert result.exit_code == 1 and result.failures == ["policy: anchor_broken: anchor missing for silver_demo.delay_minutes"]


def test_verify_fails_on_a_binding_to_a_missing_column(bound: Path) -> None:
    write_register(bound, [standing_row(text_sha256=policy_digest())], [binding_row(column_name="gone")])
    result = verify(bound, TODAY)
    assert result.exit_code == 1 and result.failures == ["policy: binding_broken:silver_demo.gone"]


def test_verify_fails_on_a_nonconforming_register_or_a_missing_contract(bound: Path, tmp_path: Path) -> None:
    write_register(bound, [standing_row(text_sha256=policy_digest(), declared_by="claude-opus-5")], [])
    result = verify(bound, TODAY)
    assert result.exit_code == 1 and result.failures[0].startswith("register does not conform:")
    empty = tmp_path / "empty"
    empty.mkdir()
    assert verify(empty, TODAY).failures == ["no register contract at contracts/documents_register.odcs.yaml"]


def test_verify_fails_on_an_error_rule_and_only_reports_a_warning(bound: Path) -> None:
    write_register(bound, [standing_row(text_sha256=None, access="in_repo")], [binding_row()])
    result = verify(bound, TODAY)
    assert result.exit_code == 1 and any("measured text digest" in f for f in result.failures)
    write_register(bound, [standing_row(text_sha256=policy_digest(), review_by=date(2020, 1, 1))], [binding_row()])
    result = verify(bound, TODAY)
    assert result.exit_code == 0
    assert "WARN [warn]" in commands.render_verify(result, TODAY, None)
    assert result.reports[0].flags == ["review_overdue (review_by 2020-01-01)"]


def test_a_broken_anchor_on_a_local_path_document_reports_and_does_not_fail(bound: Path, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "policy.md").write_text(POLICY_MD.replace("in minutes", "in seconds"), encoding="utf-8")
    write_register(bound, [standing_row(access="local_path", governance="pinned", location="${MM_DOCS_ROOT}/policy.md", text_sha256=policy_digest())], [binding_row()])
    result = verify(bound, TODAY, root)
    assert result.reports[0].state == "anchor_broken" and result.exit_code == 0


def test_verify_with_a_reading_copy(bound: Path) -> None:
    write_register(bound, [standing_row(access="pointer_only", governance="platform_governed", certification_source="platform_approval",
                                        location="https://example.invalid/d", text_sha256=None)], [binding_row()])
    (bound / "documents" / "inbox").mkdir()
    (bound / "documents" / "inbox" / "d.md").write_text(POLICY_MD, encoding="utf-8")
    copies = commands.parse_reading_copies(bound, ["policy=documents/inbox/d.md"])
    result = verify(bound, TODAY, None, copies)
    assert result.reports[0].verified_against == "reading_copy" and result.reports[0].state == "changed_anchors_intact"
    for bad in ("policy", "policy=/abs/d.md", "policy=../d.md", "policy=documents/inbox/none.md"):
        with pytest.raises(CommandError):
            commands.parse_reading_copies(bound, [bad])


# ---------------------------------------------------------------- the CLI


def test_cli_find_inspect_bind_verify(bare: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MM_DOCS_ROOT", raising=False)
    assert cli.main(["--repo", str(bare), "find", "policy"]) == 0
    assert "docs/policy.md | in_repo | markdown" in capsys.readouterr().out
    assert cli.main(["--repo", str(bare), "inspect", "docs/policy.md", "--grep", "minutes"]) == 0
    assert "> text, line 4 | Delays are measured in minutes." in capsys.readouterr().out
    code = cli.main([
        "--repo", str(bare), "bind", "docs/policy.md", "--contract", "silver_demo", "--column", "delay_minutes",
        "--anchor", ANCHOR, "--intent", INTENT, "--by", "a.person", "--today", "2026-10-17", "--title", "Delay policy",
    ])
    out = capsys.readouterr().out
    assert code == 0 and "wrote proposals/documents/2026-10-17_delay-policy_silver_demo.delay_minutes/" in out
    assert "the register is unchanged" in out
    assert cli.main(["--repo", str(bare), "verify", "--today", "2026-10-17"]) == 0
    assert "documents: 0" in capsys.readouterr().out


def test_cli_outbox_outside_proposals_is_refused_and_the_register_untouched(bound: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MM_DOCS_ROOT", raising=False)
    before = (bound / "documents" / "register" / "bindings.yaml").read_bytes()
    code = cli.main([
        "--repo", str(bound), "bind", "policy", "--contract", "silver_demo", "--column", "delay_minutes",
        "--anchor", "Negative values are early departures.", "--intent", INTENT, "--by", "a.person", "--today", "2026-10-17",
        "--outbox", "documents/register",
    ])
    captured = capsys.readouterr()
    assert code == 2 and "is outside proposals/" in captured.err and captured.out == ""
    assert (bound / "documents" / "register" / "bindings.yaml").read_bytes() == before
    assert not (bound / "documents" / "register" / "DRAFT.md").exists()


def test_cli_a_bad_today_is_a_usage_error(bare: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        cli.main(["--repo", str(bare), "verify", "--today", "garbage"])
    assert info.value.code == 2
    assert "not a date (YYYY-MM-DD): 'garbage'" in capsys.readouterr().err


def test_the_default_day_is_utc_like_the_scan() -> None:
    from datetime import datetime, timezone

    before = datetime.now(timezone.utc).date()
    measured = cli._today(None)
    after = datetime.now(timezone.utc).date()
    assert measured in {before, after}  # the two reads may straddle a UTC midnight
    assert cli._today(date(2026, 1, 1)) == date(2026, 1, 1)


def test_cli_refusals_exit_2_on_stderr(bare: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MM_DOCS_ROOT", raising=False)
    code = cli.main([
        "--repo", str(bare), "bind", "docs/policy.md", "--contract", "silver_demo", "--column", "delay_minutes",
        "--anchor", ANCHOR, "--intent", INTENT, "--by", "claude-sonnet-5", "--today", "2026-10-17", "--title", "T",
    ])
    captured = capsys.readouterr()
    assert code == 2 and captured.out == "" and "refused: --by 'claude-sonnet-5' is not a person" in captured.err
    assert cli.main(["--repo", str(bare), "inspect", "/etc/hostname"]) == 2
    assert "only a repository-relative path" in capsys.readouterr().err


def test_cli_verify_exits_1_on_a_failure(bound: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MM_DOCS_ROOT", raising=False)
    (bound / "docs" / "policy.md").write_text(POLICY_MD.replace("in minutes", "in seconds"), encoding="utf-8")
    assert cli.main(["--repo", str(bound), "verify", "--today", "2026-10-17"]) == 1
    assert "result: FAIL" in capsys.readouterr().out


def test_cli_reads_the_root_from_the_environment(bare: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root(tmp_path)
    (root / "delay.md").write_text(POLICY_MD, encoding="utf-8")
    monkeypatch.setenv("MM_DOCS_ROOT", str(root))
    assert cli.main(["--repo", str(bare), "find", "delay"]) == 0
    out = capsys.readouterr().out
    assert "1 candidate(s) in the repository and under MM_DOCS_ROOT" in out
    assert "${MM_DOCS_ROOT}/delay.md | local_path | markdown" in out


def test_the_cli_help_names_the_boundary() -> None:
    text = " ".join(cli.build_parser().format_help().split())
    assert "never an agent" in text and "never writes the register" in text


def test_the_draft_yaml_round_trips_dates(bare: Path) -> None:
    out = write_draft(bare, _bind(bare))
    standing = yaml.safe_load((out / "standing.yaml").read_text(encoding="utf-8"))["documents"][0]
    assert standing["declared_on"] == TODAY and standing["review_by"] == date(2027, 10, 17)
