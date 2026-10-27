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

Additive moves no existing binding's digest. Changing moves a term's or
a concept's digest, and the command re-binds every binding that cites
it under the set's intent, `by`, and day, listing each by name.
Removing is two steps: a deprecation first (additive in its mechanics
and served as declared), then a drop, refused while a binding stands,
while the row is not deprecated by an earlier merge, or, for a concept,
while a child names it as parent (HW-35, deprecate then drop). The five
document kinds D-44 enumerates ride the slice that serves meaning and
are refused here by name.

What the command never does: write under `meaning/` or `contracts/`
(the outbox is fenced and no file is written through a symbolic link),
certify anything, relax a check, or re-bind a binding whose row this
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
from pathlib import Path

from metricmine.documents.commands import FenceError, check_fenced, fenced_dir, render_yaml, write_fenced
from metricmine.documents.extract import normalize
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
}
DOCUMENT_KINDS = ("add_document", "bind_document", "unbind_document", "recertify_document", "retire_document")
REGISTER_CONTRACTS = ("documents_register", "glossary_register", "ontology_register")
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


# ---------------------------------------------------------------- the file


def load_schema(repo: Path) -> dict:
    return json.loads((repo / SCHEMA_PATH).read_text(encoding="utf-8"))


def load_change_set(repo: Path, path: Path) -> ChangeSet:
    """The change-set file, validated against the committed schema; a
    document kind is refused by name before any other check."""
    if not path.is_file():
        raise ChangeError(f"no change-set file at {path.as_posix()}")
    try:
        raw = load_yaml(path)
    except RegisterError as exc:
        raise ChangeError(str(exc)) from exc
    for index, change in enumerate(raw.get("changes") or [], 1):
        kind = change.get("kind") if isinstance(change, dict) else None
        if kind in DOCUMENT_KINDS:
            raise ChangeError(
                f"change {index}: `{kind}` is a document change kind; it rides the slice that serves governed"
                " meaning (D-44) and is not in this slice's vocabulary. Until then a document change beyond"
                " `bind` is a hand edit a reviewer reads, and `python -m metricmine.documents bind` drafts a binding"
            )
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
    applied: list[Applied] = []
    for position, change in enumerate(change_set.changes, 1):
        kind = str(change["kind"])
        what = f"change {position} ({kind})"
        if kind not in VOCABULARY:
            raise ChangeError(f"{what}: not in the vocabulary")
        register_kind, _ = VOCABULARY[kind]
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
    return Proposal(
        registers=rendered,
        applied=applied,
        rebound=rebound,
        standing_drift=drift,
        before={kind: register_digest(r) for kind, r in registers.items()},
        after={kind: register_digest(r) for kind, r in rendered.items()},
        rules=results,
    )


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
            "register_digests": {kind: {"before": proposal.before[kind], "after": proposal.after[kind]} for kind in proposal.registers},
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
    for kind in proposal.registers:
        lines.append(f"- {kind}: `{proposal.before[kind][:16]}` before, `{proposal.after[kind][:16]}` after")
    lines += [
        "",
        "## To apply (on a branch, as a person)",
        "",
        f"    cp {rel}/glossary/*.yaml meaning/glossary/",
        f"    cp {rel}/ontology/*.yaml meaning/ontology/",
        "    uv run python -m metricmine.meaning verify",
        "    uv run python -m metricmine.adoption scan",
        "",
        "Then open the pull request with this summary in its body. The merge is",
        "the certification; the unit lane holds the registers to their contracts",
        "and every binding to its row.",
        "",
    ]
    return "\n".join(lines)
