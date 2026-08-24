"""The live evaluation lane over the golden-profile set (D-25, D-34).

Spec: docs/spec/agent-layer.md §5. `make eval-agents` runs the proposers
against the configured fixtures (agents.eval.fixtures in
config/default.yaml) when a key is present and reports the first-attempt
lint pass rate and the first-attempt groundedness pass rate with token
and cost actuals. "First attempt" is read from each record's
validation.attempt_log[0]: lint passes only when the first attempt
reached lint and lint passed; groundedness passes only when the first
attempt parsed and carried no groundedness error; a fixture refused
before any call scores false on both. The lane honors the D-34 override
(--model, then MM_PROPOSER_MODEL, then the pinned default), so a model
comparison is one command; comparing is enabled, not performed. Every
call is the ordinary harness call: one structured call per fixture, the
same retry budget, the same outbox. The report lands under
<outbox_dir>/eval/<stamp>_<model>/ and prints to stdout. Exit 0 when
every fixture wrote a draft, 2 when any failed closed (the report is
still written), 1 on a precondition.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from metricmine.agents import (
    harness,
    mapping_proposer,
    models,
    silver_proposer,
)

BUILDERS = {
    "silver": silver_proposer.build_spec,
    "mapping": mapping_proposer.build_spec,
}


def load_fixtures(repo_root: Path) -> list[dict]:
    return list(harness.load_agents_config(repo_root)["eval"]["fixtures"])


def _first_attempt(record: dict) -> tuple[bool, bool]:
    log = record["validation"].get("attempt_log") or []
    if not log:
        return False, False
    first = log[0]
    return bool(first.get("lint_pass")), bool(first.get("groundedness_pass"))


def run_eval(
    repo_root: Path,
    *,
    model_flag: str | None = None,
    labels: list[str] | None = None,
    client: Any = None,
    lint_runner: harness.LintRunner | None = None,
    now: datetime | None = None,
) -> int:
    try:
        resolved = models.resolve_model(model_flag)
    except models.ModelNotAllowedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if client is None and not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "error: ANTHROPIC_API_KEY is not set; the eval lane is the live "
            "lane (make demo and the test lane never need it)",
            file=sys.stderr,
        )
        return 1
    fixtures = load_fixtures(repo_root)
    if labels:
        fixtures = [f for f in fixtures if f["label"] in labels]
        if not fixtures:
            print(f"error: no fixture matches {labels}", file=sys.stderr)
            return 1

    now = now or datetime.now(timezone.utc)
    rows: list[dict] = []
    worst = 0
    for fixture in fixtures:
        spec = BUILDERS[fixture["proposer"]](repo_root)
        report: dict = {}
        code = harness.run_proposer(
            spec,
            repo_root,
            profile=str(repo_root / fixture["profile"]),
            model_flag=model_flag,
            client=client,
            lint_runner=lint_runner,
            now=now,
            report=report,
            quiet=True,
        )
        worst = max(worst, code)
        record = report.get("record")
        if record is None:
            rows.append(
                {
                    "label": fixture["label"],
                    "proposer": spec.name,
                    "stance": spec.stance,
                    "profile": fixture["profile"],
                    "exit": code,
                    "disposition": "refused",
                }
            )
            continue
        lint_first, grounded_first = _first_attempt(record)
        rows.append(
            {
                "label": fixture["label"],
                "proposer": spec.name,
                "stance": spec.stance,
                "profile": fixture["profile"],
                "profile_hash": record["profile_hash"],
                "exit": code,
                "disposition": record["disposition"],
                "attempts": record["validation"]["attempts"],
                "first_attempt_lint_pass": lint_first,
                "first_attempt_groundedness_pass": grounded_first,
                "input_tokens": record["usage"]["input_tokens"],
                "output_tokens": record["usage"]["output_tokens"],
                "cost_usd_estimate": record["cost_usd_estimate"],
                "prompt_version": record["prompt_version"],
                "run_dir": str(report["run_dir"].relative_to(repo_root)),
            }
        )

    total = len(rows)
    lint_n = sum(1 for r in rows if r.get("first_attempt_lint_pass"))
    grounded_n = sum(
        1 for r in rows if r.get("first_attempt_groundedness_pass")
    )
    summary = {
        "created_at": now.isoformat(),
        "model_id": resolved.model_id,
        "model_source": resolved.source,
        "rates": asdict(models.MODELS[resolved.model_id]),
        "sdk_version": anthropic.__version__,
        "fixtures": total,
        "drafts_written": sum(
            1 for r in rows if r["disposition"] == "draft_written"
        ),
        "first_attempt_lint_pass_rate": f"{lint_n}/{total}",
        "first_attempt_groundedness_pass_rate": f"{grounded_n}/{total}",
        "input_tokens": sum(r.get("input_tokens", 0) for r in rows),
        "output_tokens": sum(r.get("output_tokens", 0) for r in rows),
        "cost_usd_estimate": round(
            sum(r.get("cost_usd_estimate", 0.0) for r in rows), 6
        ),
        "exit": worst,
        "rows": rows,
    }

    eval_dir = (
        repo_root
        / harness.load_agents_config(repo_root)["outbox_dir"]
        / "eval"
        / f"{now.strftime('%Y%m%dT%H%M%SZ')}_{resolved.model_id}"
    )
    eval_dir.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown(summary)
    harness._replace_bytes(
        eval_dir / "report.json",
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    harness._replace_bytes(eval_dir / "report.md", markdown.encode("utf-8"))
    sys.stdout.write(markdown)
    print(f"report: {eval_dir / 'report.md'}")
    return worst


def render_markdown(summary: dict) -> str:
    lines = [
        "# eval-agents report",
        "",
        f"- created_at: {summary['created_at']}",
        f"- model: {summary['model_id']} ({summary['model_source']}); rates "
        f"{summary['rates']['input_per_mtok']}/"
        f"{summary['rates']['output_per_mtok']} USD per MTok; "
        f"sdk {summary['sdk_version']}",
        f"- fixtures: {summary['fixtures']}; "
        f"drafts written: {summary['drafts_written']}",
        f"- first-attempt lint pass rate: "
        f"{summary['first_attempt_lint_pass_rate']}",
        f"- first-attempt groundedness pass rate: "
        f"{summary['first_attempt_groundedness_pass_rate']}",
        f"- tokens: in {summary['input_tokens']}, "
        f"out {summary['output_tokens']}; "
        f"cost ~${summary['cost_usd_estimate']:.4f}",
        "",
        "| label | proposer | stance | disposition | attempts | lint@1 "
        "| grounded@1 | in | out | cost |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in summary["rows"]:
        if "attempts" not in r:
            lines.append(
                f"| {r['label']} | {r['proposer']} | {r['stance']} "
                f"| {r['disposition']} | - | - | - | - | - | - |"
            )
            continue
        lines.append(
            f"| {r['label']} | {r['proposer']} | {r['stance']} "
            f"| {r['disposition']} | {r['attempts']} "
            f"| {'yes' if r['first_attempt_lint_pass'] else 'no'} "
            f"| {'yes' if r['first_attempt_groundedness_pass'] else 'no'} "
            f"| {r['input_tokens']} | {r['output_tokens']} "
            f"| ${r['cost_usd_estimate']:.4f} |"
        )
    lines.append("")
    return "\n".join(lines)
