"""The derived document states the scan reports (D-35 as amended; D-43).

Derived on every run, written to the outbox with the plan, never stored.
For each standing row the module decides what it may open, opens only
that, extracts the text, and reports one content state with its flags
and the next command a person runs. The vocabulary:

- `in_sync`: the text digest equals the recorded one and every anchor
  is present.
- `changed_anchors_intact`: the text changed and every anchor is still
  present; nobody is asked to re-read the bindings, and an `in_repo`
  document's pull request refreshes its standing row.
- `anchor_broken`: a bound quote is no longer in the text; the flag names
  the bindings.
- `unreachable`: the location cannot be opened here: the root is not
  mapped, no file sits at the path, or the path escapes its root.
- `unverified_pointer`: a `public` or `pointer_only` location this slice
  never opens, and no reading copy was given.
- `unsupported_format`: the row names a format this slice has no
  extractor for.
- `refused_package`: the extractor refused the file under a safety limit.
- `no_text_layer`: the extraction holds no text.

Flags ride beside the content state: `review_overdue` (today is past
review_by), `pending_changes` (a Word file holds unaccepted redlines; the
flag names the bindings an acceptance would break), `binding_broken` (a
binding names a contract or column `contracts/` does not carry), and
`extractor_changed` (the recorded extractor differs from the running
one; every anchor is re-verified on every run regardless).

What the module never does: open a `public` URL, open a `pointer_only`
location, read a path outside the repository or outside the mapped root,
or store a state anywhere.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from metricmine.documents.extract import EXTRACTOR_ID, FORMATS, Extraction, RefusedPackage, extract_path, normalize
from metricmine.documents.register import Register

ROOT_ENV_VAR = "MM_DOCS_ROOT"
ROOT_TOKEN = "${MM_DOCS_ROOT}/"

CONTENT_STATES = (
    "in_sync",
    "changed_anchors_intact",
    "anchor_broken",
    "unreachable",
    "unverified_pointer",
    "unsupported_format",
    "refused_package",
    "no_text_layer",
)
FLAGS = ("review_overdue", "pending_changes", "binding_broken", "extractor_changed")

_NEXT = {
    "in_sync": "none",
    "changed_anchors_intact": (
        "none for the bindings (every bound quote is still present); for an in_repo document the"
        " pull request that changed it refreshes the standing row's text_sha256 and verified_on"
    ),
    "anchor_broken": (
        "read the pair; then re-anchor with the bind command, or amend the"
        " contract's sentence by its own pull request (rule 6)"
    ),
    "unreachable": "map MM_DOCS_ROOT on this machine, or re-point the standing row by pull request",
    "unverified_pointer": (
        "none here; verify against a reading copy with"
        " `uv run python -m metricmine.documents verify --reading-copy <id>=<path>`"
    ),
    "unsupported_format": "none in this slice; the format waits for its extractor and its pin decision",
    "refused_package": "fix or replace the file; the refusal names the limit",
    "no_text_layer": "none; the binding stands and nothing can be checked",
}


@dataclass
class DocumentReport:
    document_id: str
    title: str
    governance: str
    access: str
    location: str
    state: str
    detail: str
    flags: list[str] = field(default_factory=list)
    text_sha256_now: str | None = None
    verified_against: str = "none"

    @property
    def next_command(self) -> str:
        """Ordered by what blocks a merge: a broken anchor, then a broken
        binding, then an overdue review, then the state's own command."""
        if self.state == "anchor_broken":
            return _NEXT[self.state]
        if any(flag.startswith("binding_broken") for flag in self.flags):
            return "amend the binding by pull request: the contract or column it names is not committed"
        if any(flag.startswith("review_overdue") for flag in self.flags):
            return "re-certify by pull request: move review_by after a whole-document read"
        return _NEXT[self.state]

    @property
    def flags_text(self) -> str:
        return "; ".join(self.flags) if self.flags else "none"


