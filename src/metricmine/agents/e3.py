"""E3, the skeleton and the context channel: the arm runner, the ledger,
the evidence copier and its screen, the leakage counter, and the scorer
(experiment branch only; docs/experiments/e3/KEY.md).

`python -m metricmine.agents eval --arm <arm> --repeats <n>` runs one
batch of the arm declared in docs/experiments/e3/arms.yaml: every fixture
of the arm, `<n>` attempts each, one ordinary harness call per attempt
(the same bounded retry, the same outbox), the spend bound printed before
the first call and enforced before every call against the ledger total
plus the next run's estimate, one reported line per run, the attempt
copied into the committed evidence folder after a screen. Nothing here
calls a model outside the harness, and nothing here changes the scorer
(agreement.py, unchanged).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import statistics
import sys
from pathlib import Path
from typing import Any

import yaml

from metricmine.agents import (
    agreement,
    harness,
    mapping_proposer,
    models,
    render,
    silver_proposer,
    skeleton,
)

ARMS_PATH = Path("docs/experiments/e3/arms.yaml")
RATE_RATIO = {"claude-sonnet-5": 1.0, "claude-opus-5": 2.5, "claude-fable-5": 5.0}
LEDGER_FIELDS = (
    "arm", "model", "label", "attempt", "stance", "disposition", "attempts",
    "first_attempt_lint_pass", "first_attempt_groundedness_pass",
    "machine_errors_at_1", "judgment_errors_at_1", "structural_at_1",
    "agree", "checked", "mismatches", "oracle_columns", "shared_columns",
    "draft_columns", "fields", "grain_set_equal", "grain_order_equal",
    "empty_descriptions", "input_tokens", "output_tokens", "cost_usd",
    "prompt_version", "schema_digest", "context_hash", "technical",
    "technical_attempt", "rerun", "continued", "created_at", "evidence_dir",
)
# A cell with fewer results than this is unresolved: it decides no rule
# (KEY.md, Section 9).
CELL_FLOOR = 5
# A batch whose cost actual passes this multiple of its estimate stops
# itself; a run whose cost passes this multiple of its own estimate is
# reported (KEY.md, Section 6).
BATCH_STOP_RATIO = 3.0
COST_HIGH_RATIO = 3.0

# The error classes (KEY.md, Section 9, the class table), matched as
# substrings against the validator's and the harness's own strings. A
# string no class names is counted as judgment, except the unclassed
# strings, which are neither the model's judgment nor its structure.
_MACHINE_DESCRIBE = (
    "completeness: columns must enumerate",
    "is not a column of the profiled table",
    ".physical_type ",
    ".required ",
    ".logical_type ",
    "completeness: exactly one row_count_positive",
    "completeness: exactly one grain_unique",
    "groundedness: target_schema",
    "groundedness: target_table",
    "completeness: stance",
    "completeness: proposed_version",
    "completeness: describe must carry an empty changes",
    "completeness: table-level rule",
)
_MACHINE_AMEND = (
    "re-emits physical_type",
    "re-emits required",
    "with no declared drop_column",
    "with no declared add_column",
    "with no declared grain_change",
    "still appears in columns[]",
    "disagrees with grain_keys",
    "must enter required false",
    "completeness: proposed_version",
    "completeness: stance",
    "groundedness: target_schema",
    "groundedness: target_table",
)
_STRUCTURAL = ("response stopped on", "response is not valid JSON", "proposal schema:")
_UNCLASSED = ("staleness:", "api error:")


class E3Error(ValueError):
    """A precondition the runner refuses on, before any call."""


# ----------------------------------------------------------------- loading


def load_arms(repo_root: Path) -> dict:
    return yaml.safe_load((repo_root / ARMS_PATH).read_text(encoding="utf-8"))


def fixtures_by_label(arms: dict) -> dict[str, dict]:
    return {fixture["label"]: fixture for fixture in arms["fixtures"]}


def classify_errors(stance: str, errors: list[str]) -> tuple[int, int, int]:
    """(machine-half, judgment, structural) counts over one attempt's
    errors; a staleness or api-error string is counted nowhere."""
    machine_keys = _MACHINE_AMEND if stance == "amend" else _MACHINE_DESCRIBE
    machine = judgment = structural = 0
    for error in errors:
        if any(key in error for key in _UNCLASSED):
            continue
        if any(key in error for key in _STRUCTURAL):
            structural += 1
        elif stance in ("describe", "amend") and any(
            key in error for key in machine_keys
        ):
            machine += 1
        else:
            judgment += 1
    return machine, judgment, structural


def _schema_digest(path: Path) -> str:
    stripped, _ = harness.load_proposal_schema(path)
    compact = json.dumps(stripped, separators=(",", ":"), sort_keys=True)
    return "sha256:" + hashlib.sha256(compact.encode("utf-8")).hexdigest()


def context_file(fixture: dict, arm: dict) -> str | None:
    """The committed context file an arm reads for a fixture: the
    fixture's `context`, or its `context_docs_only` (the same text
    without the conventions sentences) when the arm says `docs_only`."""
    mode = arm["context"]
    if not mode:
        return None
    return fixture.get("context_docs_only" if mode == "docs_only" else "context")


def build_run(repo_root: Path, arms: dict, arm_name: str, label: str) -> dict:
    """The spec and the run_proposer kwargs for one fixture under one arm:
    the prompt set, the skeleton, the context, the committed input, the
    intent. Reads files; calls nothing."""
    arm = arms["arms"][arm_name]
    fixture = fixtures_by_label(arms)[label]
    stance = fixture["stance"]
    prompt_path = repo_root / arms["prompts"][arm["prompts"]][stance]
    kwargs: dict[str, Any] = {"profile": str(repo_root / fixture["profile"])}
    committed = None
    if stance == "cleanup":
        spec = silver_proposer.build_spec(
            repo_root, source=fixture.get("source"), target=fixture.get("target")
        )
    elif stance == "propose":
        spec = mapping_proposer.build_spec(
            repo_root, table=fixture.get("table"), target=fixture.get("target")
        )
    elif stance == "describe":
        spec = silver_proposer.build_describe_spec(repo_root, fixture["table"])
    elif stance == "amend":
        committed_path = repo_root / fixture["committed"]
        spec, committed, committed_bytes = silver_proposer.build_amend_spec(
            repo_root, fixture["table"], committed_path=committed_path
        )
        bound = harness.GovernedInput(
            kind="committed_contract",
            path=str(committed_path),
            content_hash=render.canonical_contract_bytes(committed_bytes),
            schema_version=str(committed.get("version", "")),
        )
        kwargs["extra_inputs"] = [(bound, committed_bytes.decode("utf-8"))]
        kwargs["intent"] = fixture["intent"].strip()
        kwargs["provenance_extras"] = {
            "amendsContract": render.amends_contract_stamp(committed, committed_bytes)
        }
    else:
        raise E3Error(f"fixture {label!r} declares an unknown stance {stance!r}")

    changes: dict[str, Any] = {"prompt_path": prompt_path}
    if arm["skeleton"]:
        if stance not in ("describe", "amend"):
            raise E3Error(
                f"arm {arm_name!r} runs the skeleton, which describe and "
                f"amend carry; fixture {label!r} is {stance}"
            )
        changes["proposal_schema"] = repo_root / arms["judgment_schema"]
        if stance == "describe":
            changes["skeleton"] = lambda artifact, judgment: skeleton.apply_judgment(
                skeleton.describe_skeleton(artifact), judgment
            )
        else:
            frozen = committed
            changes["skeleton"] = lambda artifact, judgment: skeleton.apply_judgment(
                skeleton.amend_skeleton(frozen), judgment
            )
    spec = dataclasses.replace(spec, **changes)

    if arm["context"]:
        context_rel = context_file(fixture, arm)
        if not context_rel:
            raise E3Error(
                f"arm {arm_name!r} carries a context ({arm['context']}) but "
                f"fixture {label!r} names no such context file"
            )
        context_path = repo_root / context_rel
        # Bytes, decoded: the recorded hash is the hash the staleness
        # re-check computes over the file, whatever the line endings.
        kwargs["context"] = context_path.read_bytes().decode("utf-8")
        kwargs["context_path"] = str(context_path)
    return {"spec": spec, "kwargs": kwargs, "fixture": fixture, "committed": committed}


# ----------------------------------------------------------------- ledger


def ledger_path(repo_root: Path, arms: dict) -> Path:
    return repo_root / arms["ledger"]


def read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def append_ledger(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def ledger_total(rows: list[dict]) -> float:
    return round(sum(float(row.get("cost_usd") or 0.0) for row in rows), 6)


# ----------------------------------------------------------------- screen

# The employer-safe words and the service-level claim, the website's copy
# gate's regexes, assembled from parts so this file passes its own screen;
# plus the key material a public branch must never carry, and a path under
# a home directory, which names a machine.
_BANNED = re.compile(
    "|".join(["port" + "folio", "hir" + "ing", "recr" + "uit", "res" + "ume", "through" + "put", "trusted " + "by"]),
    re.IGNORECASE,
)
_SERVICE_LEVEL = re.compile(r"\b" + "s" + "la" + r"\b", re.IGNORECASE)
_KEY_MATERIAL = re.compile("sk-" + "ant-" + r"[A-Za-z0-9_-]{8,}|ANTHROPIC" + "_API_KEY" + r"\s*[=:]\s*\S")
_HOME_PATH = re.compile(
    "(?:" + "/" + "Users/|/" + "home/|[A-Za-z]:\\\\" + "Users\\\\)" + r"[^/\\\s\"']+"
)
_EM_DASH = "\u2014"


def screen_text(text: str) -> tuple[list[str], int]:
    """Refusals (each a reason) and the em dash count for one text."""
    refusals: list[str] = []
    if _KEY_MATERIAL.search(text):
        refusals.append("key material")
    hit = _BANNED.search(text)
    if hit:
        refusals.append(f"employer-safe word {hit.group(0)!r}")
    if _SERVICE_LEVEL.search(text):
        refusals.append("service-level claim")
    if _HOME_PATH.search(text):
        refusals.append("a path under a home directory")
    return refusals, text.count(_EM_DASH)


def _relativize(node: Any, roots: tuple[str, ...]) -> Any:
    """Every occurrence of a root (the repository root, resolved and as
    given) inside a string becomes repository-relative, so an evidence
    record is the same bytes on every machine that copies it."""
    if isinstance(node, dict):
        return {key: _relativize(value, roots) for key, value in node.items()}
    if isinstance(node, list):
        return [_relativize(value, roots) for value in node]
    if isinstance(node, str):
        for root in roots:
            if root:
                node = node.replace(root + "/", "").replace(root + "\\", "").replace(root, ".")
        return node
    return node


def copy_evidence(repo_root: Path, run_dir: Path, dest: Path) -> tuple[int, int]:
    """Copy one attempt's files from the outbox into the evidence folder
    after the screen; the record's absolute paths are relativized to the
    repository root. Returns (files copied, em dashes reported). Raises
    E3Error on a refusal, copying nothing for that attempt."""
    roots = tuple(dict.fromkeys((str(repo_root.resolve()), str(repo_root))))
    staged: list[tuple[Path, bytes]] = []
    dashes = 0
    for name in ("record.json", "proposal.json", "judgment.json", "draft.odcs.yaml", "agreement.json", "raw_response.txt"):
        source = run_dir / name
        if not source.exists():
            continue
        if name == "record.json":
            record = json.loads(source.read_text(encoding="utf-8"))
            data = (
                json.dumps(_relativize(record, roots), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            ).encode("utf-8")
        else:
            data = source.read_bytes()
        text = data.decode("utf-8", errors="replace")
        refusals, count = screen_text(text)
        if refusals:
            raise E3Error(f"screen refused {name}: {', '.join(refusals)}")
        dashes += count
        staged.append((dest / name, data))
    dest.mkdir(parents=True, exist_ok=True)
    for path, data in staged:
        harness._replace_bytes(path, data)
    return len(staged), dashes


# ----------------------------------------------------------------- the runner


def _first_attempt(record: dict) -> dict:
    log = record["validation"].get("attempt_log") or []
    return log[0] if log else {}


def technical_attempt(record: dict) -> int | None:
    """The attempt at which the SDK raised, or at which a response carried
    no usage; None when every attempt answered. A technical failure at
    attempt 1 is not a result; one on a retry turn leaves attempt 1 as a
    result for the first-attempt rates (KEY.md, Section 8)."""
    if record.get("api_error"):
        return int(record["validation"]["attempts"])
    usage = record.get("usage") or {}
    if record.get("response_id") and not (usage.get("input_tokens") or usage.get("output_tokens")):
        return 1
    return None


def _is_lost(row: dict) -> bool:
    """A fail-closed result: the model's own exit (the retry budget, a
    staleness or relaxation stop), never a transport failure."""
    return row["disposition"] == "failed_closed" and not row["technical"] and row.get("technical_attempt") is None


def run_arm(
    repo_root: Path,
    arm_name: str,
    *,
    repeats: int | None = None,
    model_flag: str | None = None,
    rerun_technical: bool = False,
    continue_lost: str | None = None,
    dry_run: bool = False,
    client: Any = None,
    lint_runner: harness.LintRunner | None = None,
    out=None,
    ledger: Path | None = None,
    evidence_dir: Path | None = None,
    arms: dict | None = None,
) -> int:
    """One batch. Exit 0 when every planned attempt ran (results included),
    3 on a bound or batch stop or a screen refusal, 1 on a precondition.
    `ledger`, `evidence_dir`, and `arms` default to arms.yaml's; tests pass
    their own so nothing under docs/ moves."""
    out = out or sys.stdout
    arms = arms or load_arms(repo_root)
    if arm_name not in arms["arms"]:
        print(f"error: no arm {arm_name!r} in {ARMS_PATH}; arms are {sorted(arms['arms'])}", file=sys.stderr)
        return 1
    arm = arms["arms"][arm_name]
    try:
        resolved = models.resolve_model(model_flag)
    except models.ModelNotAllowedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if resolved.model_id != arms["default_model"] and not arm["model_override"]:
        print(
            f"error: arm {arm_name!r} runs at {arms['default_model']} only "
            f"(KEY.md, Section 7); the model control re-runs the baseline arm",
            file=sys.stderr,
        )
        return 1
    if not dry_run and client is None and not os.environ.get("ANTHROPIC_API_KEY"):
        print("error: ANTHROPIC_API_KEY is not set; the eval lane is the live lane", file=sys.stderr)
        return 1
    n = int(arm["repeats"]) if repeats is None else int(repeats)
    if n < 1:
        print("error: --repeats must be a positive integer", file=sys.stderr)
        return 1
    if continue_lost is not None and continue_lost not in arm["fixtures"]:
        print(f"error: --continue-lost names {continue_lost!r}, which arm {arm_name!r} does not run", file=sys.stderr)
        return 1
    by_label = fixtures_by_label(arms)
    ratio = RATE_RATIO[resolved.model_id]
    bound = float(arms["spend_bound_usd"])
    ledger = ledger or ledger_path(repo_root, arms)
    rows = read_ledger(ledger)
    # The ledger is read once per batch; every appended row keeps the
    # in-memory total equal to the file's.
    total = ledger_total(rows)
    tag = arm_name if resolved.model_id == arms["default_model"] else f"{arm_name}-{resolved.model_id}"
    evidence_root = (evidence_dir or (repo_root / arms["evidence_dir"])) / tag

    planned = [(label, attempt) for label in arm["fixtures"] for attempt in range(1, n + 1)]
    batch_estimate = round(sum(float(by_label[label]["estimate_usd"]) * ratio for label, _ in planned), 4)
    print(
        f"SPEND-BOUND {bound:.2f} USD; ledger total {total:.4f} USD; this batch: "
        f"{arm_name} {resolved.model_id} {len(planned)} runs estimated {batch_estimate:.4f} USD",
        file=out,
    )

    if dry_run:
        return _dry_run(repo_root, arms, arm_name, arm, resolved, out, model_flag)

    done: dict[tuple, dict] = {}
    latest_result: dict[str, dict] = {}
    for row in rows:
        if row["arm"] != arm_name or row["model"] != resolved.model_id:
            continue
        done[(row["label"], row["attempt"])] = row
        if not row["technical"]:
            latest_result[row["label"]] = row
    lost = {label for label, row in latest_result.items() if _is_lost(row)}
    batch_cost = 0.0
    counts = {"ran": 0, "written": 0, "failed": 0, "technical": 0, "lost": 0, "skipped": 0, "files": 0, "dashes": 0}
    for label in arm["fixtures"]:
        fixture = by_label[label]
        continued = False
        if label in lost:
            if continue_lost == label:
                print(
                    f"CONTINUE {arm_name} {label}: its latest result failed closed; re-invoked on a "
                    f"person's instruction after the record was read (D-10 Amendment G)",
                    file=out,
                )
                continued = True
                lost.discard(label)
            else:
                print(
                    f"LOST {arm_name} {label}: its latest result failed closed; never re-invoked "
                    f"unattended (D-10 Amendment G)",
                    file=out,
                )
                counts["lost"] += 1
                continue
        for attempt in range(1, n + 1):
            key = (label, attempt)
            prior = done.get(key)
            if prior is not None:
                if prior["technical"] and rerun_technical and not prior.get("rerun"):
                    print(f"RERUN {arm_name} {label} a{attempt:02d}: the ledger marks it technical; re-invoked once by a person", file=out)
                else:
                    counts["skipped"] += 1
                    continue
            estimate = float(fixture["estimate_usd"]) * ratio
            if total + estimate > bound:
                print(
                    f"BOUND-STOP ledger total {total:.4f} USD plus the next run's estimate "
                    f"{estimate:.4f} USD would pass the bound {bound:.2f} USD; nothing called",
                    file=out,
                )
                return 3
            if batch_cost > BATCH_STOP_RATIO * batch_estimate:
                print(
                    f"BATCH-STOP this batch's cost {batch_cost:.4f} USD passed {BATCH_STOP_RATIO:g} times its estimate "
                    f"{batch_estimate:.4f} USD; nothing further called",
                    file=out,
                )
                return 3
            built = build_run(repo_root, arms, arm_name, label)
            report: dict = {}
            code = harness.run_proposer(
                built["spec"], repo_root, model_flag=resolved.model_id if model_flag else None,
                client=client, lint_runner=lint_runner, report=report, quiet=True, **built["kwargs"],
            )
            record = report.get("record")
            run_dir = report.get("run_dir")
            if record is None:
                # A precondition refusal (exit 1) is the same on every
                # attempt: report it and stop before the ledger grows.
                print(
                    f"REFUSED {arm_name} {label} a{attempt:02d}: the harness refused before any call "
                    f"(exit {code}); the batch stops; nothing recorded",
                    file=out,
                )
                return 1
            row = _ledger_row(repo_root, arms, arm_name, resolved.model_id, label, attempt, built, record)
            row["rerun"] = prior is not None
            row["continued"] = continued
            technical = row["technical"]
            cost = float(row["cost_usd"] or 0.0)
            total = round(total + cost, 6)
            batch_cost = round(batch_cost + cost, 6)
            counts["ran"] += 1
            if row["disposition"] == "draft_written":
                counts["written"] += 1
                if fixture.get("oracle") and run_dir is not None:
                    row.update(_score_draft(repo_root, fixture, record, run_dir))
                if run_dir is not None:
                    row["empty_descriptions"] = _empty_descriptions(Path(run_dir))
            elif technical:
                counts["technical"] += 1
            else:
                counts["failed"] += 1
                if _is_lost(row):
                    lost.add(label)
            dest = evidence_root / label / f"a{attempt:02d}"
            row["evidence_dir"] = (
                str(dest.relative_to(repo_root)) if dest.is_relative_to(repo_root) else str(dest)
            )
            if run_dir is not None:
                try:
                    files, dashes = copy_evidence(repo_root, Path(run_dir), dest)
                except E3Error as exc:
                    append_ledger(ledger, row)
                    print(f"SCREEN-STOP {arm_name} {label} a{attempt:02d}: {exc}; the attempt stays in the outbox only", file=out)
                    return 3
                counts["files"] += files
                counts["dashes"] += dashes
            append_ledger(ledger, row)
            done[key] = row
            high = " COST-HIGH" if cost > COST_HIGH_RATIO * estimate else ""
            agreement_cell = (
                f"{row['agree']}/{row['checked']}" if row["checked"] is not None else "-"
            )
            technical_note = (
                f" technical@{row['technical_attempt']}" if row["technical_attempt"] else ""
            )
            shared = row["shared_columns"] if row["shared_columns"] is not None else "-"
            print(
                f"RUN {arm_name} {label} a{attempt:02d} {row['disposition']}{technical_note} "
                f"attempts={row['attempts']} "
                f"lint@1={'yes' if row['first_attempt_lint_pass'] else 'no'} "
                f"grounded@1={'yes' if row['first_attempt_groundedness_pass'] else 'no'} "
                f"machine@1={row['machine_errors_at_1']} judgment@1={row['judgment_errors_at_1']} "
                f"agreement={agreement_cell} shared={shared} "
                f"in={row['input_tokens']} out={row['output_tokens']} cost={cost:.4f}{high}",
                file=out,
            )
            if label in lost:
                print(
                    f"LOST {arm_name} {label}: failed closed at a{attempt:02d}; its remaining attempts "
                    f"are not run unattended (D-10 Amendment G)",
                    file=out,
                )
                counts["lost"] += 1
                break
    print(
        f"BATCH {arm_name} {resolved.model_id}: runs={counts['ran']} written={counts['written']} "
        f"failed={counts['failed']} technical={counts['technical']} lost={counts['lost']} "
        f"skipped={counts['skipped']} cost={batch_cost:.4f} USD; ledger total {total:.4f} USD",
        file=out,
    )
    print(
        f"EVIDENCE {tag}: {counts['files']} file(s) copied under {arms['evidence_dir']}/{tag} "
        f"(screen: 0 refusal(s), {counts['dashes']} em dash(es) reported)",
        file=out,
    )
    return 0


def _ledger_row(repo_root, arms, arm_name, model_id, label, attempt, built, record) -> dict:
    spec = built["spec"]
    fixture = built["fixture"]
    prompt_meta, _ = harness.parse_prompt_front_matter(spec.prompt_path)
    context_hash = None
    if "context" in built["kwargs"]:
        context_hash = "sha256:" + hashlib.sha256(built["kwargs"]["context"].encode("utf-8")).hexdigest()
    first = _first_attempt(record)
    machine, judgment, structural = classify_errors(fixture["stance"], list(first.get("errors") or []))
    at = technical_attempt(record)
    row = dict.fromkeys(LEDGER_FIELDS)
    row.update(
        arm=arm_name, model=model_id, label=label, attempt=attempt, stance=fixture["stance"],
        prompt_version=str(prompt_meta["version"]), schema_digest=_schema_digest(spec.proposal_schema),
        context_hash=context_hash, technical=at == 1, technical_attempt=at, rerun=False, continued=False,
        disposition=record["disposition"], attempts=record["validation"]["attempts"],
        first_attempt_lint_pass=bool(first.get("lint_pass")),
        first_attempt_groundedness_pass=bool(first.get("groundedness_pass")),
        machine_errors_at_1=machine, judgment_errors_at_1=judgment, structural_at_1=structural,
        input_tokens=record["usage"]["input_tokens"], output_tokens=record["usage"]["output_tokens"],
        cost_usd=round(float(record["cost_usd_estimate"]), 6), created_at=record["created_at"],
        fields=len(agreement._MAPPING_FIELDS) if fixture["proposer"] == "mapping" else len(agreement._COLUMN_FIELDS),
    )
    return row


def _score_draft(repo_root: Path, fixture: dict, record: dict, run_dir: Path) -> dict:
    draft = yaml.safe_load(Path(record["draft_path"]).read_text(encoding="utf-8"))
    oracle = yaml.safe_load((repo_root / fixture["oracle"]).read_text(encoding="utf-8"))
    scorer = agreement.score_mapping if fixture["proposer"] == "mapping" else agreement.score
    result = scorer(draft, oracle)
    harness._replace_bytes(
        Path(run_dir) / "agreement.json",
        (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"),
    )
    first = result["first_class_checks"]
    columns = result.get("columns") or result.get("properties") or {}  # the mapping scorer names them properties
    grain = result.get("grain") or {}
    return {
        "agree": first["agree"], "checked": first["checked"], "mismatches": len(result["mismatches"]),
        "oracle_columns": columns.get("oracle"), "shared_columns": columns.get("shared"),
        "draft_columns": columns.get("draft"),
        "grain_set_equal": grain.get("set_equal"), "grain_order_equal": grain.get("order_equal"),
    }


def _empty_descriptions(run_dir: Path) -> int | None:
    path = run_dir / "proposal.json"
    if not path.exists():
        return None
    proposal = json.loads(path.read_text(encoding="utf-8"))
    columns = proposal.get("columns") or proposal.get("fields") or []
    if not any("description" in column for column in columns):
        return None  # the cleanup proposal carries rationales, no descriptions
    return sum(1 for column in columns if not str(column.get("description", "")).strip())


class _Captured(Exception):
    def __init__(self, kwargs: dict) -> None:
        self.kwargs = kwargs


class _CaptureClient:
    """Aborts at the API seam, before the harness writes anything."""

    def __init__(self) -> None:
        self.messages = self

    def create(self, **kwargs):  # noqa: ANN003
        raise _Captured(kwargs)


def _dry_run(repo_root, arms, arm_name, arm, resolved, out, model_flag) -> int:
    """The probe rule: what each fixture's call would carry, with no call,
    through the same harness call the live path makes."""
    for label in arm["fixtures"]:
        built = build_run(repo_root, arms, arm_name, label)
        try:
            harness.run_proposer(
                built["spec"], repo_root, model_flag=resolved.model_id if model_flag else None,
                client=_CaptureClient(), lint_runner=lambda p: (True, ""), quiet=True,
                **built["kwargs"],
            )
        except _Captured as captured:
            kw = captured.kwargs
        else:
            print(f"DRY {arm_name} {label}: the harness refused before the call", file=out)
            return 1
        content = kw["messages"][0]["content"]
        tags = re.findall(r"^<([a-z_]+)>$", content, flags=re.M)
        prompt_meta, body = harness.parse_prompt_front_matter(built["spec"].prompt_path)
        context_hash = "-"
        if "context" in built["kwargs"]:
            context_hash = hashlib.sha256(built["kwargs"]["context"].encode("utf-8")).hexdigest()[:16]
        print(
            f"DRY {arm_name} {label}: stance={built['fixture']['stance']} model={kw['model']} "
            f"prompt={built['spec'].prompt_path.relative_to(repo_root)}@{prompt_meta['version']} "
            f"schema={_schema_digest(built['spec'].proposal_schema)[7:23]} "
            f"skeleton={'yes' if built['spec'].skeleton else 'no'} tags={','.join(tags)} "
            f"context={context_hash} inputs={len(content)} system={len(kw['system'])} "
            f"user_sha={hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]}",
            file=out,
        )
    return 0


# ----------------------------------------------------------------- leakage

_TOKEN = re.compile(r"[a-z][a-z0-9_]*")


def leakage(repo_root: Path, out=None) -> list[dict]:
    """Per context file of a context-bearing fixture: the oracle's column
    names that appear in the text verbatim (as tokens), and the
    oracle-only names every underscore part of which is a token or a
    token's part in the text (composable: the parts are there and the
    conventions say how to join them, which is the mechanism under test).
    An observation; the test on the branch holds verbatim oracle-only
    names to zero and reports the composable count (KEY.md, Section 5)."""
    out = out or sys.stdout
    arms = load_arms(repo_root)
    results = []
    for fixture in arms["fixtures"]:
        if not fixture.get("context") or not fixture.get("oracle"):
            continue
        profile = json.loads((repo_root / fixture["profile"]).read_text(encoding="utf-8"))
        profile_names = {column["name"] for column in profile["dataset"]["columns"]}
        oracle = yaml.safe_load((repo_root / fixture["oracle"]).read_text(encoding="utf-8"))
        oracle_names = [prop["name"] for prop in oracle["schema"][0]["properties"]]
        oracle_only = [name for name in oracle_names if name not in profile_names]
        for key in ("context", "context_docs_only"):
            if not fixture.get(key):
                continue
            text = (repo_root / fixture[key]).read_text(encoding="utf-8")
            tokens = set(_TOKEN.findall(text.lower()))
            # The parts: every token and every underscore part of a token,
            # so `dep_delay` in the text supplies `dep` and `delay`.
            parts = {part for token in tokens for part in token.split("_") if part} | tokens
            shared = sorted(name for name in oracle_names if name in tokens and name in profile_names)
            only = sorted(name for name in oracle_only if name in tokens)
            composable = sorted(
                name for name in oracle_only
                if name not in tokens and all(part in parts for part in name.split("_") if part)
            )
            row = {
                "label": fixture["label"], "file": fixture[key], "context_chars": len(text),
                "oracle_columns": len(oracle_names), "oracle_only_columns": len(oracle_only),
                "shared_names_in_context": shared, "oracle_only_names_in_context": only,
                "oracle_only_names_composable": composable,
            }
            results.append(row)
            suffix = " docs-only" if key == "context_docs_only" else ""
            print(
                f"LEAKAGE {fixture['label']}{suffix}: {len(text)} chars; oracle {len(oracle_names)} columns, "
                f"{len(oracle_only)} not in the profile; shared names in the text {len(shared)}; "
                f"oracle-only names in the text {len(only)}" + (f" {only}" if only else "")
                + f"; composable from the text {len(composable)}",
                file=out,
            )
    return results


# ----------------------------------------------------------------- the scorer


def _median(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.median(values), 4) if values else None


def _frac(pair: tuple[int, int]) -> float | None:
    return pair[0] / pair[1] if pair[1] else None


def score(repo_root: Path, out=None, ledger: Path | None = None) -> dict:
    """Read the committed ledger and the committed evidence, never the
    outbox; write scores.json and scores.md beside the ledger; print the
    verdict lines by KEY.md Section 9."""
    out = out or sys.stdout
    arms = load_arms(repo_root)
    ledger = ledger or ledger_path(repo_root, arms)
    rows = read_ledger(ledger)
    by_label = fixtures_by_label(arms)
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for row in rows:
        groups.setdefault((row["arm"], row["model"], row["label"]), []).append(row)

    cells: dict[str, dict] = {}
    for (arm, model, label), group in sorted(groups.items()):
        results = [r for r in group if not r["technical"]]
        drafts = [r for r in results if r["disposition"] == "draft_written"]
        fixture = by_label[label]
        oracle_columns = next((r["oracle_columns"] for r in drafts if r.get("oracle_columns")), None)
        fields = next((r["fields"] for r in results if r.get("fields")), None)
        denominator = (fields * oracle_columns) if fields and oracle_columns else None
        fractions = [((r["agree"] / r["checked"]) if r.get("checked") else 0.0) for r in results]
        normalized = [
            ((r["agree"] / denominator) if denominator and r.get("agree") is not None else 0.0)
            for r in results
        ]
        first_only = [r for r in results if r["attempts"] == 1]
        n = len(results)
        cell = {
            "arm": arm, "model": model, "label": label, "stance": fixture["stance"],
            "n": n, "technical": len(group) - n, "unresolved": n < CELL_FLOOR,
            "written": len(drafts),
            "failed_closed": sum(1 for r in results if r["disposition"] == "failed_closed"),
            "technical_on_retry": sum(1 for r in results if r.get("technical_attempt")),
            "lint_at_1": sum(1 for r in results if r["first_attempt_lint_pass"]),
            "grounded_at_1": sum(1 for r in results if r["first_attempt_groundedness_pass"]),
            "machine_at_1_runs": sum(1 for r in results if r["machine_errors_at_1"]),
            "machine_at_1_errors": sum(r["machine_errors_at_1"] for r in results),
            "judgment_at_1_runs": sum(1 for r in results if r["judgment_errors_at_1"]),
            "structural_at_1_runs": sum(1 for r in results if r["structural_at_1"]),
            "fraction_median": _median(fractions), "fraction_min": min(fractions) if fractions else None,
            "fraction_max": max(fractions) if fractions else None,
            "oracle_columns": oracle_columns, "fields": fields,
            "normalized_median": _median(normalized),
            "normalized_min": min(normalized) if normalized else None,
            "normalized_max": max(normalized) if normalized else None,
            "checked_median": _median([r["checked"] if r.get("checked") is not None else 0 for r in results]),
            "shared_median": _median([r["shared_columns"] if r.get("shared_columns") is not None else 0 for r in results]),
            "shared_min": min((r.get("shared_columns") or 0) for r in results) if results else None,
            "shared_max": max((r.get("shared_columns") or 0) for r in results) if results else None,
            "mismatches_median": _median([r.get("mismatches") for r in drafts]),
            "grain_set_equal": sum(1 for r in drafts if r.get("grain_set_equal")),
            "grain_order_equal": sum(1 for r in drafts if r.get("grain_order_equal")),
            "empty_descriptions": sum(int(r.get("empty_descriptions") or 0) for r in drafts),
            "input_tokens_median": _median([r["input_tokens"] for r in results]),
            "output_tokens_median": _median([r["output_tokens"] for r in results]),
            "n_first_attempt_only": len(first_only),
            "output_tokens_first_attempt_median": _median([r["output_tokens"] for r in first_only]),
            "cost_usd": round(sum(float(r["cost_usd"] or 0) for r in group), 4),
        }
        cells[f"{arm}|{model}|{label}"] = cell

    default = arms["default_model"]

    def cell(arm, label, model=default):
        return cells.get(f"{arm}|{model}|{label}")

    def resolved(arm, labels, model=default):
        return all(cell(arm, lab, model) and not cell(arm, lab, model)["unresolved"] for lab in labels)

    def rate(arm, labels, field, model=default):
        ran = sum((cell(arm, lab, model) or {}).get("n", 0) for lab in labels)
        hit = sum((cell(arm, lab, model) or {}).get(field, 0) for lab in labels)
        return (hit, ran)

    def rate_not_below(mine, theirs) -> bool | None:
        # Within one attempt's worth of the measured side: not a failure.
        if _frac(mine) is None or _frac(theirs) is None:
            return None
        return _frac(mine) >= _frac(theirs) - 1.0 / mine[1]

    def median_below(mine: dict, theirs: dict) -> bool:
        # Below by more than one field's worth of the oracle: a failure.
        a, b = mine["normalized_median"], theirs["normalized_median"]
        if a is None or b is None:
            return False
        denominator = ((mine["fields"] or 0) * (mine["oracle_columns"] or 0)) or (
            (theirs["fields"] or 0) * (theirs["oracle_columns"] or 0)
        )
        tolerance = (1.0 / denominator) if denominator else 0.0
        return a < b - tolerance

    zero_fixtures = list(arms["zero_fixtures"])
    a_fixtures = arms["arms"]["A"]["fixtures"]
    a_other = [lab for lab in a_fixtures if lab not in zero_fixtures]
    b_fixtures = arms["arms"]["B"]["fixtures"]
    verdict: dict[str, Any] = {}

    # E3a
    have_a = resolved("A", a_fixtures) and resolved("baseline", a_fixtures)
    have_a0 = resolved("A0", zero_fixtures)
    r1 = [lab for lab in zero_fixtures if ((cell("A", lab) or {}).get("checked_median") or 0) > 0]
    r2_fail = [
        lab for lab in a_other
        if cell("A", lab) and cell("baseline", lab) and median_below(cell("A", lab), cell("baseline", lab))
    ]
    lint_a, grounded_a = rate("A", a_fixtures, "lint_at_1"), rate("A", a_fixtures, "grounded_at_1")
    lint_b, grounded_b = rate("baseline", a_fixtures, "lint_at_1"), rate("baseline", a_fixtures, "grounded_at_1")
    a0 = {lab: (cell("A0", lab) or {}).get("checked_median") for lab in zero_fixtures}
    a0_alone = sum(1 for v in a0.values() if v and v > 0) >= 2
    e3a = {
        "measured": bool(have_a and have_a0),
        "unresolved_cells": sorted(
            k for k, c in cells.items() if c["unresolved"] and c["model"] == default
            and c["arm"] in ("A", "A0", "baseline") and c["label"] in a_fixtures
        ),
        "rule1_fixtures_off_zero": r1,
        "rule1_shared_median": {lab: (cell("A", lab) or {}).get("shared_median") for lab in zero_fixtures},
        "rule1_shared_range": {
            lab: [(cell("A", lab) or {}).get("shared_min"), (cell("A", lab) or {}).get("shared_max")]
            for lab in zero_fixtures
        },
        "rule1": len(r1) >= 2,
        "rule2_fixtures_below_baseline": r2_fail,
        "rule2_compared": a_other,
        "rule2": not r2_fail,
        "rule3_lint": [lint_a, lint_b], "rule3_grounded": [grounded_a, grounded_b],
        "rule3": bool(rate_not_below(lint_a, lint_b) and rate_not_below(grounded_a, grounded_b)),
        "rule4_a0_checked_median": a0,
        "rule4_a0_alone_satisfies_rule1": a0_alone,
        "rule4": not a0_alone,
        "a1_docs_only_checked_median": {lab: (cell("A1", lab) or {}).get("checked_median") for lab in zero_fixtures},
        "a1_docs_only_shared_median": {lab: (cell("A1", lab) or {}).get("shared_median") for lab in zero_fixtures},
    }
    e3a["earned"] = bool(e3a["measured"] and e3a["rule1"] and e3a["rule2"] and e3a["rule3"] and e3a["rule4"])
    verdict["E3a"] = e3a

    # E3b
    have_b = resolved("B", b_fixtures) and resolved("B-baseline", b_fixtures)
    machine_b = sum((cell("B", lab) or {}).get("machine_at_1_errors", 0) for lab in b_fixtures)
    machine_bb = sum((cell("B-baseline", lab) or {}).get("machine_at_1_errors", 0) for lab in b_fixtures)
    machine_bb_runs = sum((cell("B-baseline", lab) or {}).get("machine_at_1_runs", 0) for lab in b_fixtures)
    judgment = {}
    rule2 = True
    for stance in ("describe", "amend"):
        labs = [lab for lab in b_fixtures if by_label[lab]["stance"] == stance]
        jb, jbb = rate("B", labs, "judgment_at_1_runs"), rate("B-baseline", labs, "judgment_at_1_runs")
        judgment[stance] = [jb, jbb]
        if _frac(jb) is not None and _frac(jbb) is not None and _frac(jb) > _frac(jbb) + 1.0 / jb[1]:
            rule2 = False
    r3_fail = [
        lab for lab in b_fixtures
        if cell("B", lab) and cell("B-baseline", lab) and median_below(cell("B", lab), cell("B-baseline", lab))
    ]
    split = {}
    for lab in b_fixtures:
        cb, cbb = cell("B", lab) or {}, cell("B-baseline", lab) or {}
        ob, obb = cb.get("output_tokens_first_attempt_median"), cbb.get("output_tokens_first_attempt_median")
        split[lab] = {
            "B_output_tokens_first_attempt_median": ob,
            "B_baseline_output_tokens_first_attempt_median": obb,
            "B_first_attempt_runs": cb.get("n_first_attempt_only"),
            "B_baseline_first_attempt_runs": cbb.get("n_first_attempt_only"),
            "output_token_saving": round(1 - ob / obb, 4) if ob and obb else None,
            "structure_share_chars_median": _structure_share(repo_root, rows, lab),
        }
    e3b = {
        "measured": bool(have_b),
        "unresolved_cells": sorted(
            k for k, c in cells.items() if c["unresolved"] and c["arm"] in ("B", "B-baseline")
        ),
        "rule1_machine_errors_B": machine_b,
        "rule1_machine_errors_B_baseline": machine_bb,
        "rule1_machine_runs_B_baseline": machine_bb_runs,
        "rule1": machine_b == 0,
        "rule2_judgment_runs": judgment, "rule2": rule2,
        "rule3_fixtures_below_B_baseline": r3_fail, "rule3": not r3_fail,
        "rule3_grain_set_equal": {
            lab: [(cell("B", lab) or {}).get("grain_set_equal"), (cell("B-baseline", lab) or {}).get("grain_set_equal")]
            for lab in b_fixtures
        },
        "empty_descriptions": {
            lab: [(cell("B", lab) or {}).get("empty_descriptions"), (cell("B-baseline", lab) or {}).get("empty_descriptions")]
            for lab in b_fixtures
        },
        "rule4_token_split": split,
        "rule4": bool(have_b and all(v["output_token_saving"] is not None for v in split.values())),
    }
    e3b["earned"] = bool(e3b["measured"] and e3b["rule1"] and e3b["rule2"] and e3b["rule3"] and e3b["rule4"])
    verdict["E3b"] = e3b

    scores = {"cells": cells, "verdict": verdict, "ledger_rows": len(rows), "ledger_total_usd": ledger_total(rows)}
    base = ledger.parent
    harness._replace_bytes(base / "scores.json", (json.dumps(scores, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    harness._replace_bytes(base / "scores.md", render_scores_markdown(scores).encode("utf-8"))
    for name in ("E3a", "E3b"):
        v = verdict[name]
        state = "not measured" if not v["measured"] else ("earned" if v["earned"] else "not earned")
        print(f"VERDICT {name}: {state}", file=out)
    print(f"SCORES {len(cells)} cell(s) over {len(rows)} ledger row(s); ledger total {ledger_total(rows):.4f} USD", file=out)
    return scores


def _structure_share(repo_root: Path, rows: list[dict], label: str) -> float | None:
    """The machine half's share of every written B-baseline proposal for
    the fixture (compact-JSON characters, the September 17 method), read
    from the committed evidence; the median."""
    shares = []
    for row in rows:
        if row["arm"] != "B-baseline" or row["label"] != label or row["disposition"] != "draft_written":
            continue
        path = repo_root / row["evidence_dir"] / "proposal.json"
        if not path.exists():
            continue
        proposal = json.loads(path.read_text(encoding="utf-8"))
        machine, total = skeleton.machine_half_chars(proposal)
        if total:
            shares.append(machine / total)
    return _median(shares)


def render_scores_markdown(scores: dict) -> str:
    lines = [
        "# E3 scores", "",
        f"- ledger rows: {scores['ledger_rows']}; ledger total: ${scores['ledger_total_usd']:.4f}",
        "",
        "| arm | model | fixture | n | written | failed | lint@1 | grounded@1 | machine@1 runs | judgment@1 runs | structural@1 runs | agreement median (min, max) | normalized median | shared median (min, max) | mismatches median | grain set equal | empty descriptions | out tokens median (first-attempt runs) | cost |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for key in sorted(scores["cells"]):
        c = scores["cells"][key]
        agreement_cell = "-" if c["fraction_median"] is None else f"{c['fraction_median']} ({c['fraction_min']}, {c['fraction_max']})"
        shared = "-" if c["shared_median"] is None else f"{c['shared_median']} ({c['shared_min']}, {c['shared_max']})"
        lines.append(
            f"| {c['arm']} | {c['model']} | {c['label']} | {c['n']}{' (unresolved)' if c['unresolved'] else ''} | {c['written']} | {c['failed_closed']} "
            f"| {c['lint_at_1']} | {c['grounded_at_1']} | {c['machine_at_1_runs']} | {c['judgment_at_1_runs']} "
            f"| {c['structural_at_1_runs']} | {agreement_cell} | {c['normalized_median']} | {shared} | {c['mismatches_median']} "
            f"| {c['grain_set_equal']} | {c['empty_descriptions']} "
            f"| {c['output_tokens_median']} ({c['output_tokens_first_attempt_median']}) | ${c['cost_usd']:.4f} |"
        )
    lines += ["", "## Verdict", "", "```json", json.dumps(scores["verdict"], indent=2, sort_keys=True), "```", ""]
    return "\n".join(lines)
