"""The change set: the closed vocabulary, its validation, its
classification, and the rendering (D-44).

A context proposal is a declared change set, a YAML file a person runs
through `python -m metricmine.meaning propose <file>`: `by` (the
person's name), `intent` (the person's words, verbatim), and `changes`,
a list in the closed vocabulary below, each with its fields and a
rationale. The file's shape is `docs/spec/meaning/change-set.schema.json`;
the checks a schema cannot express run here, in order, against a working
copy of the two registers, so a change may name a row an earlier change
in the same set added.

The vocabulary and the class of each kind, by what it re-asks of people:

| kind | register | class |
|---|---|---|
| add_term, add_synonym, remove_synonym, bind | glossary | additive |
| amend_definition, rename_term | glossary | changing |
| deprecate_term, drop_term, unbind | glossary | removing |
| add_concept, bind_concept | ontology | additive |
| amend_concept, relabel | ontology | changing |
| deprecate_concept, drop_concept, unbind_concept | ontology | removing |
| add_document, bind_document | documents | additive |
| recertify_document | documents | changing |
| unbind_document, retire_document | documents | removing |

Additive moves no existing binding's digest. Changing moves a term's or
a concept's digest, and the command re-binds every binding that cites
it under the set's intent, `by`, and day, listing each by name.
Removing is two steps: a deprecation first (additive in its mechanics
and served as declared), then a drop, refused while a binding stands,
while the row is not deprecated by an earlier merge, or, for a concept,
while a child names it as parent (HW-35, deprecate then drop).

The five document kinds (D-44; Amendment AD) take the same command,
record, and pull request. They change the governed documents register
(D-43) the way `python -m metricmine.documents bind` drafts a binding,
and they read committed files only: a document this command opens is an
`in_repo` row's committed copy, so an anchor is checked against the text
as the tree carries it; a `local_path` document is drafted at a terminal
with the documents module under the mapped root, and a binding on a
`public` or `pointer_only` one is a hand edit checked with the documents
module's `verify --reading-copy`.
`retire_document` is the second of two steps: it is refused while a
binding stood on the row when the set started (unbind, merge, then
retire, as deprecate then drop). A recertification re-measures the
committed copy's text and refuses to leave an anchor behind.

What the command never does: write under `meaning/`, `contracts/`, or
`documents/register/` (the outbox is fenced and no file is written
through a symbolic link), certify anything, relax a check, open a
location outside the repository, or re-bind a binding whose row this
set did not move (a binding already stale at the start of the set is
reported as standing drift, and an explicit `bind` re-binds it).
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path, PurePosixPath

from metricmine.documents import register as documents_register
from metricmine.documents import states as documents_states
from metricmine.documents.commands import (
    BINDINGS_HEADER as DOCUMENTS_BINDINGS_HEADER,
    FORMAT_BY_SUFFIX,
    INBOX,
    REVIEW_DEFAULT_DAYS as DOCUMENTS_REVIEW_DAYS,
    STANDING_HEADER as DOCUMENTS_STANDING_HEADER,
    FenceError,
    check_fenced,
    fenced_dir,
    render_yaml,
    write_fenced,
)
from metricmine.documents.extract import EXTRACTOR_ID, FORMATS, RefusedPackage, extract_path, normalize
from metricmine.documents.register import RegisterError, is_person, load_yaml, sha256_text
from metricmine.documents.states import contracts_index
from metricmine.meaning.register import (
    ONTOLOGY,
    MeaningRegister,
    RegisterSpec,
    integrity_problems,
    join_synonyms,
    register_digest,
    run_rules,
    split_synonyms,
)

MODULE_ID = "metricmine.meaning@1.0.0"
SCHEMA_PATH = Path("docs") / "spec" / "meaning" / "change-set.schema.json"
OUTBOX = Path("proposals") / "meaning"
REVIEW_DEFAULT_DAYS = 365
_ID = re.compile(r"^[a-z][a-z0-9_]*$")

VOCABULARY: dict[str, tuple[str, str]] = {
    "add_term": ("glossary", "additive"),
    "amend_definition": ("glossary", "changing"),
    "rename_term": ("glossary", "changing"),
    "add_synonym": ("glossary", "additive"),
    "remove_synonym": ("glossary", "additive"),
    "deprecate_term": ("glossary", "removing"),
    "drop_term": ("glossary", "removing"),
    "bind": ("glossary", "additive"),
    "unbind": ("glossary", "removing"),
    "add_concept": ("ontology", "additive"),
    "amend_concept": ("ontology", "changing"),
    "relabel": ("ontology", "changing"),
    "deprecate_concept": ("ontology", "removing"),
    "drop_concept": ("ontology", "removing"),
    "bind_concept": ("ontology", "additive"),
    "unbind_concept": ("ontology", "removing"),
    "add_document": ("documents", "additive"),
    "bind_document": ("documents", "additive"),
    "unbind_document": ("documents", "removing"),
    "recertify_document": ("documents", "changing"),
    "retire_document": ("documents", "removing"),
}
DOCUMENT_KINDS = ("add_document", "bind_document", "unbind_document", "recertify_document", "retire_document")
REGISTER_CONTRACTS = ("documents_register", "glossary_register", "ontology_register")
# The documents register's closed fields, as its contract's rules declare
# them (D-43); checked here by name so a refusal names the field, and
# held again by the contract's own rules on the rendered register.
GOVERNANCE = ("in_repo", "platform_governed", "pinned")
ACCESS = ("in_repo", "public", "local_path", "pointer_only")
CERTIFICATION_SOURCES = ("git_merge", "platform_approval", "steward_attestation", "none")
GATE_STRENGTHS = ("publication_gate", "attestation_badge", "none")
_DOCUMENT_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMON = ("kind", "rationale")
FIELDS: dict[str, tuple[str, ...]] = {
    "add_term": _COMMON + ("term_id", "term", "definition", "synonyms", "owner", "review_by"),
    "amend_definition": _COMMON + ("term_id", "definition"),
    "rename_term": _COMMON + ("term_id", "term"),
    "add_synonym": _COMMON + ("term_id", "synonym"),
    "remove_synonym": _COMMON + ("term_id", "synonym"),
    "deprecate_term": _COMMON + ("term_id", "superseded_by"),
    "drop_term": _COMMON + ("term_id",),
    "bind": _COMMON + ("term_id", "contract_id", "column_name"),
    "unbind": _COMMON + ("term_id", "contract_id", "column_name"),
    "add_concept": _COMMON + ("concept_id", "label", "parent_id", "definition", "owner", "review_by"),
    "amend_concept": _COMMON + ("concept_id", "definition", "parent_id"),
    "relabel": _COMMON + ("concept_id", "label"),
    "deprecate_concept": _COMMON + ("concept_id", "superseded_by"),
    "drop_concept": _COMMON + ("concept_id",),
    "bind_concept": _COMMON + ("concept_id", "contract_id", "column_name"),
    "unbind_concept": _COMMON + ("concept_id", "contract_id", "column_name"),
    "add_document": _COMMON + (
        "document_id", "title", "governance", "access", "location", "format", "certification_source",
        "gate_strength", "review_by", "durable_id", "approver_role", "pinned_version", "upstream_url",
        "upstream_sha256", "license", "text_sha256",
    ),
    "bind_document": _COMMON + ("document_id", "contract_id", "column_name", "anchor"),
    "unbind_document": _COMMON + ("document_id", "contract_id", "column_name"),
    "recertify_document": _COMMON + ("document_id", "pinned_version", "text_sha256", "review_by"),
    "retire_document": _COMMON + ("document_id",),
}

TERMS_HEADER = (
    "# The governed glossary register, terms (D-44): one row per business term\n"
    "# a person certified. Held to contracts/glossary_register.odcs.yaml by the\n"
    "# meaning module (verify) and the unit lane. Changes only by pull request;\n"
    "# a change set is rendered by `python -m metricmine.meaning propose`.\n"
)
GLOSSARY_BINDINGS_HEADER = (
    "# The governed glossary register, bindings (D-44): one row per contract\n"
    "# element a term labels, carrying the term's content digest as it read when\n"
    "# the binding was made. The scan reads term_changed when the digest moves.\n"
    "# Changes only by pull request; a change set is rendered by `propose`.\n"
)
CONCEPTS_HEADER = (
    "# The governed ontology register, concepts (D-44): one row per concept a\n"
    "# person certified, with its parent where one exists. Held to\n"
    "# contracts/ontology_register.odcs.yaml by the meaning module (verify) and\n"
    "# the unit lane. Changes only by pull request; a change set is rendered by\n"
    "# `python -m metricmine.meaning propose`.\n"
)
ONTOLOGY_BINDINGS_HEADER = (
    "# The governed ontology register, bindings (D-44): one row per contract\n"
    "# element a concept labels (a table's concept is its entity type), carrying\n"
    "# the concept's node digest as it read when the binding was made. Changes\n"
    "# only by pull request; a change set is rendered by `propose`.\n"
)
HEADERS = {
    ("glossary", "rows"): TERMS_HEADER,
    ("glossary", "bindings"): GLOSSARY_BINDINGS_HEADER,
    ("ontology", "rows"): CONCEPTS_HEADER,
    ("ontology", "bindings"): ONTOLOGY_BINDINGS_HEADER,
}


class ChangeError(Exception):
    """A refusal: the command stops before it writes; the message names why."""


@dataclass(frozen=True)
class ChangeSet:
    source: Path
    by: str
    intent: str
    changes: list[dict]
    raw: dict


@dataclass
class Applied:
    index: int
    kind: str
    register: str
    klass: str
    target: str
    element: str | None
    note: str


@dataclass
class Proposal:
    registers: dict[str, MeaningRegister]
    applied: list[Applied]
    rebound: list[dict]
    standing_drift: list[dict]
    before: dict[str, str]
    after: dict[str, str]
    rules: list = field(default_factory=list)
    # The governed documents register as it would read after the set, when
    # the set carries a document kind; None leaves it unrendered.
    documents: documents_register.Register | None = None


# ---------------------------------------------------------------- the file


def load_schema(repo: Path) -> dict:
    return json.loads((repo / SCHEMA_PATH).read_text(encoding="utf-8"))


def load_change_set(repo: Path, path: Path) -> ChangeSet:
    """The change-set file, validated against the committed schema."""
    if not path.is_file():
        raise ChangeError(f"no change-set file at {path.as_posix()}")
    try:
        raw = load_yaml(path)
    except RegisterError as exc:
        raise ChangeError(str(exc)) from exc
    for change in raw.get("changes") or []:
        if isinstance(change, dict) and isinstance(change.get("review_by"), date):
            change["review_by"] = change["review_by"].isoformat()  # YAML reads a bare date; the schema reads text
    import jsonschema  # the dev group's validator, as the engine's reader imports it; find, show, and verify never need it

    validator = jsonschema.Draft202012Validator(load_schema(repo))
    errors = sorted(validator.iter_errors(raw), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        where = "/".join(str(p) for p in first.absolute_path) or "the top level"
        raise ChangeError(f"{path.name} does not match the change-set schema at {where}: {first.message}")
    for index, change in enumerate(raw["changes"], 1):
        kind = str(change["kind"])
        unread = sorted(set(change) - set(FIELDS.get(kind, _COMMON)))
        if unread:
            raise ChangeError(f"change {index} ({kind}) carries fields the kind does not read: {', '.join(unread)}")
    return ChangeSet(path, str(raw["by"]), str(raw["intent"]), list(raw["changes"]), raw)


# ---------------------------------------------------------------- the working copy


class _Working:
    """A working copy of one register's rows and bindings, with the lookups
    the checks need. Rows are copied, never the loaded register's."""

    def __init__(self, register: MeaningRegister) -> None:
        self.spec: RegisterSpec = register.spec
        self.contract = register.contract
        self.rows: list[dict] = copy.deepcopy(register.rows)
        self.bindings: list[dict] = copy.deepcopy(register.bindings)
        self.start_digests: dict[str, str] = register.digests()
        self.start_status: dict[str, str] = {r[self.spec.id_field]: str(r.get("status")) for r in register.rows}
        self.touched: set[tuple[str, str, str]] = set()

    def row(self, row_id: str) -> dict | None:
        for row in self.rows:
            if row[self.spec.id_field] == row_id:
                return row
        return None

    def require(self, row_id: str, what: str) -> dict:
        row = self.row(row_id)
        if row is None:
            raise ChangeError(f"{what}: the {self.spec.kind} register carries no {self.spec.noun} {row_id!r}, and this set does not add it earlier")
        return row

    def digest(self, row: dict) -> str:
        return self.spec.digest(row)

    def binding(self, row_id: str, contract_id: str, column_name: str) -> dict | None:
        for b in self.bindings:
            if (b[self.spec.id_field], b["contract_id"], b["column_name"]) == (row_id, contract_id, column_name):
                return b
        return None

    def as_register(self) -> MeaningRegister:
        return MeaningRegister(self.spec, self.contract, self.rows, self.bindings)


