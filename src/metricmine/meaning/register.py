"""The two meaning registers and their contracts (D-44).

Each register is two YAML files under `meaning/<kind>/` (the rows and the
bindings) held to an ordinary ODCS contract under `contracts/` by the
mechanisms the documents register already has: every row carries the
columns the contract declares and no other, every required column is
present, every date parses, and the contract's own sql rules run over
the rows in an in-memory DuckDB at the severity each declares (D-28).
The two checks a contract cannot express run here: a declarer, a
binder, or an owner is a person (the known agent, model, and tool names
are refused), and an intent travels with its hash.

Identity is a stable id and a content digest. A term's digest is the
sha256 of the canonical bytes of its `term_id`, `term`, and
`definition` after NFKC and whitespace normalization, nothing else:
synonyms are served and never hashed, so adding or removing one moves no
binding. A concept's digest is a node digest over `concept_id`, `label`,
`parent_id`, and `definition`: a parent change re-asks the bindings of
the concept whose parent moved and not its descendants'. The canonical
bytes are the profiler's (`canonical_bytes`: sorted keys, two-space
indent, UTF-8, a trailing newline), the form the Prep H probe measured.

Nothing here writes. The registers change only by pull request; a change
set renders into the outbox through `propose`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from metricmine.documents.extract import normalize
from metricmine.documents.register import (
    Contract,
    RegisterError,
    RuleResult,
    conform_rows,
    execute_rules,
    is_person,
    load_yaml,
    parse_contract,
    rows_from,
    sha256_text,
)
from metricmine.profiling.canonical import canonical_bytes

MEANING_DIR = Path("meaning")
STATUSES = ("active", "deprecated")
SYNONYM_SEPARATOR = "; "


def _digest(mapping: dict[str, str]) -> str:
    return hashlib.sha256(canonical_bytes(mapping)).hexdigest()


def term_digest(row: dict) -> str:
    """sha256 over the canonical bytes of the term's id, label, and
    definition, each NFKC- and whitespace-normalized; never its synonyms."""
    return _digest({
        "term_id": normalize(str(row.get("term_id", ""))),
        "term": normalize(str(row.get("term", ""))),
        "definition": normalize(str(row.get("definition", ""))),
    })


def concept_digest(row: dict) -> str:
    """The node digest: sha256 over the canonical bytes of the concept's id,
    label, parent id (the empty string at a root), and definition."""
    parent = row.get("parent_id")
    return _digest({
        "concept_id": normalize(str(row.get("concept_id", ""))),
        "label": normalize(str(row.get("label", ""))),
        "parent_id": normalize(str(parent)) if parent is not None else "",
        "definition": normalize(str(row.get("definition", ""))),
    })


def split_synonyms(value) -> list[str]:
    """The synonyms a row carries, as the register stores them: a string
    separated by `; `, each trimmed, empties dropped."""
    if value is None:
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]


def join_synonyms(values: list[str]) -> str | None:
    return SYNONYM_SEPARATOR.join(values) if values else None


@dataclass(frozen=True)
class RegisterSpec:
    """What makes the glossary and the ontology two registers of one shape."""

    kind: str
    contract_path: Path
    rows_dir: Path
    rows_file: str
    rows_key: str
    rows_table: str
    bindings_file: str
    bindings_table: str
    id_field: str
    label_field: str
    digest_field: str
    digest: Callable[[dict], str]
    noun: str

    @property
    def rows_path(self) -> Path:
        return self.rows_dir / self.rows_file

    @property
    def bindings_path(self) -> Path:
        return self.rows_dir / self.bindings_file


GLOSSARY = RegisterSpec(
    kind="glossary",
    contract_path=Path("contracts") / "glossary_register.odcs.yaml",
    rows_dir=MEANING_DIR / "glossary",
    rows_file="terms.yaml",
    rows_key="terms",
    rows_table="glossary_terms",
    bindings_file="bindings.yaml",
    bindings_table="glossary_bindings",
    id_field="term_id",
    label_field="term",
    digest_field="term_sha256",
    digest=term_digest,
    noun="term",
)
ONTOLOGY = RegisterSpec(
    kind="ontology",
    contract_path=Path("contracts") / "ontology_register.odcs.yaml",
    rows_dir=MEANING_DIR / "ontology",
    rows_file="concepts.yaml",
    rows_key="concepts",
    rows_table="ontology_concepts",
    bindings_file="bindings.yaml",
    bindings_table="ontology_bindings",
    id_field="concept_id",
    label_field="label",
    digest_field="concept_sha256",
    digest=concept_digest,
    noun="concept",
)
SPECS = (GLOSSARY, ONTOLOGY)


@dataclass
class MeaningRegister:
    """One register: its spec, its contract, its rows, and its bindings."""

    spec: RegisterSpec
    contract: Contract
    rows: list[dict] = field(default_factory=list)
    bindings: list[dict] = field(default_factory=list)

    def row(self, row_id: str) -> dict | None:
        for row in self.rows:
            if row[self.spec.id_field] == row_id:
                return row
        return None

    def bindings_for(self, row_id: str) -> list[dict]:
        return [b for b in self.bindings if b[self.spec.id_field] == row_id]

    def digest_of(self, row: dict) -> str:
        return self.spec.digest(row)

    def digests(self) -> dict[str, str]:
        """The current digest per row id; the first row wins a duplicate
        id, which the contract's own rule reports."""
        out: dict[str, str] = {}
        for row in self.rows:
            out.setdefault(row[self.spec.id_field], self.spec.digest(row))
        return out


