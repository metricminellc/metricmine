"""The producer commands: find, inspect, bind, verify (D-43; S37 18.4).

Deterministic code a person runs at a terminal, or a coding host runs in
its shell and reads. No model call, no network, no MCP tool. The commands
open a document only where the states module allows: a repository path,
a rooted path under MM_DOCS_ROOT, or a reading copy the person names.

- `find` lists candidate documents by file name, and by text when asked,
  with their locations and text digests, and says which are registered.
- `inspect` prints a document's parts, its text digest, whether it holds
  pending changes, and with `--grep` the sentences that contain a word,
  each with its locator, so a quote is chosen and never reproduced from
  memory (S37 17.2).
- `bind` drafts a binding into the outbox and never writes the register.
  Code refuses what it can check (HW-25: a narrowing is never enabled by
  what an agent can supply alone): the column must exist in a committed
  contract, the quote must be in the extraction, the same text may not
  be registered under a second location, and the binder must be a
  person. The same title with different text is a warning. The person's
  intent is recorded verbatim and hashed (the Amendment I pattern).
- `verify` holds the register to its contract, runs the contract's rules,
  derives every state, and exits nonzero on an integrity failure, a
  failing error-severity rule, a broken anchor on an in-repository
  document, or a binding to a column no contract carries.

Consent in chat is permission to draft, never certification (design rule
3): what a person approves into the record is the draft this module
renders, merged by pull request.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

import yaml

from metricmine.documents.extract import EXTRACTOR_ID, FORMATS, Extraction, RefusedPackage, extract_path, normalize
from metricmine.documents.register import (
    BINDINGS_FILE,
    CONTRACT_PATH,
    REGISTER_DIR,
    STANDING_FILE,
    Register,
    RegisterError,
    integrity_problems,
    is_person,
    load_register,
    run_rules,
    sha256_text,
)
from metricmine.documents.states import (
    ROOT_ENV_VAR,
    ROOT_TOKEN,
    DocumentReport,
    contracts_index,
    derive,
    mapped_root,
    resolve_location,
)

OUTBOX = Path("proposals") / "documents"
INBOX = Path("documents") / "inbox"  # gitignored; a reading copy's staging place, never a record

FORMAT_BY_SUFFIX = {
    ".txt": "text",
    ".text": "text",
    ".rd": "text",  # R documentation markup, read as text (the demo's document)
    ".md": "markdown",
    ".markdown": "markdown",
    ".docx": "docx",
    ".pptx": "pptx",
}

# What `find` never walks in the repository: tooling and outputs by name,
# the vendored dbt package, and the register itself (its rows are not
# documents). A staged prep folder (prep-*) is skipped too.
_SKIP_NAMES = {".git", ".venv", ".adbc", "node_modules", "proposals", "warehouse", "__pycache__"}
_SKIP_RELATIVE = {Path("transform") / "vendor", REGISTER_DIR}

REVIEW_DEFAULT_DAYS = {"in_repo": 365, "local_path": 182}


class CommandError(Exception):
    """A refusal: the command stops before it writes; the message names why."""


@dataclass(frozen=True)
class Target:
    """A document the commands may open: the file, the location string the
    register stores, the access class that string implies, the format,
    and the document_id when the register already carries it."""

    path: Path
    location: str
    access: str
    format: str
    document_id: str | None = None


# ---------------------------------------------------------------- resolution


def format_for(path: Path, override: str | None = None) -> str:
    if override:
        if override not in FORMATS:
            raise CommandError(f"no extractor for format {override!r}; this slice reads {', '.join(FORMATS)}")
        return override
    fmt = FORMAT_BY_SUFFIX.get(path.suffix.lower())
    if fmt is None:
        raise CommandError(f"{path.name}: no extractor for suffix {path.suffix!r}; pass --format, or stage a supported copy")
    return fmt


def load_register_or_empty(repo: Path) -> Register | None:
    """The register when the tree carries its contract, else None. A
    nonconforming register is an error here: the commands never guess."""
    if not (repo / CONTRACT_PATH).is_file():
        return None
    return load_register(repo)


def resolve_target(repo: Path, register: Register | None, spec: str, root: Path | None,
                   fmt: str | None = None) -> Target:
    """`spec` is a registered document_id, a rooted path (${MM_DOCS_ROOT}/...),
    or a repository-relative path. Nothing else is opened."""
    if register is not None:
        row = register.standing_row(spec)
        if row is not None:
            path, how = resolve_location(repo, row, root)
            if path is None:
                raise CommandError(f"{spec}: {how}")
            return Target(path, str(row["location"]), row["access"], format_for(path, fmt or row.get("format")), spec)
    if spec.startswith(ROOT_TOKEN):
        row = {"access": "local_path", "location": spec}
        path, how = resolve_location(repo, row, root)
        if path is None:
            raise CommandError(f"{spec}: {how}")
        return Target(path, spec, "local_path", format_for(path, fmt), _registered_as(register, spec))
    pure = PurePosixPath(spec.replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts or spec.startswith("~"):
        raise CommandError(f"{spec}: only a repository-relative path, a rooted path under {ROOT_TOKEN}, or a registered document id is opened")
    location = pure.as_posix()
    row = {"access": "in_repo", "location": location}
    path, how = resolve_location(repo, row, root)
    if path is None:
        raise CommandError(f"{spec}: {how}")
    return Target(path, location, "in_repo", format_for(path, fmt), _registered_as(register, location))


def _registered_as(register: Register | None, location: str) -> str | None:
    if register is None:
        return None
    for row in register.standing:
        if str(row["location"]) == location:
            return row["document_id"]
    return None


def _extract(target: Target) -> Extraction:
    try:
        return extract_path(target.path, target.format)
    except RefusedPackage as exc:
        raise CommandError(f"{target.location}: refused_package: {exc}") from exc


# ---------------------------------------------------------------- find


@dataclass(frozen=True)
class Candidate:
    location: str
    access: str
    format: str | None
    text_sha256: str | None
    note: str


def _walk(base: Path, in_repo: bool) -> list[Path]:
    found: list[Path] = []
    for current, dirs, files in os.walk(base):
        rel = Path(current).relative_to(base)
        dirs[:] = sorted(
            d for d in dirs
            if d not in _SKIP_NAMES and not d.startswith(".") and not d.startswith("prep-")
            and not (in_repo and (rel / d) in _SKIP_RELATIVE)
        )
        for name in sorted(files):
            found.append(Path(current) / name)
    return found


def find(repo: Path, register: Register | None, query: str, root: Path | None = None,
         text: str | None = None) -> list[Candidate]:
    """Candidates whose file name contains `query` (case-insensitive) in
    the repository and under the mapped root; with `text`, only those
    whose extraction contains it. Each prints with its location, its
    format, its text digest, and whether the register knows it."""
    needle = query.lower()
    places = [(repo, "in_repo", "", True)]
    if root is not None:
        places.append((root, "local_path", ROOT_TOKEN, False))
    by_digest = {str(row.get("text_sha256")): row["document_id"] for row in (register.standing if register else [])}
    by_location = {str(row["location"]): row["document_id"] for row in (register.standing if register else [])}
    out: list[Candidate] = []
    for base, access, prefix, in_repo in places:
        for path in _walk(base, in_repo):
            fmt = FORMAT_BY_SUFFIX.get(path.suffix.lower())
            if fmt is None or (needle and needle not in path.name.lower()):
                continue
            location = prefix + path.relative_to(base).as_posix()
            try:
                extraction = extract_path(path, fmt)
            except RefusedPackage as exc:
                if text:
                    continue
                out.append(Candidate(location, access, fmt, None, f"refused_package: {exc}"))
                continue
            if text and not extraction.contains(text):
                continue
            digest = extraction.text_sha256
            if location in by_location:
                note = f"registered as {by_location[location]}"
            elif digest in by_digest:
                note = f"same text as {by_digest[digest]} (registered elsewhere)"
            else:
                note = "not registered"
            if extraction.has_pending_changes:
                note += "; pending_changes"
            out.append(Candidate(location, access, fmt, digest, note))
    return out


def render_find(candidates: list[Candidate], query: str, root: Path | None) -> str:
    lines = [
        f"find {query!r}: {len(candidates)} candidate(s)"
        + (f" in the repository and under {ROOT_ENV_VAR}" if root is not None else f" in the repository ({ROOT_ENV_VAR} not mapped)")
    ]
    for c in candidates:
        digest = c.text_sha256 or "none"
        lines.append(f"  {c.location} | {c.access} | {c.format} | {digest} | {c.note}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- inspect


def render_inspect(target: Target, extraction: Extraction, grep: str | None, limit: int = 20,
                   context: int = 0) -> str:
    lines = [
        f"document: {target.location}",
        f"access: {target.access}",
        f"format: {extraction.format}",
        f"extractor: {extraction.extractor}",
        f"text_sha256: {extraction.text_sha256}",
        f"registered as: {target.document_id or 'not registered'}",
        f"pending_changes: {'yes' if extraction.has_pending_changes else 'no'}",
        f"parts: {len(extraction.parts)}",
    ]
    for part in extraction.parts:
        lines.append(f"  {part.label}: {len(part.paragraphs)} {part.unit}(s) with text")
    sentences = extraction.sentences()
    lines.append(f"sentences: {len(sentences)}")
    if grep is not None:
        needle = normalize(grep).lower()
        hits = [i for i, (_, sentence) in enumerate(sentences) if needle in sentence.lower()]
        lines.append(f"sentences containing {grep!r}: {len(hits)}" + (f" (first {limit})" if len(hits) > limit else ""))
        for i in hits[:limit]:
            for j in range(max(0, i - context), min(len(sentences), i + context + 1)):
                locator, sentence = sentences[j]
                mark = ">" if j == i else " "
                lines.append(f"{mark} {locator} | {sentence}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- bind


@dataclass
class Draft:
    """The register as it would read after the binding: the two tables in
    full (so the draft copies onto a branch as two files), the rows the
    draft adds or replaces, the locator, and the notes a reviewer reads."""

    standing: list[dict]
    bindings: list[dict]
    standing_row: dict
    binding_row: dict
    new_document: bool
    replaced_binding: bool
    locator: str
    notes: list[str] = field(default_factory=list)


def bind(
    repo: Path,
    register: Register | None,
    target: Target,
    contract_id: str,
    column_name: str,
    anchor: str,
    intent: str,
    by: str,
    today: date,
    *,
    document_id: str | None = None,
    title: str | None = None,
    review_by: date | None = None,
    governance: str | None = None,
    certification_source: str | None = None,
    gate_strength: str | None = None,
    upstream_url: str | None = None,
    upstream_sha256: str | None = None,
    license: str | None = None,
    durable_id: str | None = None,
) -> Draft:
    """Validate, then render the draft. Raises CommandError on a refusal."""
    if not is_person(by):
        raise CommandError(f"--by {by!r} is not a person: a binder is a person, never an agent or a model (D-43)")
    if not intent.strip():
        raise CommandError("--intent is empty: the person's words are part of the record")
    if not anchor.strip():
        raise CommandError("--anchor is empty")
    index = contracts_index(repo)
    if contract_id not in index:
        raise CommandError(f"no committed contract with id {contract_id!r} under contracts/")
    if column_name not in index[contract_id]:
        raise CommandError(f"contract {contract_id} carries no column {column_name!r}")
    if target.access == "in_repo" and PurePosixPath(target.location).parts[: len(INBOX.parts)] == INBOX.parts:
        raise CommandError(
            f"{target.location} is a reading copy under {INBOX.as_posix()}/, which git never sees, so a merge"
            " could certify nothing there; declare the document's real location in standing.yaml by hand,"
            f" and check its anchors with `verify --reading-copy <id>={target.location}`"
        )
    extraction = _extract(target)
    if not extraction.text:
        raise CommandError(f"{target.location}: no_text_layer: the extraction holds no text, so no quote can be checked")
    locator = extraction.locate(anchor)
    if locator is None:
        raise CommandError(f"the quote is not in the extraction of {target.location}; take it from `inspect --grep`")
    notes: list[str] = []
    if extraction.has_pending_changes and not extraction.accepted_contains(anchor):
        notes.append("the document holds pending changes, and accepting them would break this anchor")
    elif extraction.has_pending_changes:
        notes.append("the document holds pending changes; the anchor survives their acceptance")

    standing = [dict(row) for row in (register.standing if register else [])]
    bindings = [dict(row) for row in (register.bindings if register else [])]
    digest = extraction.text_sha256
    existing = next((row for row in standing if str(row["location"]) == target.location), None)
    if target.document_id and existing is None:
        existing = next((row for row in standing if row["document_id"] == target.document_id), None)
    for row in standing:
        if row is not existing and str(row.get("text_sha256")) == digest:
            raise CommandError(
                f"the same text is already registered as {row['document_id']} at {row['location']};"
                " bind to that document instead of registering a second location"
            )
    new_document = existing is None
    if new_document:
        if not title:
            raise CommandError("--title is required for a document the register does not carry")
        document_id = document_id or _slug(title)
        if any(row["document_id"] == document_id for row in standing):
            raise CommandError(f"document_id {document_id!r} is taken; pass --document-id")
        for row in standing:
            if str(row.get("title", "")).strip().lower() == title.strip().lower():
                notes.append(f"warning: {row['document_id']} carries the same title with different text")
        standing_row = _standing_row(
            document_id, title, target, digest, today, by, review_by, governance, certification_source,
            gate_strength, upstream_url, upstream_sha256, license, durable_id,
        )
        standing.append(standing_row)
    else:
        if document_id and document_id != existing["document_id"]:
            raise CommandError(f"{target.location} is registered as {existing['document_id']}, not {document_id!r}")
        document_id = existing["document_id"]
        standing_row = existing
        for key, value in (("title", title), ("review_by", review_by)):
            if value is not None and value != existing.get(key):
                notes.append(f"--{key.replace('_', '-')} ignored: the standing row is amended by its own pull request")
        if str(existing.get("text_sha256")) != digest:
            notes.append(
                "the document's text differs from the standing row's recorded digest; the anchor was"
                " checked against the text as it reads now, and the standing row is re-verified by its"
                " own pull request"
            )
    binding_row = {
        "document_id": document_id,
        "contract_id": contract_id,
        "column_name": column_name,
        "anchor": anchor,
        "locator": locator,
        "intent": intent,
        "intent_sha256": sha256_text(intent),
        "bound_by": by,
        "bound_on": today,
    }
    key = (document_id, contract_id, column_name)
    replaced = False
    for position, row in enumerate(bindings):
        if (row["document_id"], row["contract_id"], row["column_name"]) == key:
            bindings[position] = binding_row
            replaced = True
            notes.append("re-anchored: the draft replaces the existing binding for this column")
            break
    if not replaced:
        bindings.append(binding_row)
    draft = Draft(standing, bindings, standing_row, binding_row, new_document, replaced, locator, notes)
    if register is not None:
        problems = integrity_problems(Register(register.contract, standing, bindings))
        if problems:
            raise CommandError("the draft would not pass the register's integrity checks: " + "; ".join(problems))
    return draft


def _slug(title: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "-" for ch in title.strip())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "document"


def _standing_row(document_id, title, target, digest, today, by, review_by, governance, certification_source,
                  gate_strength, upstream_url, upstream_sha256, license, durable_id) -> dict:
    if target.access == "in_repo":
        defaults = ("in_repo", "git_merge", "publication_gate")
    else:
        defaults = ("pinned", "none", "none")
    row = {
        "document_id": document_id,
        "title": title,
        "governance": governance or defaults[0],
        "access": target.access,
        "location": target.location,
        "format": target.format,
        "certification_source": certification_source or defaults[1],
        "gate_strength": gate_strength or defaults[2],
        "declared_by": by,
        "declared_on": today,
        "review_by": review_by or today + timedelta(days=REVIEW_DEFAULT_DAYS[target.access]),
        "text_sha256": digest,
        "extractor": EXTRACTOR_ID,
        "verified_against": "location",
        "verified_on": today,
    }
    for key, value in (("durable_id", durable_id), ("upstream_url", upstream_url),
                       ("upstream_sha256", upstream_sha256), ("license", license)):
        if value:
            row[key] = value
    return row


STANDING_HEADER = (
    "# The governed documents register, standing rows (D-43): one row per\n"
    "# document a person certified. Held to contracts/documents_register.odcs.yaml\n"
    "# by the documents module (verify) and the unit lane. Changes only by pull\n"
    "# request; a draft is rendered by `python -m metricmine.documents bind`.\n"
)
BINDINGS_HEADER = (
    "# The governed documents register, bindings (D-43): one row per contract\n"
    "# column that rests on a quote from a governed document. The anchor is\n"
    "# validated against the extraction at bind time and on every scan. Changes\n"
    "# only by pull request; a draft is rendered by `bind`.\n"
)


class _Dumper(yaml.SafeDumper):
    """Plain YAML: no anchors when one date object appears twice, and no
    folded scalars, so a row reads as it was typed."""

    def ignore_aliases(self, data) -> bool:  # noqa: ARG002
        return True


def render_yaml(key: str, rows: list[dict], header: str) -> str:
    body = yaml.dump({key: rows}, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=10_000)
    return header + body


class FenceError(Exception):
    """A write would leave the outbox; the message names the path."""


def fenced_dir(repo: Path, out: Path, fence: Path) -> Path:
    """`out` as a directory a draft may be written into: under `fence`
    (a folder of the gitignored outbox, never the fence itself), with no
    symbolic link on the path from the repository to it, so a link
    planted in the outbox cannot carry a write into the register or
    anywhere else (F-74). The path is read as written, before any link
    is followed, so a planted link is named as a link; a path that still
    resolves outside the fence is named as outside it. The directory is
    created. Raises FenceError, naming the path, before anything is
    written."""
    rel = fence.relative_to(repo).as_posix()
    outside = f"{out.as_posix()} is outside {rel}/; a draft lands only in the gitignored outbox, never in the register or outside the repository"
    lexical = Path(os.path.normpath(out.absolute()))
    try:
        inside = lexical.relative_to(Path(os.path.normpath(fence.absolute())))
    except ValueError:
        raise FenceError(outside) from None
    if not inside.parts:
        raise FenceError(f"{out.as_posix()} is {rel}/ itself; a draft lands in a directory of its own under it")
    probe = Path(os.path.normpath(repo.absolute()))
    for part in fence.relative_to(repo).parts + inside.parts:
        probe = probe / part
        if probe.is_symlink():
            raise FenceError(f"{probe.as_posix()} is a symbolic link; a draft is written through no link")
    try:
        out.resolve().relative_to(fence.resolve())
    except ValueError:
        raise FenceError(outside) from None
    out.mkdir(parents=True, exist_ok=True)
    return out


def check_fenced(path: Path) -> None:
    """Refuse a symbolic link where a draft file or its directory stands;
    writes nothing. A writer checks every path it will write before it
    writes the first, so a refusal leaves nothing behind (F-74)."""
    if path.is_symlink() or path.parent.is_symlink():
        raise FenceError(f"{path.as_posix()} is a symbolic link; a draft is written through no link")


def write_fenced(path: Path, text: str) -> None:
    """Write `text` to a path under a fenced directory, after the same
    check, so a link planted between the check and the write is refused
    as well. The text is written as its UTF-8 bytes, with the LF line
    endings the renderer produced, on every platform: a text-mode write
    turns each newline into CRLF on Windows, and a digest a record takes
    over the text would then not be the file's (F-75)."""
    check_fenced(path)
    path.write_bytes(text.encode("utf-8"))