def _lower(text) -> str:
    return normalize(str(text)).lower()


def _owners(working: _Working, exclude_id: str | None = None) -> dict[str, str]:
    """Every label and synonym in the glossary, lowered, to the id that owns it."""
    out: dict[str, str] = {}
    for row in working.rows:
        if row["term_id"] == exclude_id:
            continue
        out.setdefault(_lower(row["term"]), row["term_id"])
        for synonym in split_synonyms(row.get("synonyms")):
            out.setdefault(_lower(synonym), row["term_id"])
    return out


def _element(index: dict[str, set[str]], change: dict, what: str) -> tuple[str, str]:
    contract_id = str(change["contract_id"])
    column_name = str(change.get("column_name") or "")
    if contract_id in REGISTER_CONTRACTS:
        raise ChangeError(f"{what}: {contract_id} is a register, not an element a term or a concept labels")
    columns = index.get(contract_id)
    if columns is None:
        raise ChangeError(f"{what}: no committed contract with id {contract_id!r} under contracts/")
    if column_name and column_name not in columns:
        raise ChangeError(f"{what}: contract {contract_id} carries no column {column_name!r}")
    return contract_id, column_name


def _review_by(change: dict, today: date, what: str) -> date:
    value = change.get("review_by")
    if value is None:
        return today + timedelta(days=REVIEW_DEFAULT_DAYS)
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ChangeError(f"{what}: review_by {value!r} is not a date (YYYY-MM-DD)") from None


