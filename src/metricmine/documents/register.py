"""The governed documents register: two tables and their contract (D-43).

The register lives in `documents/register/` as two YAML files, one row
per governed document (`standing.yaml`) and one row per bound contract
column (`bindings.yaml`), and is held to `contracts/documents_register.odcs.yaml`
by this module: every row carries the columns the contract declares and
no other, every required column is present, every date parses, and the
contract's own quality rules run over the rows in an in-memory DuckDB so
the register is judged by the SQL the contract declares, at the severity
it declares (D-28). Gate three records the contract as having no model;
this module and the unit lane are where its rules execute.

Two checks the contract cannot express run here too. A declarer or
binder is a person: the known agent names and model identifiers are
refused (D-43; S37 lesson 5), and a name that starts with `claude-` with
them. A binding's intent travels with its hash (the Amendment I pattern),
so a record that drifts from the words a person typed is refused.

Nothing here writes. The register changes only by pull request; drafts
land in the outbox through `bind`.

The mechanisms a second register in this shape needs are public here
and take their contract or their rows as arguments: `load_yaml`,
`parse_contract`, `rows_from`, `conform_rows`, `execute_rules`,
`is_person`, and `sha256_text`. The governed meaning module (D-44)
imports them; nothing is copied.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import duckdb
import yaml

CONTRACT_PATH = Path("contracts") / "documents_register.odcs.yaml"
REGISTER_DIR = Path("documents") / "register"
STANDING_FILE = "standing.yaml"
BINDINGS_FILE = "bindings.yaml"
STANDING_TABLE = "documents_standing"
BINDINGS_TABLE = "documents_bindings"

# The closed sets (governance, access, the certification source, the gate's
# strength, verified_against) are the contract's own sql rules, not code:
# the contract is the authority and run_rules executes it (D-28).

# A declarer or binder is a person. Code refuses what it can check: the two
# proposers' names (D-10), the D-34 allow-list, the repository's own SDLC
# tooling by name, and any claude- identifier.
# tests/test_documents_register.py holds these tuples to the agents package.
KNOWN_AGENT_NAMES = ("silver-cleanup-proposer", "gold-mapping-proposer")
KNOWN_MODEL_IDS = ("claude-sonnet-5", "claude-opus-5", "claude-fable-5")
KNOWN_TOOL_NAMES = ("oscar",)  # .claude/agents/oscar.md, the resident subagent

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CURRENT_DATE = re.compile(r"\bcurrent_date\b", re.IGNORECASE)


class RegisterError(Exception):
    """The register does not conform to its contract; the message names why."""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_person(name: str) -> bool:
    """False for a name code can recognize as an agent or a model."""
    lowered = name.strip().lower()
    if not lowered:
        return False
    if lowered in KNOWN_AGENT_NAMES or lowered in KNOWN_MODEL_IDS or lowered in KNOWN_TOOL_NAMES:
        return False
    return not lowered.startswith("claude-")


@dataclass(frozen=True)
class Column:
    name: str
    physical_type: str
    required: bool


@dataclass(frozen=True)
class Rule:
    table: str
    description: str
    query: str
    must_be: int
    severity: str


@dataclass(frozen=True)
class Contract:
    id: str
    version: str
    columns: dict[str, tuple[Column, ...]]
    rules: tuple[Rule, ...]


@dataclass
class Register:
    contract: Contract
    standing: list[dict] = field(default_factory=list)
    bindings: list[dict] = field(default_factory=list)

    def standing_row(self, document_id: str) -> dict | None:
        for row in self.standing:
            if row["document_id"] == document_id:
                return row
        return None

    def bindings_for(self, document_id: str) -> list[dict]:
        return [row for row in self.bindings if row["document_id"] == document_id]


# ---------------------------------------------------------------- loading


def load_yaml(path: Path) -> dict:
    """A YAML mapping, or a RegisterError that names the file and the parser's
    reason; a malformed file is nonconforming, never a traceback."""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RegisterError(f"{path.name}: not valid YAML ({str(exc).splitlines()[0]})") from exc
    if doc is None:
        return {}
    if not isinstance(doc, dict):
        raise RegisterError(f"{path.name}: expected a mapping at the top level")
    return doc


def parse_contract(doc: dict, tables: tuple[str, ...], where: str) -> Contract:
    """The columns and the sql rules of a register contract's table objects;
    `tables` names the objects the contract must declare, and `where` is the
    contract's path for the refusal."""
    columns: dict[str, tuple[Column, ...]] = {}
    rules: list[Rule] = []
    for obj in doc.get("schema") or []:
        name = obj["name"]
        columns[name] = tuple(
            Column(prop["name"], prop.get("physicalType", "VARCHAR"), bool(prop.get("required", False)))
            for prop in obj.get("properties") or []
        )
        for rule in obj.get("quality") or []:
            if rule.get("type") == "sql" and rule.get("query"):
                rules.append(
                    Rule(
                        table=name,
                        description=str(rule.get("description", "")),
                        query=str(rule["query"]),
                        must_be=int(rule.get("mustBe", 0)),
                        severity=str(rule.get("severity", "error")),
                    )
                )
    for table in tables:
        if table not in columns:
            raise RegisterError(f"{where} declares no schema object {table}")
    return Contract(id=str(doc.get("id")), version=str(doc.get("version")), columns=columns, rules=tuple(rules))


