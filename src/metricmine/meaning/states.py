"""The derived meaning states the scan reports (D-35 as amended by
Amendment AC; D-44).

Derived on every run, written to the outbox with the plan, never stored.
For each binding in either register the module compares the digest the
binding recorded with the row's current digest and reads one state:

- `in_sync`: the digest equals the one the binding recorded and the
  element is in a committed contract.
- `term_changed` / `concept_changed`: the digest moved under a standing
  binding (a hand edit changed the definition, the label, or the parent
  without a re-bind); the item names the binding and the re-bind that
  clears it.
- `term_missing` / `concept_missing`: the binding names a row the
  register no longer carries.
- `term_deprecated` / `concept_deprecated`: the row's status is
  `deprecated`, reported as declared with its `superseded_by` when one
  exists; a deprecated bound row stands on main until a later set drops
  it (HW-35), so the gate of record accepts it beside `in_sync`.
- `binding_broken`: a binding names a contract or column `contracts/`
  does not carry.

The flag `review_overdue` rides beside the state when the cited row's
`review_by` is past the run's day; it is derived from the row, so every
binding that cites an overdue row carries it, and `verify` reports the
rows themselves through the contract's warn rule.

What the module never does: put a meaning item in the queue the batch
driver walks, route a term or a concept into a proposer, or store a
state anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from metricmine.documents.states import contracts_index
from metricmine.meaning.register import SPECS, MeaningRegister, RegisterSpec

STATES = (
    "in_sync",
    "term_changed",
    "concept_changed",
    "term_missing",
    "concept_missing",
    "term_deprecated",
    "concept_deprecated",
    "binding_broken",
)
FLAGS = ("review_overdue",)


@dataclass
class BindingReport:
    register: str
    row_id: str
    label: str
    contract_id: str
    column_name: str
    state: str
    detail: str
    flags: list[str] = field(default_factory=list)

    @property
    def element(self) -> str:
        return f"{self.contract_id}.{self.column_name}" if self.column_name else f"{self.contract_id} (table)"

    @property
    def next_command(self) -> str:
        """Ordered by what blocks a merge: a missing row, then a broken
        binding, then a moved digest, then an overdue review, then the
        state's own. No command routes a term or a concept into a
        proposer."""
        noun = "term" if self.register == "glossary" else "concept"
        kind = "bind" if self.register == "glossary" else "bind_concept"
        if self.state.endswith("_missing"):
            return (
                f"amend the binding by pull request: the register carries no {noun} {self.row_id};"
                f" restore the {noun} or unbind the element in a change set (`make meaning-propose CHANGES=<file>`)"
            )
        if self.state == "binding_broken":
            return (
                "amend the binding by pull request: the contract or column it names is not committed;"
                " `unbind` it in a change set, or re-point it with the contract pull request that renames the element"
            )
        if self.state.endswith("_changed"):
            return (
                f"re-bind by pull request: a change set with `{kind}` for {self.element} on {self.row_id}"
                f" re-renders the row at the {noun}'s current digest under your intent"
                " (`make meaning-propose CHANGES=<file>`), or restore the definition"
            )
        if any(flag.startswith("review_overdue") for flag in self.flags):
            return f"re-certify by pull request: move the {noun}'s review_by after a read of its definition"
        if self.state.endswith("_deprecated"):
            return (
                f"none required; the {noun} is deprecated and reported as declared;"
                " move the binding to the successor in a change set when one stands"
            )
        return "none"

    @property
    def flags_text(self) -> str:
        return "; ".join(self.flags) if self.flags else "none"


def derive(repo: Path, register: MeaningRegister, today: date | None,
           index: dict[str, set[str]] | None = None) -> list[BindingReport]:
    """One report per binding, in register order. ``today`` is the day
    the `review_overdue` flag is derived for; None derives no flag."""
    index = contracts_index(repo) if index is None else index
    spec = register.spec
    digests = register.digests()
    rows = {}
    for row in register.rows:
        rows.setdefault(row[spec.id_field], row)
    return [_report(spec, b, rows, digests, index, today) for b in register.bindings]


def _report(spec: RegisterSpec, b: dict, rows: dict[str, dict], digests: dict[str, str],
            index: dict[str, set[str]], today: date | None) -> BindingReport:
    row_id = str(b[spec.id_field])
    row = rows.get(row_id)
    report = BindingReport(
        register=spec.kind,
        row_id=row_id,
        label=str(row.get(spec.label_field, "")) if row else "",
        contract_id=str(b["contract_id"]),
        column_name=str(b.get("column_name") or ""),
        state="in_sync",
        detail="",
    )
    if row is not None:
        review_by = row.get("review_by")
        if today is not None and isinstance(review_by, date) and today > review_by:
            report.flags.append(f"review_overdue (review_by {review_by.isoformat()})")
    columns = index.get(report.contract_id)
    element_ok = columns is not None and (report.column_name == "" or report.column_name in columns)
    if row is None:
        report.state = f"{spec.noun}_missing"
        report.detail = f"the register carries no {spec.noun} {row_id}"
        return report
    if not element_ok:
        report.state = "binding_broken"
        report.detail = (
            f"no committed contract {report.contract_id}" if columns is None
            else f"contract {report.contract_id} carries no column {report.column_name}"
        )
        return report
    recorded = str(b.get(spec.digest_field) or "")
    current = digests[row_id]
    if recorded != current:
        report.state = f"{spec.noun}_changed"
        report.detail = f"the {spec.noun}'s digest is {current[:12]} now; the binding recorded {recorded[:12] or 'none'}"
        return report
    if str(row.get("status")) == "deprecated":
        report.state = f"{spec.noun}_deprecated"
        successor = row.get("superseded_by")
        report.detail = f"superseded by {successor}" if successor else "no successor named"
        return report
    report.detail = "digest unchanged; the element is in a committed contract"
    return report


def counts(reports: list[BindingReport]) -> dict[str, int]:
    """Nonzero state counts in the fixed STATES order, then the nonzero
    flag counts in the fixed FLAGS order."""
    out: dict[str, int] = {}
    for state in STATES:
        n = sum(1 for r in reports if r.state == state)
        if n:
            out[state] = n
    for flag in FLAGS:
        n = sum(1 for r in reports if any(f.startswith(flag) for f in r.flags))
        if n:
            out[flag] = n
    return out


def plan_rows(reports: list[BindingReport]) -> list[dict]:
    """The plan.json shape: one dict per binding, JSON-serializable."""
    return [
        {
            "register": r.register,
            "id": r.row_id,
            "label": r.label,
            "contract_id": r.contract_id,
            "column_name": r.column_name,
            "state": r.state,
            "detail": r.detail,
            "flags": list(r.flags),
            "next_command": r.next_command,
        }
        for r in reports
    ]


def meaning_section(repo: Path, today: date) -> dict:
    """What the scan reports (Amendment AC): each register's standing, the
    state counts, and one item per binding. It never raises: a tree
    without a register contract reports that register `absent`, a
    register that does not conform reports `nonconforming` with the
    reason (a row outside its contract, a name that is not a person, or
    a failing error rule; the items are still derived when the rows
    load, so an orphaned binding reads `term_missing` beside the rule
    that names it), a data contract that does not parse reports both
    registers `nonconforming`, and `verify` is where the exit code lives.
    The scan reports; it never judges."""
    import yaml

    from metricmine.documents.register import RegisterError
    from metricmine.meaning.register import load_register, run_rules

    registers: dict[str, dict] = {}
    reports: list[BindingReport] = []
    try:
        index = contracts_index(repo)
    except yaml.YAMLError as exc:
        reason = f"a data contract under contracts/ is not valid YAML ({str(exc).splitlines()[0]})"
        return {"registers": {spec.kind: {"register": "nonconforming", "detail": reason} for spec in SPECS}, "counts": {}, "items": []}
    for spec in SPECS:
        if not (repo / spec.contract_path).is_file():
            registers[spec.kind] = {"register": "absent", "detail": f"no {spec.contract_path.as_posix()} in this tree"}
            continue
        try:
            register = load_register(repo, spec)
        except RegisterError as exc:
            registers[spec.kind] = {"register": "nonconforming", "detail": str(exc)}
            continue
        failing = [r for r in run_rules(register, today) if r.severity == "error" and not r.passed]
        standing = f"{register.contract.id}@{register.contract.version}: {len(register.rows)} {spec.noun}(s), {len(register.bindings)} binding(s)"
        if failing:
            registers[spec.kind] = {
                "register": "nonconforming",
                "detail": f"{standing}; rule failed: " + "; ".join(f"{r.description} ({r.actual} rows, expected {r.expected})" for r in failing),
            }
        else:
            registers[spec.kind] = {"register": "conforms", "detail": standing}
        reports += derive(repo, register, today, index)
    return {"registers": registers, "counts": counts(reports), "items": plan_rows(reports)}