def _new_binding(spec: RegisterSpec, row_id: str, contract_id: str, column_name: str, digest: str,
                 change_set: ChangeSet, today: date) -> dict:
    return {
        spec.id_field: row_id,
        "contract_id": contract_id,
        "column_name": column_name,
        spec.digest_field: digest,
        "intent": change_set.intent,
        "intent_sha256": sha256_text(change_set.intent),
        "bound_by": change_set.by,
        "bound_on": today,
    }


# ---------------------------------------------------------------- the glossary kinds


def _add_term(w: _Working, c: dict, cs: ChangeSet, today: date, what: str) -> Applied:
    term_id = str(c["term_id"])
    if not _ID.match(term_id):
        raise ChangeError(f"{what}: term_id {term_id!r} is not lowercase letters, digits, and underscores")
    if w.row(term_id) is not None:
        raise ChangeError(f"{what}: term_id {term_id!r} is taken")
    if not is_person(str(c["owner"])):
        raise ChangeError(f"{what}: owner {c['owner']!r} is not a person or a team; an agent or a model name is refused (D-44)")
    owners = _owners(w)
    label = str(c["term"])
    if _lower(label) in owners:
        raise ChangeError(f"{what}: the label {label!r} is owned by {owners[_lower(label)]} (as a label or a synonym)")
    synonyms = split_synonyms(c.get("synonyms"))
    seen: set[str] = {_lower(label)}
    for synonym in synonyms:
        if _lower(synonym) in owners:
            raise ChangeError(f"{what}: the synonym {synonym!r} is owned by {owners[_lower(synonym)]}")
        if _lower(synonym) in seen:
            raise ChangeError(f"{what}: the synonym {synonym!r} repeats the label or another synonym of this term")
        seen.add(_lower(synonym))
    w.rows.append({
        "term_id": term_id,
        "term": label,
        "definition": str(c["definition"]),
        "synonyms": join_synonyms(synonyms),
        "owner": str(c["owner"]),
        "status": "active",
        "superseded_by": None,
        "declared_by": cs.by,
        "declared_on": today,
        "review_by": _review_by(c, today, what),
    })
    return Applied(0, "add_term", "glossary", "additive", term_id, None, f"added {label!r}")


def _amend_definition(w: _Working, c: dict, what: str) -> Applied:
    row = w.require(str(c["term_id"]), what)
    new = str(c["definition"])
    if normalize(new) == normalize(str(row["definition"])):
        raise ChangeError(f"{what}: the definition of {row['term_id']} matches the current text; nothing changes")
    row["definition"] = new
    return Applied(0, "amend_definition", "glossary", "changing", row["term_id"], None, "the definition changed; the digest moves")


def _rename_term(w: _Working, c: dict, what: str) -> Applied:
    row = w.require(str(c["term_id"]), what)
    new = str(c["term"])
    if normalize(new) == normalize(str(row["term"])):
        raise ChangeError(f"{what}: the label of {row['term_id']} already reads {row['term']!r}; nothing changes")
    owners = _owners(w, exclude_id=row["term_id"])
    if _lower(new) in owners:
        raise ChangeError(f"{what}: the label {new!r} is owned by {owners[_lower(new)]} (as a label or a synonym)")
    if _lower(new) in {_lower(s) for s in split_synonyms(row.get("synonyms"))}:
        raise ChangeError(f"{what}: {new!r} is a synonym of {row['term_id']}; remove the synonym earlier in this set")
    old = row["term"]
    row["term"] = new
    return Applied(0, "rename_term", "glossary", "changing", row["term_id"], None, f"the label {old!r} became {new!r}; the digest moves")


def _add_synonym(w: _Working, c: dict, what: str) -> Applied:
    row = w.require(str(c["term_id"]), what)
    synonym = str(c["synonym"]).strip()
    if not synonym:
        raise ChangeError(f"{what}: the synonym is empty")
    current = split_synonyms(row.get("synonyms"))
    if _lower(synonym) in {_lower(s) for s in current}:
        raise ChangeError(f"{what}: {synonym!r} is already a synonym of {row['term_id']}")
    owners = _owners(w)
    if _lower(synonym) in owners:
        raise ChangeError(f"{what}: {synonym!r} is owned by {owners[_lower(synonym)]} (as a label or a synonym)")
    row["synonyms"] = join_synonyms(current + [synonym])
    return Applied(0, "add_synonym", "glossary", "additive", row["term_id"], None, f"added the synonym {synonym!r}; never hashed, so no binding moves")


def _remove_synonym(w: _Working, c: dict, what: str) -> Applied:
    row = w.require(str(c["term_id"]), what)
    synonym = str(c["synonym"]).strip()
    current = split_synonyms(row.get("synonyms"))
    kept = [s for s in current if _lower(s) != _lower(synonym)]
    if len(kept) == len(current):
        raise ChangeError(f"{what}: {synonym!r} is not a synonym of {row['term_id']}")
    row["synonyms"] = join_synonyms(kept)
    return Applied(0, "remove_synonym", "glossary", "additive", row["term_id"], None, f"removed the synonym {synonym!r}")


def _deprecate(w: _Working, c: dict, kind: str, what: str) -> Applied:
    spec = w.spec
    row = w.require(str(c[spec.id_field]), what)
    row_id = row[spec.id_field]
    if str(row.get("status")) == "deprecated":
        raise ChangeError(f"{what}: {row_id} is already deprecated")
    successor = c.get("superseded_by")
    if successor is not None:
        successor = str(successor)
        if successor == row_id:
            raise ChangeError(f"{what}: {row_id} cannot supersede itself")
        w.require(successor, f"{what} (superseded_by)")
    row["status"] = "deprecated"
    row["superseded_by"] = successor
    note = f"deprecated, superseded by {successor}" if successor else "deprecated, no successor named"
    return Applied(0, kind, spec.kind, "removing", row_id, None, note + "; reported as declared until a later set drops it")


def _drop(w: _Working, c: dict, kind: str, what: str) -> Applied:
    spec = w.spec
    row = w.require(str(c[spec.id_field]), what)
    row_id = row[spec.id_field]
    if w.start_status.get(row_id) != "deprecated":
        if str(row.get("status")) == "deprecated":
            raise ChangeError(
                f"{what}: {row_id} is deprecated in this set; a drop is its own later set, after the deprecation"
                " has merged (HW-35, deprecate then drop)"
            )
        raise ChangeError(f"{what}: {row_id} is not deprecated; deprecate it first (HW-35, deprecate then drop)")
    standing = [b for b in w.bindings if b[spec.id_field] == row_id]
    if standing:
        elements = ", ".join(f"{b['contract_id']}.{b['column_name']}" if b["column_name"] else b["contract_id"] for b in standing)
        raise ChangeError(f"{what}: a binding stands on {row_id} ({elements}); unbind it first")
    if spec is ONTOLOGY:
        children = [r["concept_id"] for r in w.rows if r.get("parent_id") == row_id]
        if children:
            raise ChangeError(f"{what}: {', '.join(children)} names {row_id} as parent; move the children first")
    w.rows = [r for r in w.rows if r[spec.id_field] != row_id]
    return Applied(0, kind, spec.kind, "removing", row_id, None, "dropped; no binding stood")