# ---------------------------------------------------------------- loading


def load_register_contract(repo: Path, spec: RegisterSpec) -> Contract:
    return parse_contract(load_yaml(repo / spec.contract_path), (spec.rows_table, spec.bindings_table), spec.contract_path.as_posix())


def load_register(repo: Path, spec: RegisterSpec) -> MeaningRegister:
    """The register's two tables, validated against its contract. Raises
    RegisterError on the first violation, naming the file, the row, and the
    column; an orphaned or duplicated binding is a rule's finding and a
    state's reading, never a load failure, so `verify` and the scan can
    say `term_missing` instead of refusing to look."""
    contract = load_register_contract(repo, spec)
    rows = rows_from(repo / spec.rows_path, spec.rows_key)
    bindings = rows_from(repo / spec.bindings_path, "bindings")
    conform_rows(rows, contract.columns[spec.rows_table], spec.rows_file)
    conform_rows(bindings, contract.columns[spec.bindings_table], spec.bindings_file)
    register = MeaningRegister(spec, contract, rows, bindings)
    for problem in integrity_problems(register):
        raise RegisterError(problem)
    return register


def integrity_problems(register: MeaningRegister) -> list[str]:
    """The checks the contract's SQL cannot express: a person declared
    every row and owns it, a person bound every binding, and every intent
    hash matches its intent."""
    spec = register.spec
    problems: list[str] = []
    for row in register.rows:
        row_id = row.get(spec.id_field)
        for column in ("declared_by", "owner"):
            if not is_person(str(row.get(column, ""))):
                problems.append(f"{spec.rows_file} {row_id}: {column} {row.get(column)!r} is not a person")
    for b in register.bindings:
        key = (b.get(spec.id_field), b.get("contract_id"), b.get("column_name"))
        if not is_person(str(b.get("bound_by", ""))):
            problems.append(f"{spec.bindings_file} {key}: bound_by {b.get('bound_by')!r} is not a person")
        if sha256_text(str(b.get("intent", ""))) != str(b.get("intent_sha256", "")):
            problems.append(f"{spec.bindings_file} {key}: intent_sha256 does not match the intent")
    return problems


def run_rules(register: MeaningRegister, today: date | None) -> list[RuleResult]:
    """Every sql rule the register's contract declares, over its two tables,
    with `current_date` read as `today` (the documents register's runner)."""
    spec = register.spec
    return execute_rules(
        register.contract.columns,
        {spec.rows_table: register.rows, spec.bindings_table: register.bindings},
        register.contract.rules,
        today,
    )


def register_digest(register: MeaningRegister) -> str:
    """sha256 over the canonical bytes of the register's rows and bindings
    as loaded, dates as ISO text: what a record cites as the register's
    digest before and after a change set."""
    payload = {
        spec_key: [{k: (v.isoformat() if isinstance(v, date) else v) for k, v in row.items()} for row in rows]
        for spec_key, rows in ((register.spec.rows_key, register.rows), ("bindings", register.bindings))
    }
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def load_all(repo: Path) -> dict[str, MeaningRegister]:
    """Both registers, by kind; a missing contract is a RegisterError that
    names it (the scan's section reports `absent` instead)."""
    out = {}
    for spec in SPECS:
        if not (repo / spec.contract_path).is_file():
            raise RegisterError(f"no register contract at {spec.contract_path.as_posix()}")
        out[spec.kind] = load_register(repo, spec)
    return out