def tree_digest(root: Path) -> str:
    """One sha256 over every file under `root` (its relative path and its
    bytes), so a command can check that a protected folder is unchanged
    before it says so (design rule 5: never print an assurance that was
    not checked)."""
    import hashlib

    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def write_draft(repo: Path, draft: Draft, outbox: Path | None = None) -> Path:
    """Write the two register files and a DRAFT.md into the outbox. The
    directory is named from the binding, so a repeated draft overwrites
    itself and no clock is read. The outbox is fenced to `proposals/` in
    the repository: a path anywhere else, the register's own folder
    included, is refused before anything is written, and no file is
    written through a symbolic link (F-74), so the printed assurance that
    the register is unchanged is a checked one."""
    b = draft.binding_row
    out = outbox or (repo / OUTBOX / f"{b['bound_on'].isoformat()}_{b['document_id']}_{b['contract_id']}.{b['column_name']}")
    try:
        out = fenced_dir(repo, out, repo / "proposals")
    except FenceError as exc:
        raise CommandError(f"--outbox {exc}") from exc
    files = (
        (out / STANDING_FILE, render_yaml("documents", draft.standing, STANDING_HEADER)),
        (out / BINDINGS_FILE, render_yaml("bindings", draft.bindings, BINDINGS_HEADER)),
        (out / "DRAFT.md", render_draft(repo, draft, out)),
    )
    try:
        for path, _ in files:
            check_fenced(path)
        for path, text in files:
            write_fenced(path, text)
    except FenceError as exc:
        raise CommandError(str(exc)) from exc
    return out