def _bind(w: _Working, c: dict, cs: ChangeSet, today: date, index: dict[str, set[str]], kind: str, what: str) -> Applied:
    spec = w.spec
    row = w.require(str(c[spec.id_field]), what)
    row_id = row[spec.id_field]
    contract_id, column_name = _element(index, c, what)
    element = f"{contract_id}.{column_name}" if column_name else f"{contract_id} (table)"
    digest = w.digest(row)
    if spec is ONTOLOGY:
        other = next((b for b in w.bindings if (b["contract_id"], b["column_name"]) == (contract_id, column_name)
                      and b["concept_id"] != row_id), None)
        if other is not None:
            raise ChangeError(f"{what}: {element} carries the concept {other['concept_id']}; an element carries one concept, so unbind it first")
    existing = w.binding(row_id, contract_id, column_name)
    key = (row_id, contract_id, column_name)
    w.touched.add(key)
    new = _new_binding(spec, row_id, contract_id, column_name, digest, cs, today)
    note = ""
    if str(row.get("status")) == "deprecated":
        successor = row.get("superseded_by")
        note = f"; the {spec.noun} is deprecated" + (f", superseded by {successor}" if successor else "")
    if existing is not None:
        if str(existing.get(spec.digest_field)) == digest:
            raise ChangeError(f"{what}: {element} is already bound to {row_id} at its current digest; nothing changes")
        w.bindings[w.bindings.index(existing)] = new
        return Applied(0, kind, spec.kind, "changing", row_id, element, f"re-bound at the {spec.noun}'s current digest {digest[:12]}; the recorded digest moves" + note)
    w.bindings.append(new)
    return Applied(0, kind, spec.kind, "additive", row_id, element, f"bound at digest {digest[:12]}" + note)


def _unbind(w: _Working, c: dict, kind: str, what: str) -> Applied:
    spec = w.spec
    row_id = str(c[spec.id_field])
    contract_id = str(c["contract_id"])
    column_name = str(c.get("column_name") or "")
    element = f"{contract_id}.{column_name}" if column_name else f"{contract_id} (table)"
    existing = w.binding(row_id, contract_id, column_name)
    if existing is None:
        raise ChangeError(f"{what}: no binding of {row_id} on {element}")
    w.bindings.remove(existing)
    w.touched.add((row_id, contract_id, column_name))
    return Applied(0, kind, spec.kind, "removing", row_id, element, "unbound")


# ---------------------------------------------------------------- the ontology kinds


def _ancestors(w: _Working, start: str | None) -> list[str]:
    seen: list[str] = []
    current = start
    while current is not None and current not in seen:
        seen.append(current)
        row = w.row(current)
        current = row.get("parent_id") if row else None
    return seen


def _check_parent(w: _Working, concept_id: str, parent_id: str | None, what: str) -> None:
    if parent_id is None:
        return
    if parent_id == concept_id:
        raise ChangeError(f"{what}: {concept_id} cannot be its own parent")
    w.require(parent_id, f"{what} (parent_id)")
    if concept_id in _ancestors(w, parent_id):
        raise ChangeError(f"{what}: parent {parent_id} would close a cycle through {concept_id}")


def _add_concept(w: _Working, c: dict, cs: ChangeSet, today: date, what: str) -> Applied:
    concept_id = str(c["concept_id"])
    if not _ID.match(concept_id):
        raise ChangeError(f"{what}: concept_id {concept_id!r} is not lowercase letters, digits, and underscores")
    if w.row(concept_id) is not None:
        raise ChangeError(f"{what}: concept_id {concept_id!r} is taken")
    if not is_person(str(c["owner"])):
        raise ChangeError(f"{what}: owner {c['owner']!r} is not a person or a team; an agent or a model name is refused (D-44)")
    label = str(c["label"])
    for row in w.rows:
        if _lower(row["label"]) == _lower(label):
            raise ChangeError(f"{what}: the label {label!r} is owned by {row['concept_id']}")
    parent_id = str(c["parent_id"]) if c.get("parent_id") not in (None, "") else None
    _check_parent(w, concept_id, parent_id, what)
    w.rows.append({
        "concept_id": concept_id,
        "label": label,
        "parent_id": parent_id,
        "definition": str(c["definition"]),
        "owner": str(c["owner"]),
        "status": "active",
        "superseded_by": None,
        "declared_by": cs.by,
        "declared_on": today,
        "review_by": _review_by(c, today, what),
    })
    return Applied(0, "add_concept", "ontology", "additive", concept_id, None, f"added {label!r}" + (f" under {parent_id}" if parent_id else " at a root"))


def _amend_concept(w: _Working, c: dict, what: str) -> Applied:
    row = w.require(str(c["concept_id"]), what)
    notes: list[str] = []
    if "definition" in c and c["definition"] is not None:
        new = str(c["definition"])
        if normalize(new) != normalize(str(row["definition"])):
            row["definition"] = new
            notes.append("the definition changed")
    if "parent_id" in c:
        parent_id = str(c["parent_id"]) if c["parent_id"] not in (None, "") else None
        if parent_id != row.get("parent_id"):
            _check_parent(w, row["concept_id"], parent_id, what)
            old = row.get("parent_id")
            row["parent_id"] = parent_id
            notes.append(f"the parent moved from {old or 'a root'} to {parent_id or 'a root'}")
    if not notes:
        raise ChangeError(f"{what}: {row['concept_id']} already reads as amended; nothing changes")
    return Applied(0, "amend_concept", "ontology", "changing", row["concept_id"], None, "; ".join(notes) + "; the digest moves")


def _relabel(w: _Working, c: dict, what: str) -> Applied:
    row = w.require(str(c["concept_id"]), what)
    new = str(c["label"])
    if normalize(new) == normalize(str(row["label"])):
        raise ChangeError(f"{what}: the label of {row['concept_id']} already reads {row['label']!r}; nothing changes")
    for other in w.rows:
        if other is not row and _lower(other["label"]) == _lower(new):
            raise ChangeError(f"{what}: the label {new!r} is owned by {other['concept_id']}")
    old = row["label"]
    row["label"] = new
    return Applied(0, "relabel", "ontology", "changing", row["concept_id"], None, f"the label {old!r} became {new!r}; the digest moves")


# ---------------------------------------------------------------- the document kinds


