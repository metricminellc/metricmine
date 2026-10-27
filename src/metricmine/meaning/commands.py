"""The producer commands: find, show, propose, verify (D-44).

Deterministic code a person runs at a terminal, or a coding host runs in
its shell and reads. No model call, no network, no MCP tool: the host
door is a command, not a tool, and the pull request is the only
approval.

- `find` lists terms and concepts whose id, label, definition, synonyms,
  or parent id contain a text, each with its carried-by list, derived
  from the bindings and never authored.
- `show` prints one term or concept with its bindings and their states.
- `propose` runs a change set through the closed vocabulary's checks,
  classifies every change, re-binds what a changed digest touches under
  the set's intent, and renders the registers as they would read into
  `proposals/meaning/<name>/`; nothing under `meaning/` or `contracts/`
  is touched, and no flag certifies anything or relaxes a check.
- `verify` holds both registers to their contracts, runs their rules,
  derives every binding's state, and exits 1 on what blocks a merge: a
  register that does not conform, a failing error-severity rule, a
  changed or missing term or concept under a standing binding, or a
  broken binding; a deprecation and an overdue review are reported.

Consent in chat is permission to draft, never certification (design rule
3): what a person approves into the record is the rendering this module
writes, merged by pull request.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from metricmine.documents.register import RegisterError
from metricmine.documents.states import contracts_index
from metricmine.meaning import changes as cs
from metricmine.meaning.register import SPECS, MeaningRegister, load_all, run_rules, split_synonyms
from metricmine.meaning.states import BindingReport, derive

BLOCKING = ("term_changed", "concept_changed", "term_missing", "concept_missing", "binding_broken")


class CommandError(Exception):
    """A refusal: the command stops before it writes; the message names why."""


# ---------------------------------------------------------------- find


@dataclass(frozen=True)
class Hit:
    register: str
    row_id: str
    label: str
    status: str
    carried_by: tuple[str, ...]
    text: str


def _carried_by(register: MeaningRegister, row_id: str) -> tuple[str, ...]:
    return tuple(
        f"{b['contract_id']}.{b['column_name']}" if b.get("column_name") else f"{b['contract_id']} (table)"
        for b in register.bindings_for(row_id)
    )


def find(registers: dict[str, MeaningRegister], query: str) -> list[Hit]:
    """Rows whose id, label, definition, synonyms, or parent id contain
    `query` (case-insensitive); an empty query lists every row."""
    needle = query.strip().lower()
    hits: list[Hit] = []
    for spec in SPECS:
        register = registers[spec.kind]
        for row in register.rows:
            haystack = " ".join(
                str(row.get(key) or "") for key in (spec.id_field, spec.label_field, "definition", "synonyms", "parent_id")
            ).lower()
            if needle and needle not in haystack:
                continue
            text = str(row.get("definition", ""))
            if spec.kind == "glossary" and row.get("synonyms"):
                text += f" (synonyms: {'; '.join(split_synonyms(row.get('synonyms')))})"
            if spec.kind == "ontology" and row.get("parent_id"):
                text += f" (parent: {row['parent_id']})"
            hits.append(Hit(spec.kind, str(row[spec.id_field]), str(row[spec.label_field]), str(row.get("status", "")),
                            _carried_by(register, str(row[spec.id_field])), text))
    return hits


def render_find(hits: list[Hit], query: str) -> str:
    lines = [f"find {query!r}: {len(hits)} hit(s) across the glossary and the ontology"]
    for h in hits:
        carried = ", ".join(h.carried_by) if h.carried_by else "nothing (no binding)"
        lines.append(f"  {h.register} | {h.row_id} | {h.label} | {h.status} | carried by {carried}")
        lines.append(f"    {h.text}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- show


def show(repo: Path, registers: dict[str, MeaningRegister], row_id: str) -> str:
    """One row with its bindings and their states, derived for no
    calendar (the review flag is `verify`'s and the scan's)."""
    index = contracts_index(repo)
    found: list[str] = []
    for spec in SPECS:
        register = registers[spec.kind]
        row = register.row(row_id)
        if row is None:
            continue
        lines = [f"{spec.kind} {spec.noun}: {row_id}"]
        for key in register.contract.columns[spec.rows_table]:
            value = row.get(key.name)
            lines.append(f"  {key.name}: {_iso(value) if value is not None else ''}")
        lines.append(f"  digest: {register.digest_of(row)}")
        reports = [r for r in derive(repo, register, None, index) if r.row_id == row_id]
        lines.append(f"  bindings: {len(reports)}")
        for r in reports:
            lines.append(f"    {r.element} | {r.state} | {r.detail}")
            lines.append(f"      next: {r.next_command}")
        found.append("\n".join(lines))
    if not found:
        raise CommandError(f"no term or concept with id {row_id!r} in either register")
    return "\n".join(found) + "\n"


def _iso(value) -> str:
    return value.isoformat() if isinstance(value, date) else str(value)


# ---------------------------------------------------------------- propose


def propose(repo: Path, registers: dict[str, MeaningRegister], path: Path, today: date,
            outbox: Path | None = None) -> tuple[cs.Proposal, cs.ChangeSet, Path]:
    try:
        change_set = cs.load_change_set(repo, path)
        proposal = cs.propose(repo, registers, change_set, today)
        out = cs.write_proposal(repo, proposal, change_set, today, outbox)
    except cs.ChangeError as exc:
        raise CommandError(str(exc)) from exc
    return proposal, change_set, out


# ---------------------------------------------------------------- verify


@dataclass
class Verification:
    registers: dict[str, MeaningRegister]
    errors: list[str]
    rules: dict[str, list]
    reports: list[BindingReport]

    @property
    def failures(self) -> list[str]:
        out = list(self.errors)
        for kind, results in self.rules.items():
            for result in results:
                if result.severity == "error" and not result.passed:
                    out.append(f"{kind}: rule failed: {result.description} ({result.actual} rows, expected {result.expected})")
        for report in self.reports:
            if report.state in BLOCKING:
                out.append(f"{report.register}: {report.row_id} on {report.element}: {report.state}: {report.detail}")
        return out

    @property
    def exit_code(self) -> int:
        return 1 if self.failures else 0


def verify(repo: Path, today: date) -> Verification:
    """Both registers held to their contracts, every rule, every state."""
    try:
        registers = load_all(repo)
    except RegisterError as exc:
        return Verification({}, [f"register does not conform: {exc}"], {}, [])
    index = contracts_index(repo)
    rules = {kind: run_rules(register, today) for kind, register in registers.items()}
    reports: list[BindingReport] = []
    for spec in SPECS:
        reports += derive(repo, registers[spec.kind], today, index)
    return Verification(registers, [], rules, reports)


def render_verify(v: Verification, today: date) -> str:
    lines = [f"meaning verify (today {today.isoformat()})"]
    if v.errors:
        for error in v.errors:
            lines.append(f"  FAIL {error}")
        return "\n".join(lines) + "\n"
    for spec in SPECS:
        register = v.registers[spec.kind]
        lines.append(
            f"  {spec.kind}: conforms to {register.contract.id}@{register.contract.version}"
            f" ({len(register.rows)} {spec.noun}(s), {len(register.bindings)} binding(s))"
        )
        lines.append(f"  rules: {len(v.rules[spec.kind])}")
        for r in v.rules[spec.kind]:
            mark = "pass" if r.passed else ("WARN" if r.severity == "warn" else "FAIL")
            lines.append(f"    {mark} [{r.severity}] {r.table}: {r.description} ({r.actual} rows, expected {r.expected})")
    lines.append(f"  bindings: {len(v.reports)}")
    for rep in v.reports:
        lines.append(f"    {rep.register} | {rep.row_id} | {rep.element} | {rep.state} | flags: {rep.flags_text}")
        lines.append(f"      {rep.detail}")
        lines.append(f"      next: {rep.next_command}")
    lines.append("  result: " + ("OK" if not v.failures else "FAIL"))
    for failure in v.failures:
        lines.append(f"    {failure}")
    return "\n".join(lines) + "\n"