def render_draft(repo: Path, draft: Draft, out: Path) -> str:
    s, b = draft.standing_row, draft.binding_row
    try:
        rel = out.relative_to(repo).as_posix()
    except ValueError:
        rel = out.as_posix()
    lines = [
        "# Governed documents: a binding draft (D-43)",
        "",
        "Drafted by code from a person's words. Nothing here is certified until",
        "the register changes by pull request and the merge approves it.",
        "",
        f"- document: `{s['document_id']}` ({'new standing row' if draft.new_document else 'existing standing row'})",
        f"- title: {s.get('title', '')}",
        f"- location: `{s['location']}` (governance {s['governance']}, access {s['access']}, format {s['format']})",
        f"- certification: {s['certification_source']} ({s['gate_strength']}), review by {_iso(s.get('review_by'))}",
        f"- text_sha256: `{s.get('text_sha256')}` by {s.get('extractor')}",
        f"- binding: `{b['contract_id']}.{b['column_name']}`" + (" (re-anchored)" if draft.replaced_binding else ""),
        f"- anchor: \"{b['anchor']}\"",
        f"- locator: {b['locator']}",
        f"- intent: \"{b['intent']}\"",
        f"- intent_sha256: `{b['intent_sha256']}`",
        f"- bound by: {b['bound_by']} on {_iso(b['bound_on'])}",
        "",
        "## Notes",
        "",
    ]
    lines += [f"- {note}" for note in draft.notes] or ["- none"]
    lines += [
        "",
        "## To apply (on a branch, as a person)",
        "",
        f"    cp {rel}/{STANDING_FILE} {rel}/{BINDINGS_FILE} {REGISTER_DIR.as_posix()}/",
        "    uv run python -m metricmine.documents verify",
        "    make scan",
        "",
        "Then open the pull request. The merge is the certification.",
        "",
    ]
    return "\n".join(lines)