class _DocumentsWorking:
    """A working copy of the governed documents register (D-43): its
    standing rows and bindings, copied, with the lookups the five
    document kinds need and the bindings that stood when the set started."""

    def __init__(self, register: documents_register.Register) -> None:
        self.contract = register.contract
        self.standing: list[dict] = copy.deepcopy(register.standing)
        self.bindings: list[dict] = copy.deepcopy(register.bindings)
        self.start_bound: set[str] = {str(b["document_id"]) for b in register.bindings}
        self.start_digest: str = documents_register.register_digest(register)

    def row(self, document_id: str) -> dict | None:
        for row in self.standing:
            if row["document_id"] == document_id:
                return row
        return None

    def require(self, document_id: str, what: str) -> dict:
        row = self.row(document_id)
        if row is None:
            raise ChangeError(f"{what}: the documents register carries no document {document_id!r}, and this set does not add it earlier")
        return row

    def binding(self, document_id: str, contract_id: str, column_name: str) -> dict | None:
        for b in self.bindings:
            if (b["document_id"], b["contract_id"], b["column_name"]) == (document_id, contract_id, column_name):
                return b
        return None

    def as_register(self) -> documents_register.Register:
        return documents_register.Register(contract=self.contract, standing=self.standing, bindings=self.bindings)


def load_documents(repo: Path) -> documents_register.Register:
    """The committed governed documents register, held to its contract; a
    tree without the contract, or a nonconforming register, is a refusal
    that names it."""
    if not (repo / documents_register.CONTRACT_PATH).is_file():
        raise ChangeError(
            f"a document change needs the governed documents register, and this tree has no"
            f" {documents_register.CONTRACT_PATH.as_posix()}"
        )
    try:
        return documents_register.load_register(repo)
    except RegisterError as exc:
        raise ChangeError(f"the committed documents register does not conform: {exc}; fix it by pull request first") from exc


def _committed_copy(repo: Path, row: dict, what: str):
    """The extraction of an in_repo row's committed copy: the one document
    text this command opens. Every other access class is drafted at a
    terminal with the documents module, which opens the mapped root or a
    reading copy, never here."""
    access = str(row.get("access"))
    if access == "local_path":
        raise ChangeError(
            f"{what}: {row['document_id']} is a local_path document; this command reads committed files only,"
            " so its binding is drafted at a terminal with `python -m metricmine.documents bind` under the mapped root"
        )
    if access != "in_repo":
        raise ChangeError(
            f"{what}: {row['document_id']} is a {access} document, which this project never opens; a binding on it"
            " is a hand edit of documents/register/bindings.yaml, checked with"
            " `python -m metricmine.documents verify --reading-copy`, by its own pull request"
        )
    path, how = documents_states.resolve_location(repo, row, None)
    if path is None:
        raise ChangeError(f"{what}: {row['document_id']}: {how}")
    fmt = str(row.get("format") or "")
    if fmt not in FORMATS:
        raise ChangeError(f"{what}: {row['document_id']}: no extractor for format {fmt!r}; this slice reads {', '.join(FORMATS)}")
    try:
        extraction = extract_path(path, fmt)
    except RefusedPackage as exc:
        raise ChangeError(f"{what}: {row['document_id']}: refused_package: {exc}") from exc
    if not extraction.text:
        raise ChangeError(f"{what}: {row['document_id']}: no_text_layer: the extraction holds no text, so no quote can be checked")
    return extraction