def load_contract(repo: Path) -> Contract:
    return parse_contract(load_yaml(repo / CONTRACT_PATH), (STANDING_TABLE, BINDINGS_TABLE), CONTRACT_PATH.as_posix())


def rows_from(path: Path, key: str) -> list[dict]:
    """The rows under `key` in a YAML file, or none when the file is absent."""
    if not path.is_file():
        return []
    doc = load_yaml(path)
    rows = doc.get(key)
    if rows is None:
        return []
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise RegisterError(f"{path.as_posix()}: {key} must be a list of rows")
    return rows


def load_register(repo: Path) -> Register:
    """The two tables, validated against the contract. Raises RegisterError
    on the first violation, naming the file, the row, and the column."""
    contract = load_contract(repo)
    standing = rows_from(repo / REGISTER_DIR / STANDING_FILE, "documents")
    bindings = rows_from(repo / REGISTER_DIR / BINDINGS_FILE, "bindings")
    conform_rows(standing, contract.columns[STANDING_TABLE], STANDING_FILE)
    conform_rows(bindings, contract.columns[BINDINGS_TABLE], BINDINGS_FILE)
    register = Register(contract=contract, standing=standing, bindings=bindings)
    for problem in integrity_problems(register):
        raise RegisterError(problem)
    return register


def _as_date(value, where: str) -> date:
    if isinstance(value, datetime):
        raise RegisterError(f"{where}: a timestamp where a date belongs: {value.isoformat()}")
    if isinstance(value, date):
        return value
    if isinstance(value, str) and _DATE.match(value):
        return date.fromisoformat(value)
    raise RegisterError(f"{where}: not a date: {value!r}")


def conform_rows(rows: list[dict], columns: tuple[Column, ...], file: str) -> None:
    """Every row carries the columns the contract declares and no other,
    every required column is present, every date parses, and every other
    value is text; the first violation names the file, the row, and the
    column. Dates are parsed in place."""
    names = {column.name for column in columns}
    for index, row in enumerate(rows, 1):
        where = f"{file} row {index}"
        extra = sorted(set(row) - names)
        if extra:
            raise RegisterError(f"{where}: columns not in the contract: {', '.join(extra)}")
        for column in columns:
            value = row.get(column.name)
            if value is None:
                if column.required:
                    raise RegisterError(f"{where}: required column {column.name} is missing")
                continue
            if column.physical_type.upper() == "DATE":
                row[column.name] = _as_date(value, f"{where}.{column.name}")
            elif not isinstance(value, str):
                raise RegisterError(f"{where}.{column.name}: expected text, got {type(value).__name__}")