def mapped_root(environ: dict | None = None) -> Path | None:
    value = (environ if environ is not None else os.environ).get(ROOT_ENV_VAR)
    return Path(value) if value else None


def contracts_index(repo: Path) -> dict[str, set[str]]:
    """Contract id to the set of property names across its table objects."""
    index: dict[str, set[str]] = {}
    for path in sorted((repo / "contracts").glob("*.odcs.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        names: set[str] = set()
        for obj in doc.get("schema") or []:
            for prop in obj.get("properties") or []:
                if prop.get("name"):
                    names.add(prop["name"])
        if doc.get("id"):
            index[str(doc["id"])] = names
    return index


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def resolve_location(repo: Path, row: dict, root: Path | None) -> tuple[Path | None, str]:
    """The path the module may open for this row, or None with the reason.
    `in_repo` resolves under the repository; `local_path` under the mapped
    root; `public` and `pointer_only` are never opened."""
    access = row["access"]
    location = str(row["location"])
    if access == "in_repo":
        candidate = repo / location
        if not _under(candidate, repo):
            return None, f"the path {location} escapes the repository"
        if not candidate.is_file():
            return None, f"no file at {location} in the repository"
        return candidate, "location"
    if access == "local_path":
        if not location.startswith(ROOT_TOKEN):
            return None, f"a local_path location must start with {ROOT_TOKEN}"
        if root is None:
            return None, f"root {ROOT_ENV_VAR} is not mapped on this machine"
        candidate = root / location[len(ROOT_TOKEN):]
        if not _under(candidate, root):
            return None, f"the path {location} escapes the mapped root"
        if not candidate.is_file():
            return None, f"no file at the mapped path for {location}"
        return candidate, "location"
    return None, f"a {access} location is never opened by this slice"


def derive(
    repo: Path,
    register: Register,
    today: date,
    root: Path | None = None,
    reading_copies: dict[str, Path] | None = None,
) -> list[DocumentReport]:
    """One report per standing row, in register order."""
    index = contracts_index(repo)
    reading_copies = reading_copies or {}
    reports = []
    for row in register.standing:
        reports.append(_report(repo, row, register.bindings_for(row["document_id"]), index, today, root, reading_copies))
    return reports


def _report(repo: Path, row: dict, bindings: list[dict], index: dict[str, set[str]], today: date,
            root: Path | None, reading_copies: dict[str, Path]) -> DocumentReport:
    report = DocumentReport(
        document_id=row["document_id"],
        title=str(row.get("title", "")),
        governance=row["governance"],
        access=row["access"],
        location=str(row["location"]),
        state="unverified_pointer",
        detail="",
    )
    review_by = row.get("review_by")
    if isinstance(review_by, date) and today > review_by:
        report.flags.append(f"review_overdue (review_by {review_by.isoformat()})")
    for binding in bindings:
        columns = index.get(binding["contract_id"])
        if columns is None or binding["column_name"] not in columns:
            report.flags.append(f"binding_broken:{binding['contract_id']}.{binding['column_name']}")

    copy = reading_copies.get(row["document_id"])
    if copy is not None:
        path, how = copy, "reading_copy"
    else:
        path, how = resolve_location(repo, row, root)
    if path is None:
        if row["access"] in ("public", "pointer_only"):
            report.state, report.detail = "unverified_pointer", how
        else:
            report.state, report.detail = "unreachable", how
        return report
    report.verified_against = how

    fmt = str(row.get("format", ""))
    if fmt not in FORMATS:
        report.state, report.detail = "unsupported_format", f"no extractor for {fmt!r} in this slice"
        return report
    try:
        extraction = extract_path(path, fmt)
    except RefusedPackage as exc:
        report.state, report.detail = "refused_package", str(exc)
        return report
    except OSError as exc:
        report.state, report.detail = "unreachable", f"the file could not be read ({exc.__class__.__name__}: {exc})"
        report.verified_against = "none"
        return report
    _content_state(report, row, bindings, extraction)
    return report


def _content_state(report: DocumentReport, row: dict, bindings: list[dict], extraction: Extraction) -> None:
    text = extraction.text
    if not text:
        report.state, report.detail = "no_text_layer", "the extraction holds no text"
        return
    report.text_sha256_now = extraction.text_sha256
    recorded = row.get("extractor")
    if recorded and str(recorded) != EXTRACTOR_ID:
        report.flags.append(f"extractor_changed ({recorded} recorded, {EXTRACTOR_ID} running)")
    missing = [b for b in bindings if normalize(str(b["anchor"])) not in text]
    targets = ", ".join(f"{b['contract_id']}.{b['column_name']}" for b in missing)
    recorded_digest = row.get("text_sha256")
    if missing:
        report.state = "anchor_broken"
        report.detail = f"anchor missing for {targets}"
    elif report.text_sha256_now == recorded_digest:
        report.state = "in_sync"
        report.detail = "text digest unchanged; every anchor present"
    elif not recorded_digest:
        report.state = "changed_anchors_intact"
        report.detail = f"no recorded digest to compare (the text read now is {report.text_sha256_now}); every anchor present"
    else:
        report.state = "changed_anchors_intact"
        report.detail = f"text digest changed to {report.text_sha256_now}; every anchor present"
    if extraction.has_pending_changes:
        accepted = extraction.accepted_text or ""
        would_break = [b for b in bindings if normalize(str(b["anchor"])) not in accepted]
        if would_break:
            report.flags.append(
                "pending_changes (accepting them breaks: "
                + ", ".join(f"{b['contract_id']}.{b['column_name']}" for b in would_break)
                + ")"
            )
        else:
            report.flags.append("pending_changes (no anchor touched)")


def counts(reports: list[DocumentReport]) -> dict[str, int]:
    """Nonzero state counts in the fixed CONTENT_STATES order, then the
    nonzero flag counts in the fixed FLAGS order."""
    out: dict[str, int] = {}
    for state in CONTENT_STATES:
        n = sum(1 for r in reports if r.state == state)
        if n:
            out[state] = n
    for flag in FLAGS:
        n = sum(1 for r in reports if any(f.startswith(flag) for f in r.flags))
        if n:
            out[flag] = n
    return out


def plan_rows(reports: list[DocumentReport]) -> list[dict]:
    """The plan.json shape: one dict per document, JSON-serializable."""
    return [
        {
            "document_id": r.document_id,
            "title": r.title,
            "governance": r.governance,
            "access": r.access,
            "location": r.location,
            "state": r.state,
            "detail": r.detail,
            "flags": list(r.flags),
            "text_sha256_now": r.text_sha256_now,
            "verified_against": r.verified_against,
            "next_command": r.next_command,
        }
        for r in reports
    ]


def documents_section(repo: Path, today: date, root: Path | None = None) -> dict:
    """What the scan reports (D-35 as amended): the register's standing,
    the state counts, and one item per document. It never raises: a tree
    without the register contract reports `absent`, a register that does
    not conform reports `nonconforming` with the reason, and `verify` is
    where the exit code lives. The scan reports; it never judges."""
    from metricmine.documents.register import CONTRACT_PATH, RegisterError, load_register

    if not (repo / CONTRACT_PATH).is_file():
        return {
            "register": "absent",
            "detail": f"no {CONTRACT_PATH.as_posix()} in this tree",
            "counts": {},
            "items": [],
        }
    try:
        register = load_register(repo)
    except RegisterError as exc:
        return {"register": "nonconforming", "detail": str(exc), "counts": {}, "items": []}
    reports = derive(repo, register, today, root)
    return {
        "register": "conforms",
        "detail": (
            f"{register.contract.id}@{register.contract.version}: {len(register.standing)}"
            f" standing row(s), {len(register.bindings)} binding(s)"
        ),
        "counts": counts(reports),
        "items": plan_rows(reports),
    }