def _in_repo_location(location: str, what: str) -> str:
    pure = PurePosixPath(location.replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts or location.startswith("~") or not location.strip():
        raise ChangeError(f"{what}: an in_repo location is a repository-relative path, not {location!r}")
    if pure.parts[: len(INBOX.parts)] == INBOX.parts:
        raise ChangeError(
            f"{what}: {location} is a reading copy under {INBOX.as_posix()}/, which git never sees, so a merge"
            " could certify nothing there; declare the document's real location"
        )
    return pure.as_posix()


def _closed(value, allowed: tuple[str, ...], field_name: str, what: str) -> str:
    if value not in allowed:
        raise ChangeError(f"{what}: {field_name} {value!r} is not one of {', '.join(allowed)} (D-43)")
    return str(value)


def _add_document(w: _DocumentsWorking, c: dict, cs: ChangeSet, today: date, repo: Path, what: str) -> Applied:
    document_id = str(c["document_id"])
    if not _DOCUMENT_ID.match(document_id):
        raise ChangeError(f"{what}: document_id {document_id!r} is not lowercase letters, digits, dots, hyphens, and underscores")
    if w.row(document_id) is not None:
        raise ChangeError(f"{what}: document_id {document_id!r} is taken")
    governance = _closed(c["governance"], GOVERNANCE, "governance", what)
    access = _closed(c["access"], ACCESS, "access", what)
    certification = _closed(c["certification_source"], CERTIFICATION_SOURCES, "certification_source", what)
    gate = _closed(c["gate_strength"], GATE_STRENGTHS, "gate_strength", what)
    fmt = str(c["format"])
    title = str(c["title"]).strip()
    if not title:
        raise ChangeError(f"{what}: the title is empty")
    if access == "local_path":
        raise ChangeError(
            f"{what}: a local_path document is drafted at a terminal with `python -m metricmine.documents bind`,"
            " which opens the mapped root; this command reads committed files only"
        )
    row = {
        "document_id": document_id,
        "title": title,
        "governance": governance,
        "access": access,
        "location": str(c["location"]),
        "format": fmt,
        "certification_source": certification,
        "gate_strength": gate,
        "declared_by": cs.by,
        "declared_on": today,
        "review_by": _review_by(c, today, what) if c.get("review_by") is not None
        else today + timedelta(days=DOCUMENTS_REVIEW_DAYS.get(access, DOCUMENTS_REVIEW_DAYS["local_path"])),
    }
    for key in ("durable_id", "approver_role", "pinned_version", "upstream_url", "upstream_sha256", "license"):
        if c.get(key):
            row[key] = str(c[key])
    if access == "in_repo":
        row["location"] = _in_repo_location(str(c["location"]), what)
        if fmt not in FORMATS:
            suffix = PurePosixPath(row["location"]).suffix.lower()
            raise ChangeError(
                f"{what}: no extractor for format {fmt!r} (the suffix {suffix!r} reads as"
                f" {FORMAT_BY_SUFFIX.get(suffix, 'nothing this slice extracts')!r}); this slice reads {', '.join(FORMATS)}"
            )
        if c.get("text_sha256"):
            raise ChangeError(f"{what}: an in_repo document's text_sha256 is measured from the committed copy, never declared")
        extraction = _committed_copy(repo, row, what)
        digest = extraction.text_sha256
        for other in w.standing:
            if str(other.get("text_sha256")) == digest:
                raise ChangeError(
                    f"{what}: the same text is already registered as {other['document_id']} at {other['location']};"
                    " bind to that document instead of registering a second location"
                )
        row.update({"text_sha256": digest, "extractor": EXTRACTOR_ID, "verified_against": "location", "verified_on": today})
        note = f"added {title!r} from its committed copy; text digest {digest[:12]}"
    else:
        declared = c.get("text_sha256")
        if declared is not None:
            if not _SHA256.match(str(declared)):
                raise ChangeError(f"{what}: text_sha256 {declared!r} is not 64 lowercase hex characters")
            row.update({"text_sha256": str(declared), "verified_against": "none"})
        note = f"added {title!r} as declared ({access}); this command never opens its location"
    for other in w.standing:
        if str(other.get("title", "")).strip().lower() == title.lower():
            note += f"; warning: {other['document_id']} carries the same title"
    w.standing.append(row)
    return Applied(0, "add_document", "documents", "additive", document_id, None, note)


def _bind_document(w: _DocumentsWorking, c: dict, cs: ChangeSet, today: date, index: dict[str, set[str]], repo: Path, what: str) -> Applied:
    row = w.require(str(c["document_id"]), what)
    document_id = row["document_id"]
    contract_id, column_name = _element(index, c, what)
    if not column_name:
        raise ChangeError(f"{what}: a document binds a column; a claim about the table itself is a term or a concept (D-44)")
    anchor = str(c["anchor"]).strip()
    if not anchor:
        raise ChangeError(f"{what}: the anchor is empty")
    extraction = _committed_copy(repo, row, what)
    locator = extraction.locate(anchor)
    if locator is None:
        raise ChangeError(
            f"{what}: the quote is not in the committed copy of {row['location']};"
            " take it from `python -m metricmine.documents inspect --grep`"
        )
    element = f"{contract_id}.{column_name}"
    new = {
        "document_id": document_id,
        "contract_id": contract_id,
        "column_name": column_name,
        "anchor": anchor,
        "locator": locator,
        "intent": cs.intent,
        "intent_sha256": sha256_text(cs.intent),
        "bound_by": cs.by,
        "bound_on": today,
    }
    # L5 of the design round: the committed copy may have moved on from the
    # standing row's recorded digest; the quote was checked against the
    # text as it reads now, and the note says so (the documents module's
    # `bind` prints the same).
    drift = ""
    if str(row.get("text_sha256")) != extraction.text_sha256:
        drift = (
            "; the committed copy's text differs from the standing row's recorded digest, so the quote was"
            " checked against the text as it reads now; recertify the row in this set or by its own pull request"
        )
    existing = w.binding(document_id, contract_id, column_name)
    if existing is not None:
        if normalize(str(existing.get("anchor", ""))) == normalize(anchor):
            raise ChangeError(f"{what}: {element} is already bound to {document_id} on this quote; nothing changes")
        w.bindings[w.bindings.index(existing)] = new
        return Applied(0, "bind_document", "documents", "changing", document_id, element, f"re-anchored at {locator}; the draft replaces the standing binding" + drift)
    w.bindings.append(new)
    return Applied(0, "bind_document", "documents", "additive", document_id, element, f"bound on the quote at {locator}" + drift)


def _unbind_document(w: _DocumentsWorking, c: dict, what: str) -> Applied:
    document_id = str(c["document_id"])
    contract_id = str(c["contract_id"])
    column_name = str(c.get("column_name") or "")
    element = f"{contract_id}.{column_name}" if column_name else f"{contract_id} (table)"
    existing = w.binding(document_id, contract_id, column_name)
    if existing is None:
        raise ChangeError(f"{what}: no binding of {document_id} on {element}")
    w.bindings.remove(existing)
    return Applied(0, "unbind_document", "documents", "removing", document_id, element, "unbound")


def _recertify_document(w: _DocumentsWorking, c: dict, today: date, repo: Path, what: str) -> Applied:
    row = w.require(str(c["document_id"]), what)
    document_id = row["document_id"]
    notes: list[str] = []
    if str(row.get("access")) == "in_repo":
        if c.get("text_sha256"):
            raise ChangeError(f"{what}: an in_repo document's text_sha256 is measured from the committed copy, never declared")
        extraction = _committed_copy(repo, row, what)
        digest = extraction.text_sha256
        for b in w.bindings:
            if b["document_id"] != document_id:
                continue
            locator = extraction.locate(str(b["anchor"]))
            if locator is None:
                raise ChangeError(
                    f"{what}: the committed copy no longer carries the quote bound on {b['contract_id']}.{b['column_name']};"
                    " unbind it or restore the sentence before recertifying"
                )
            if locator != b.get("locator"):
                b["locator"] = locator
                notes.append(f"the quote bound on {b['contract_id']}.{b['column_name']} now sits at {locator}")
        if str(row.get("text_sha256")) != digest:
            notes.append(f"the text digest moved from {str(row.get('text_sha256'))[:12]} to {digest[:12]}; every anchor is present")
        day_moved = row.get("verified_on") != today
        row.update({"text_sha256": digest, "extractor": EXTRACTOR_ID, "verified_against": "location", "verified_on": today})
    elif str(row.get("access")) == "local_path":
        raise ChangeError(
            f"{what}: {document_id} is a local_path document; run `python -m metricmine.documents verify` with the root"
            " mapped and amend its standing row in that pull request; this command reads committed files only"
        )
    else:
        day_moved = False
        declared = c.get("text_sha256")
        if declared is not None:
            if not _SHA256.match(str(declared)):
                raise ChangeError(f"{what}: text_sha256 {declared!r} is not 64 lowercase hex characters")
            if str(row.get("text_sha256")) != str(declared):
                # A declared digest this command cannot measure replaces
                # whatever a person recorded, and says so; an equal digest
                # leaves the recorded verification as it stands.
                notes.append(f"the declared text digest moved to {str(declared)[:12]}; this command never opens its location")
                row["text_sha256"] = str(declared)
                row["verified_against"] = "none"
                row.pop("verified_on", None)
                row.pop("extractor", None)
    if c.get("pinned_version") is not None and str(c["pinned_version"]) != str(row.get("pinned_version")):
        row["pinned_version"] = str(c["pinned_version"])
        notes.append(f"pinned_version is {row['pinned_version']!r}")
    if c.get("review_by") is not None:
        review_by = _review_by(c, today, what)
        if review_by != row.get("review_by"):
            row["review_by"] = review_by
            notes.append(f"review_by moved to {review_by.isoformat()}")
    if not notes:
        if day_moved:
            notes.append("the text is unchanged; the verification day moved")
        else:
            raise ChangeError(f"{what}: {document_id} already reads as recertified; nothing changes")
    return Applied(0, "recertify_document", "documents", "changing", document_id, None, "; ".join(notes))


def _retire_document(w: _DocumentsWorking, c: dict, what: str) -> Applied:
    row = w.require(str(c["document_id"]), what)
    document_id = row["document_id"]
    if document_id in w.start_bound:
        standing = [b for b in w.bindings if b["document_id"] == document_id]
        held = ", ".join(f"{b['contract_id']}.{b['column_name']}" for b in standing) if standing else "unbound in this set"
        raise ChangeError(
            f"{what}: a binding stood on {document_id} when this set started ({held}); unbind it in its own set,"
            " merge, then retire (HW-35, two steps)"
        )
    w.standing = [r for r in w.standing if r["document_id"] != document_id]
    return Applied(0, "retire_document", "documents", "removing", document_id, None, "retired; no binding stood")


# ---------------------------------------------------------------- propose


def propose(repo: Path, registers: dict[str, MeaningRegister], change_set: ChangeSet, today: date) -> Proposal:
    """Validate every change in order against a working copy, classify
    each, re-bind every binding a changed digest touches under the set's
    intent, `by`, and day, and hold the result to the contracts' error
    rules. Raises ChangeError on the first refusal; nothing is written."""
    if not is_person(change_set.by):
        raise ChangeError(f"by {change_set.by!r} is not a person: the author of a change set is a person, never an agent or a model (D-44)")
    if not change_set.intent.strip():
        raise ChangeError("intent is empty: the person's words are part of the record")
    if not change_set.changes:
        raise ChangeError("the change set lists no change; nothing to propose")
    for register in registers.values():
        failing = [r for r in run_rules(register, today) if r.severity == "error" and not r.passed]
        if failing:
            names = "; ".join(f"{r.description} ({r.actual} rows)" for r in failing)
            raise ChangeError(
                f"the committed {register.spec.kind} register fails its contract's rules ({names});"
                " fix the register by pull request first, and `verify` names the rows"
            )
    index = contracts_index(repo)
    working = {kind: _Working(register) for kind, register in registers.items()}
    documents: _DocumentsWorking | None = None
    if any(str(change.get("kind")) in DOCUMENT_KINDS for change in change_set.changes):
        committed = load_documents(repo)
        failing = [r for r in documents_register.run_rules(committed, today) if r.severity == "error" and not r.passed]
        if failing:
            names = "; ".join(f"{r.description} ({r.actual} rows)" for r in failing)
            raise ChangeError(
                f"the committed documents register fails its contract's rules ({names});"
                " fix the register by pull request first, and `python -m metricmine.documents verify` names the rows"
            )
        documents = _DocumentsWorking(committed)
    applied: list[Applied] = []
    for position, change in enumerate(change_set.changes, 1):
        kind = str(change["kind"])
        what = f"change {position} ({kind})"
        if kind not in VOCABULARY:
            raise ChangeError(f"{what}: not in the vocabulary")
        register_kind, _ = VOCABULARY[kind]
        if register_kind == "documents":
            assert documents is not None
            if kind == "add_document":
                done = _add_document(documents, change, change_set, today, repo, what)
            elif kind == "bind_document":
                done = _bind_document(documents, change, change_set, today, index, repo, what)
            elif kind == "unbind_document":
                done = _unbind_document(documents, change, what)
            elif kind == "recertify_document":
                done = _recertify_document(documents, change, today, repo, what)
            else:
                done = _retire_document(documents, change, what)
            done.index = position
            applied.append(done)
            continue
        w = working[register_kind]
        if kind == "add_term":
            done = _add_term(w, change, change_set, today, what)
        elif kind == "amend_definition":
            done = _amend_definition(w, change, what)
        elif kind == "rename_term":
            done = _rename_term(w, change, what)
        elif kind == "add_synonym":
            done = _add_synonym(w, change, what)
        elif kind == "remove_synonym":
            done = _remove_synonym(w, change, what)
        elif kind in ("deprecate_term", "deprecate_concept"):
            done = _deprecate(w, change, kind, what)
        elif kind in ("drop_term", "drop_concept"):
            done = _drop(w, change, kind, what)
        elif kind in ("bind", "bind_concept"):
            done = _bind(w, change, change_set, today, index, kind, what)
        elif kind in ("unbind", "unbind_concept"):
            done = _unbind(w, change, kind, what)
        elif kind == "add_concept":
            done = _add_concept(w, change, change_set, today, what)
        elif kind == "amend_concept":
            done = _amend_concept(w, change, what)
        else:
            done = _relabel(w, change, what)
        done.index = position
        applied.append(done)

    rebound: list[dict] = []
    drift: list[dict] = []
    for w in working.values():
        spec = w.spec
        end = {r[spec.id_field]: w.digest(r) for r in w.rows}
        for b in w.bindings:
            row_id = b[spec.id_field]
            key = (row_id, b["contract_id"], b["column_name"])
            if row_id not in end or str(b.get(spec.digest_field)) == end[row_id]:
                continue
            element = f"{b['contract_id']}.{b['column_name']}" if b["column_name"] else f"{b['contract_id']} (table)"
            where = {"register": spec.kind, "id": row_id, "contract_id": b["contract_id"], "column_name": b["column_name"], "element": element}
            if key in w.touched or w.start_digests.get(row_id) != end[row_id]:
                # The row's digest moved in this set (an amended definition
                # or label, a moved parent), or this set bound it before
                # moving it: re-bind under the set's intent, by, and day.
                b[spec.digest_field] = end[row_id]
                b["intent"] = change_set.intent
                b["intent_sha256"] = sha256_text(change_set.intent)
                b["bound_by"] = change_set.by
                b["bound_on"] = today
                rebound.append(where)
            else:
                # Stale before this set started and untouched by it: reported,
                # never re-bound behind the person's back.
                drift.append(where)

    rendered = {kind: w.as_register() for kind, w in working.items()}
    problems: list[str] = []
    results = []
    for register in rendered.values():
        problems += integrity_problems(register)
        for result in run_rules(register, today):
            results.append(result)
            if result.severity == "error" and not result.passed:
                problems.append(f"{register.spec.kind}: rule failed: {result.description} ({result.actual} rows, expected {result.expected})")
    if problems:
        raise ChangeError("the rendered registers would not pass their contracts: " + "; ".join(problems) + "; the set is refused whole")
    from metricmine.meaning.states import derive

    drifted = {(d["register"], d["id"], d["contract_id"], d["column_name"]) for d in drift}
    for register in rendered.values():
        for report in derive(repo, register, None, index):
            if report.state.endswith("_changed") and (report.register, report.row_id, report.contract_id, report.column_name) not in drifted:
                raise ChangeError(f"the rendering would leave {report.row_id} on {report.element} {report.state}; the set is refused whole")
    before = {kind: register_digest(r) for kind, r in registers.items()}
    after = {kind: register_digest(r) for kind, r in rendered.items()}
    rendered_documents = None
    if documents is not None:
        rendered_documents = documents.as_register()
        _hold_documents(repo, rendered_documents, today, results)
        before["documents"] = documents.start_digest
        after["documents"] = documents_register.register_digest(rendered_documents)
    return Proposal(
        registers=rendered,
        applied=applied,
        rebound=rebound,
        standing_drift=drift,
        before=before,
        after=after,
        rules=results,
        documents=rendered_documents,
    )


def _hold_documents(repo: Path, register: documents_register.Register, today: date, results: list) -> None:
    """The rendered documents register held to its contract: the integrity
    checks (a person declared and bound every row; every binding rests on a
    standing row; every intent hash matches), the contract's error rules,
    and every in_repo row's anchors against its committed copy, with no
    calendar read. A failure refuses the whole set."""
    problems = documents_register.integrity_problems(register)
    for result in documents_register.run_rules(register, today):
        results.append(result)
        if result.severity == "error" and not result.passed:
            problems.append(f"documents: rule failed: {result.description} ({result.actual} rows, expected {result.expected})")
    if problems:
        raise ChangeError("the rendered documents register would not pass its contract: " + "; ".join(problems) + "; the set is refused whole")
    for report in documents_states.derive(repo, register, today=None):
        if report.state == "anchor_broken" and report.access == "in_repo":
            raise ChangeError(f"the rendering would leave {report.document_id} anchor_broken ({report.detail}); the set is refused whole")
        for flag in report.flags:
            if flag.startswith("binding_broken"):
                raise ChangeError(f"the rendering would leave {report.document_id} {flag}; the set is refused whole")


# ---------------------------------------------------------------- rendering


def draft_name(path: Path) -> str:
    """The outbox directory's name, from the change-set file's stem with a
    `.changes` suffix dropped, so a repeated draft overwrites itself."""
    stem = path.name
    for suffix in (".yaml", ".yml"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    if stem.endswith(".changes"):
        stem = stem[: -len(".changes")]
    return stem or "change-set"


def _iso(value) -> str:
    return value.isoformat() if isinstance(value, date) else str(value)


def _plain(obj):
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_plain(v) for v in obj]
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def write_proposal(repo: Path, proposal: Proposal, change_set: ChangeSet, today: date, outbox: Path | None = None) -> Path:
    """Write the four register files as they would read after the set,
    `record.json`, and `summary.md` into `proposals/meaning/<name>/`. The
    directory is fenced to the outbox: a path anywhere else, the register's
    own folder included, is refused before anything is written, and no
    file is written through a symbolic link (F-74)."""
    out = outbox or (repo / OUTBOX / draft_name(change_set.source))
    try:
        out = fenced_dir(repo, out, repo / OUTBOX)
    except FenceError as exc:
        raise ChangeError(f"--outbox {exc}") from exc
    rendered: dict[str, str] = {}
    files: list[tuple[Path, str]] = []
    try:
        for kind, register in proposal.registers.items():
            spec = register.spec
            folder = fenced_dir(repo, out / spec.rows_dir.name, repo / OUTBOX)
            for file, key, rows, which in (
                (spec.rows_file, spec.rows_key, register.rows, "rows"),
                (spec.bindings_file, "bindings", register.bindings, "bindings"),
            ):
                text = render_yaml(key, rows, HEADERS[(kind, which)])
                files.append((folder / file, text))
                rendered[f"{spec.rows_dir.name}/{file}"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if proposal.documents is not None:
            # The governed documents register as it would read, in the
            # documents module's own rendering (D-43), only when the set
            # carries a document kind; an untouched register is not rendered.
            folder = fenced_dir(repo, out / "documents", repo / OUTBOX)
            for file, key, rows, header in (
                (documents_register.STANDING_FILE, "documents", proposal.documents.standing, DOCUMENTS_STANDING_HEADER),
                (documents_register.BINDINGS_FILE, "bindings", proposal.documents.bindings, DOCUMENTS_BINDINGS_HEADER),
            ):
                text = render_yaml(key, rows, header)
                files.append((folder / file, text))
                rendered[f"documents/{file}"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        record = {
            "module": MODULE_ID,
            "source": _relative(repo, change_set.source),
            "by": change_set.by,
            "intent": change_set.intent,
            "intent_sha256": sha256_text(change_set.intent),
            "day": today.isoformat(),
            "change_set": _plain(change_set.raw),
            "changes": [
                {"index": a.index, "kind": a.kind, "register": a.register, "class": a.klass, "target": a.target,
                 "element": a.element, "note": a.note}
                for a in proposal.applied
            ],
            "rebound": proposal.rebound,
            "standing_drift": proposal.standing_drift,
            "register_digests": {kind: {"before": proposal.before[kind], "after": proposal.after[kind]} for kind in proposal.before},
            "rendered": rendered,
        }
        files.append((out / "record.json", json.dumps(record, indent=2, sort_keys=True) + "\n"))
        files.append((out / "summary.md", render_summary(repo, proposal, change_set, today, out)))
        # Every path is checked before the first write, so a refusal
        # leaves nothing behind in the outbox (F-74).
        for path, _ in files:
            check_fenced(path)
        for path, text in files:
            write_fenced(path, text)
    except FenceError as exc:
        raise ChangeError(str(exc)) from exc
    return out


def _relative(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def render_summary(repo: Path, proposal: Proposal, change_set: ChangeSet, today: date, out: Path) -> str:
    rel = _relative(repo, out)
    classes = {klass: sum(1 for a in proposal.applied if a.klass == klass) for klass in ("additive", "changing", "removing")}
    lines = [
        "# Governed meaning: a change set, rendered (D-44)",
        "",
        "Rendered by code from a person's change set. Nothing here is certified",
        "until the registers change by pull request and the merge approves it.",
        "",
        f"- by: {change_set.by} on {today.isoformat()}",
        f"- intent: \"{change_set.intent}\"",
        f"- intent_sha256: `{sha256_text(change_set.intent)}`",
        f"- changes: {len(proposal.applied)} ({classes['additive']} additive, {classes['changing']} changing, {classes['removing']} removing)",
        "",
        "## The changes, in order",
        "",
    ]
    for a in proposal.applied:
        target = f"{a.target} on {a.element}" if a.element else a.target
        lines.append(f"{a.index}. `{a.kind}` ({a.register}, {a.klass}): {target}; {a.note}")
    lines += ["", "## Re-bound under this set's intent", ""]
    if proposal.rebound:
        lines += [f"- {r['register']}: {r['id']} on {r['element']}" for r in proposal.rebound]
    else:
        lines.append("- none: no existing binding's digest moved")
    lines += ["", "## Standing drift this set did not touch", ""]
    if proposal.standing_drift:
        lines += [
            f"- {d['register']}: {d['id']} on {d['element']} reads changed; add a `bind` for it to re-bind, or restore the row"
            for d in proposal.standing_drift
        ]
    else:
        lines.append("- none")
    lines += ["", "## Register digests", ""]
    for kind in proposal.before:
        lines.append(f"- {kind}: `{proposal.before[kind][:16]}` before, `{proposal.after[kind][:16]}` after")
    lines += [
        "",
        "## To apply (on a branch, as a person)",
        "",
        f"    cp {rel}/glossary/*.yaml meaning/glossary/",
        f"    cp {rel}/ontology/*.yaml meaning/ontology/",
    ]
    if proposal.documents is not None:
        lines += [
            f"    cp {rel}/documents/*.yaml {documents_register.REGISTER_DIR.as_posix()}/",
            "    uv run python -m metricmine.documents verify",
        ]
    lines += [
        "    uv run python -m metricmine.meaning verify",
        "    uv run python -m metricmine.adoption scan",
        "",
        "Then open the pull request with this summary in its body. The merge is",
        "the certification; the unit lane holds the registers to their contracts",
        "and every binding to its row.",
        "",
    ]
    return "\n".join(lines)