def _iso(value) -> str:
    return value.isoformat() if isinstance(value, date) else str(value)


# ---------------------------------------------------------------- verify


@dataclass
class Verification:
    register: Register | None
    error: str | None
    rules: list
    reports: list[DocumentReport]

    @property
    def failures(self) -> list[str]:
        out: list[str] = []
        if self.error:
            out.append(self.error)
        for result in self.rules:
            if result.severity == "error" and not result.passed:
                out.append(f"rule failed: {result.description} ({result.actual} rows, expected {result.expected})")
        for report in self.reports:
            if report.state == "anchor_broken" and report.access == "in_repo":
                out.append(f"{report.document_id}: anchor_broken: {report.detail}")
            for flag in report.flags:
                if flag.startswith("binding_broken"):
                    out.append(f"{report.document_id}: {flag}")
        return out

    @property
    def exit_code(self) -> int:
        return 1 if self.failures else 0


def verify(repo: Path, today: date, root: Path | None = None,
           reading_copies: dict[str, Path] | None = None) -> Verification:
    if not (repo / CONTRACT_PATH).is_file():
        return Verification(None, f"no register contract at {CONTRACT_PATH.as_posix()}", [], [])
    try:
        register = load_register(repo)
    except RegisterError as exc:
        return Verification(None, f"register does not conform: {exc}", [], [])
    rules = run_rules(register, today)
    reports = derive(repo, register, today, root, reading_copies)
    return Verification(register, None, rules, reports)