# ---------------------------------------------------------------- integrity


def integrity_problems(register: Register) -> list[str]:
    """The checks the contract's SQL cannot express: a person declared
    every row, every intent hash matches its intent, and every binding
    rests on a standing row."""
    problems: list[str] = []
    ids = {row["document_id"] for row in register.standing}
    if len(ids) != len(register.standing):
        problems.append(f"{STANDING_FILE}: document_id is not unique")
    for row in register.standing:
        if not is_person(str(row.get("declared_by", ""))):
            problems.append(f"{STANDING_FILE} {row['document_id']}: declared_by {row.get('declared_by')!r} is not a person")
    seen: set[tuple] = set()
    for row in register.bindings:
        key = (row["document_id"], row["contract_id"], row["column_name"])
        if key in seen:
            problems.append(f"{BINDINGS_FILE}: duplicate binding {key}")
        seen.add(key)
        if row["document_id"] not in ids:
            problems.append(f"{BINDINGS_FILE} {key}: no standing row for {row['document_id']}")
        if not is_person(str(row.get("bound_by", ""))):
            problems.append(f"{BINDINGS_FILE} {key}: bound_by {row.get('bound_by')!r} is not a person")
        if sha256_text(str(row.get("intent", ""))) != str(row.get("intent_sha256", "")):
            problems.append(f"{BINDINGS_FILE} {key}: intent_sha256 does not match the intent")
    return problems


# ---------------------------------------------------------------- the contract's rules


@dataclass(frozen=True)
class RuleResult:
    table: str
    description: str
    severity: str
    actual: int
    expected: int

    @property
    def passed(self) -> bool:
        return self.actual == self.expected


def run_rules(register: Register, today: date | None) -> list[RuleResult]:
    """Run every sql quality rule the contract declares over the register's
    rows in an in-memory DuckDB. `current_date` in a rule reads as `today`,
    so a caller fixes the calendar and no test turns red on a date. With
    ``today`` None the rules that read `current_date` are not run: the
    context compiler holds the register to the contract's other rules and
    reads no calendar (D-30 as amended by Amendment AA)."""
    return execute_rules(
        register.contract.columns,
        {STANDING_TABLE: register.standing, BINDINGS_TABLE: register.bindings},
        register.contract.rules,
        today,
    )


def execute_rules(
    columns_by_table: dict[str, tuple[Column, ...]],
    rows_by_table: dict[str, list[dict]],
    rules: tuple[Rule, ...],
    today: date | None,
) -> list[RuleResult]:
    """The rule runner `run_rules` delegates to, for any register in this
    shape: one in-memory table per entry of `rows_by_table`, typed from
    the contract's columns, then every rule in declared order."""
    con = duckdb.connect()
    try:
        for table, rows in rows_by_table.items():
            columns = columns_by_table[table]
            ddl = ", ".join(f'"{c.name}" {"DATE" if c.physical_type.upper() == "DATE" else "VARCHAR"}' for c in columns)
            con.execute(f'CREATE TABLE "{table}" ({ddl})')
            if rows:
                placeholders = ", ".join("?" for _ in columns)
                con.executemany(
                    f'INSERT INTO "{table}" VALUES ({placeholders})',
                    [[row.get(c.name) for c in columns] for row in rows],
                )
        results = []
        for rule in rules:
            if today is None:
                if _CURRENT_DATE.search(rule.query):
                    continue
                query = rule.query
            else:
                query = _CURRENT_DATE.sub(f"DATE '{today.isoformat()}'", rule.query)
            actual = con.execute(query).fetchone()[0]
            results.append(RuleResult(rule.table, rule.description, rule.severity, int(actual), rule.must_be))
        return results
    finally:
        con.close()