def render_verify(v: Verification, today: date, root: Path | None) -> str:
    lines = [f"documents verify (today {today.isoformat()}; {ROOT_ENV_VAR} {'mapped' if root is not None else 'not mapped'})"]
    if v.error:
        lines.append(f"  FAIL {v.error}")
        return "\n".join(lines) + "\n"
    assert v.register is not None
    lines.append(
        f"  register: conforms to {v.register.contract.id}@{v.register.contract.version}"
        f" ({len(v.register.standing)} standing row(s), {len(v.register.bindings)} binding(s))"
    )
    lines.append(f"  rules: {len(v.rules)}")
    for r in v.rules:
        mark = "pass" if r.passed else ("WARN" if r.severity == "warn" else "FAIL")
        lines.append(f"    {mark} [{r.severity}] {r.table}: {r.description} ({r.actual} rows, expected {r.expected})")
    lines.append(f"  documents: {len(v.reports)}")
    for rep in v.reports:
        lines.append(f"    {rep.document_id} | {rep.state} | flags: {rep.flags_text} | verified against {rep.verified_against}")
        lines.append(f"      {rep.detail}")
        lines.append(f"      next: {rep.next_command}")
    lines.append("  result: " + ("OK" if not v.failures else "FAIL"))
    for failure in v.failures:
        lines.append(f"    {failure}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- helpers for the CLI


def today_or_utc(value: date | None) -> date:
    """The day a command reasons with: `--today` when given, else the UTC
    day, as the scan uses (`datetime.now(timezone.utc).date()`)."""
    return value if value is not None else datetime.now(timezone.utc).date()


def parse_date(value: str) -> date:
    """An argparse type for `--today`: YYYY-MM-DD or a usage error."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not a date (YYYY-MM-DD): {value!r}") from exc


def parse_reading_copies(repo: Path, values: list[str]) -> dict[str, Path]:
    """`ID=PATH` pairs; the path is repository-relative or under the mapped
    root token, never anywhere else."""
    out: dict[str, Path] = {}
    root = mapped_root()
    for value in values:
        document_id, sep, spec = value.partition("=")
        if not sep or not document_id or not spec:
            raise CommandError(f"--reading-copy takes ID=PATH, got {value!r}")
        if spec.startswith(ROOT_TOKEN):
            path, how = resolve_location(repo, {"access": "local_path", "location": spec}, root)
        else:
            pure = PurePosixPath(spec.replace("\\", "/"))
            if pure.is_absolute() or ".." in pure.parts:
                raise CommandError(f"--reading-copy {spec!r}: a reading copy is staged inside the repository or under {ROOT_TOKEN}")
            path, how = resolve_location(repo, {"access": "in_repo", "location": pure.as_posix()}, root)
        if path is None:
            raise CommandError(f"--reading-copy {spec!r}: {how}")
        out[document_id] = path
    return out
