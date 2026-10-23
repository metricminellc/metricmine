"""Render the E3 finding's measured sections from the committed evidence.

    uv run python docs/experiments/e3/render_finding.py \
        --key-commit <sha> --bounds bounds.md --possible possible.md \
        --out docs/experiments/e3-skeleton-and-context.md

Every number in the record comes from `scores.json` and `ledger.jsonl`
(written by `make e3-score` and the arm runner) and from the leakage
counter over the committed context files; none is typed. The two
narrative sections ("What the result bounds", "What remains possible")
are read from the files named, written by a person after the numbers
exist; the script refuses to render when either is missing or empty,
when `scores.json` is missing, or when a question is unmeasured and not
named in `--allow-unmeasured`. Experiment branch only
(docs/experiments/e3/KEY.md); the finding lands on main by its own
documentation pull request.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))

from metricmine.agents import e3  # noqa: E402



def _load(path: Path, what: str) -> str:
    if not path.is_file():
        raise SystemExit(f"error: {what} {path} does not exist; the finding is not rendered")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit(f"error: {what} {path} is empty; the finding is not rendered")
    return text + "\n"


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".") if value != int(value) else str(int(value))
    return str(value)


def _cell_rows(cells: dict, arm: str, model: str) -> list[dict]:
    return sorted(
        (c for c in cells.values() if c["arm"] == arm and c["model"] == model),
        key=lambda c: c["label"],
    )


def _arm_table(cells: dict, arm: str, model: str) -> list[str]:
    rows = _cell_rows(cells, arm, model)
    if not rows:
        return [f"No ledger row for `{arm}` at `{model}`."]
    lines = [
        "| Fixture | n | written | failed closed | technical | lint at 1 | grounded at 1 | machine at 1 (runs, errors) | judgment at 1 (runs) | agreement median (min, max) | normalized median | shared names median (min, max) | mismatches median | grain set equal | empty descriptions | out tokens median (first-attempt runs) | cost |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in rows:
        agreement = "-" if c["fraction_median"] is None else f"{_fmt(c['fraction_median'])} ({_fmt(c['fraction_min'])}, {_fmt(c['fraction_max'])})"
        shared = "-" if c["shared_median"] is None else f"{_fmt(c['shared_median'])} ({_fmt(c['shared_min'])}, {_fmt(c['shared_max'])})"
        n = f"{c['n']} (unresolved)" if c["unresolved"] else str(c["n"])
        lines.append(
            f"| `{c['label']}` | {n} | {c['written']} | {c['failed_closed']} | {c['technical']} "
            f"| {c['lint_at_1']} | {c['grounded_at_1']} | {c['machine_at_1_runs']}, {c['machine_at_1_errors']} "
            f"| {c['judgment_at_1_runs']} | {agreement} | {_fmt(c['normalized_median'])} | {shared} "
            f"| {_fmt(c['mismatches_median'])} | {c['grain_set_equal']} | {c['empty_descriptions']} "
            f"| {_fmt(c['output_tokens_median'])} ({_fmt(c['output_tokens_first_attempt_median'])}) | ${c['cost_usd']:.4f} |"
        )
    return lines


def render(repo_root: Path, *, key_commit: str, bounds: str, possible: str, allow_unmeasured: set[str], today: str) -> str:
    arms = e3.load_arms(repo_root)
    e3_dir = repo_root / "docs" / "experiments" / "e3"
    scores_path = e3_dir / "scores.json"
    if not scores_path.is_file():
        raise SystemExit(f"error: {scores_path} does not exist; run make e3-score first")
    scores = json.loads(scores_path.read_text(encoding="utf-8"))
    rows = e3.read_ledger(e3_dir / "ledger.jsonl")
    if not rows:
        raise SystemExit("error: the ledger is empty; nothing was measured")
    verdict = scores["verdict"]
    for name in ("E3a", "E3b"):
        if not verdict[name]["measured"] and name not in allow_unmeasured:
            raise SystemExit(f"error: {name} is not measured and --allow-unmeasured does not name it")
    cells = scores["cells"]
    default = arms["default_model"]
    stamps = sorted(r["created_at"] for r in rows)
    first_day, last_day = stamps[0][:10], stamps[-1][:10]
    models_run = sorted({r["model"] for r in rows})

    out: list[str] = []
    out += [
        f"# E3, the skeleton and the context channel: measured ({today})",
        "",
        "> Repo path: `docs/experiments/e3-skeleton-and-context.md`",
        "> An experiments-lane record (CLAUDE.md rule 19). It mints no decision",
        "> and no finding. The two proposers, their prompts on main, the",
        "> validators, the scorer, and the eval lane at head are unchanged; the",
        "> experiment ran on the branch `experiment/e3-skeleton-and-context`",
        f"> under the key committed at `{key_commit}` (`docs/experiments/e3/KEY.md`",
        "> on that branch), which fixed every rule below before the first run.",
        "",
        "## The question",
        "",
        "E3a: does a few sentences of operator context, bound as one more",
        "governed input and rendered as data, move the cleanup proposer off",
        "the three `0/0` fixtures of the Arc 6 agreement study without",
        "regressing the other eight? E3b: when code writes the machine half",
        "of a describe or amend proposal and the model emits only the judgment",
        "over it, do the first-attempt machine-half failures go to zero",
        "without the judgment failures rising, and how many of the output",
        "tokens were structure? The key states both as measurable claims",
        "(Section 1) and the verdict rule per question (Section 9).",
        "",
        "## The rule",
        "",
        "E3a is earned when, over ten repeats at the pinned model, at least",
        "two of the three `0/0` fixtures reach a nonzero checked set under",
        "arm A (rule 1), no comparable fixture's oracle-normalized agreement",
        "median under A falls below its baseline median by more than one",
        "field's worth (rule 2), the first-attempt lint and groundedness",
        "rates under A are not below the baseline's by more than one",
        "attempt's worth (rule 3), and the prompt-only control A0 does not",
        "satisfy rule 1 on its own (rule 4). E3b is earned when the",
        "first-attempt machine-half errors under arm B are zero (rule 1, held",
        "by construction and checked), the judgment-error rate under B is not",
        "above the B-baseline's per stance by more than one attempt's worth",
        "(rule 2), no fixture's oracle-normalized agreement median under B",
        "falls below the B-baseline's by more than one field's worth (rule",
        "3), and the output-token split is measurable on every fixture over",
        "first-attempt runs (rule 4). A cell with fewer than five results",
        "decides no rule: the question is then not measured. A technical",
        "failure at attempt 1 is not a result; a fixture whose latest result",
        "failed closed lost its remaining attempts unless a person continued it",
        "by name (D-10 Amendment G). The scorer is `agreement.py` at head,",
        "unchanged; the oracle-normalized measure divides its agree count by",
        "the oracle's column count times its field count.",
        "",
        "## What was measured",
        "",
        f"Models: {', '.join(f'`{m}`' for m in models_run)} (the baseline arm",
        f"alone ran at a model other than `{default}`, the D-34 override).",
        f"Runs: {len(rows)} ledger rows from {first_day} to {last_day}; ledger total",
        f"${scores['ledger_total_usd']:.4f} against the bound ${arms['spend_bound_usd']:.2f}.",
        "The live calls ran on the operator's machine by the runbook with",
        "`ANTHROPIC_API_KEY` in the environment; the sandbox ran nothing live.",
        "",
        "| Arm | Model | Rows | Results | Technical | Failed closed | Cost |",
        "|---|---|---|---|---|---|---|",
    ]
    by_arm: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        by_arm.setdefault((r["arm"], r["model"]), []).append(r)
    for (arm, model), group in sorted(by_arm.items()):
        results = [r for r in group if not r["technical"]]
        out.append(
            f"| `{arm}` | `{model}` | {len(group)} | {len(results)} | {len(group) - len(results)} "
            f"| {sum(1 for r in results if r['disposition'] == 'failed_closed')} "
            f"| ${e3.ledger_total(group):.4f} |"
        )
    out += ["", "The leakage count over the committed context files, as the lane prints it:", ""]
    for row in e3.leakage(repo_root, out=io.StringIO()):
        docs_only = " (docs-only)" if "docs-only" in row["file"] else ""
        out.append(
            f"- `{row['label']}`{docs_only}: {row['context_chars']} characters; oracle {row['oracle_columns']} columns, "
            f"{row['oracle_only_columns']} not in the profile; shared names in the text {len(row['shared_names_in_context'])}; "
            f"oracle-only names in the text {len(row['oracle_only_names_in_context'])}; "
            f"composable from the text {len(row['oracle_only_names_composable'])}"
        )
    out += ["", "## The result, as measured", ""]
    for arm, model in (("baseline", default), ("A", default), ("A0", default), ("A1", default), ("B-baseline", default), ("B", default)):
        out += [f"### Arm `{arm}` at `{model}`", ""] + _arm_table(cells, arm, model) + [""]
    for model in models_run:
        if model != default:
            out += [f"### The model control: `baseline` at `{model}`", ""] + _arm_table(cells, "baseline", model) + [""]

    a = verdict["E3a"]
    out += ["### E3a by the rule", ""]
    if not a["measured"]:
        out += [
            "Not measured: the ledger lacks arm A, A0, or the baseline on at least one fixture, or a cell is below "
            f"the floor of five results: {', '.join(f'`{x}`' for x in a['unresolved_cells']) or 'none unresolved'}.",
            "",
        ]
    else:
        out += [
            f"- Rule 1: fixtures off `0/0` under A: {', '.join(f'`{x}`' for x in a['rule1_fixtures_off_zero']) or 'none'} "
            f"({'met' if a['rule1'] else 'not met'}; two of three required).",
            "- Rule 1, the shared names under A, median (min, max): "
            + ", ".join(f"`{k}` {_fmt(v)} ({_fmt(a['rule1_shared_range'][k][0])}, {_fmt(a['rule1_shared_range'][k][1])})" for k, v in a["rule1_shared_median"].items())
            + ".",
            f"- Rule 2 (over {', '.join(f'`{x}`' for x in a['rule2_compared'])}; the three `0/0` fixtures have no baseline agreement to fall below): "
            f"fixtures whose normalized median fell below the baseline's by more than one field's worth: "
            f"{', '.join(f'`{x}`' for x in a['rule2_fixtures_below_baseline']) or 'none'} ({'met' if a['rule2'] else 'not met'}).",
            f"- Rule 3: first-attempt lint A {a['rule3_lint'][0][0]}/{a['rule3_lint'][0][1]} against baseline {a['rule3_lint'][1][0]}/{a['rule3_lint'][1][1]}; "
            f"groundedness A {a['rule3_grounded'][0][0]}/{a['rule3_grounded'][0][1]} against baseline {a['rule3_grounded'][1][0]}/{a['rule3_grounded'][1][1]} "
            f"({'met' if a['rule3'] else 'not met'}).",
            "- Rule 4, the prompt-only control `A0` (the e3 prompt, no context): checked median per `0/0` fixture "
            + ", ".join(f"`{k}` {_fmt(v)}" for k, v in a["rule4_a0_checked_median"].items())
            + f"; A0 alone {'would' if a['rule4_a0_alone_satisfies_rule1'] else 'would not'} satisfy rule 1 "
            + f"({'met' if a['rule4'] else 'not met'}).",
            "- Reported, never a condition: the docs-only control `A1` (the context without its conventions sentences): "
            "checked median per `0/0` fixture "
            + ", ".join(f"`{k}` {_fmt(v)}" for k, v in a["a1_docs_only_checked_median"].items())
            + "; shared names median "
            + ", ".join(f"`{k}` {_fmt(v)}" for k, v in a["a1_docs_only_shared_median"].items())
            + ".",
            f"- **E3a: {'earned' if a['earned'] else 'not earned'}.**",
            "",
        ]
    b = verdict["E3b"]
    out += ["### E3b by the rule", ""]
    if not b["measured"]:
        out += [
            "Not measured: the ledger lacks arm B or the B-baseline on at least one of the three fixtures, or a cell is "
            f"below the floor of five results: {', '.join(f'`{x}`' for x in b['unresolved_cells']) or 'none unresolved'}.",
            "",
        ]
    else:
        judgment = b["rule2_judgment_runs"]
        out += [
            f"- Rule 1 (held by construction; checked): first-attempt machine-half errors under B {b['rule1_machine_errors_B']}; "
            f"under B-baseline {b['rule1_machine_errors_B_baseline']} errors over {b['rule1_machine_runs_B_baseline']} runs, "
            f"the failures the skeleton removes ({'met' if b['rule1'] else 'not met'}).",
            "- Rule 2: runs with a judgment error at attempt 1, B against B-baseline: "
            + "; ".join(f"{stance} {v[0][0]}/{v[0][1]} against {v[1][0]}/{v[1][1]}" for stance, v in judgment.items())
            + f" ({'met' if b['rule2'] else 'not met'}).",
            f"- Rule 3: fixtures whose normalized median under B fell below the B-baseline's by more than one field's worth: "
            f"{', '.join(f'`{x}`' for x in b['rule3_fixtures_below_B_baseline']) or 'none'} ({'met' if b['rule3'] else 'not met'}). "
            "Grain set equal (drafts, B against B-baseline): "
            + "; ".join(f"`{lab}` {v[0]} against {v[1]}" for lab, v in b["rule3_grain_set_equal"].items())
            + ". Empty descriptions (B against B-baseline): "
            + "; ".join(f"`{lab}` {v[0]} against {v[1]}" for lab, v in b["empty_descriptions"].items())
            + ".",
            "- Rule 4, the token split over first-attempt runs (output tokens median, B against B-baseline, the "
            "output-token saving, and the machine half's character share of the B-baseline proposals): "
            + "; ".join(
                f"`{lab}` {_fmt(v['B_output_tokens_first_attempt_median'])} against {_fmt(v['B_baseline_output_tokens_first_attempt_median'])} "
                f"over {_fmt(v['B_first_attempt_runs'])} and {_fmt(v['B_baseline_first_attempt_runs'])} runs, saving {_fmt(v['output_token_saving'])}, "
                f"structure share {_fmt(v['structure_share_chars_median'])}"
                for lab, v in b["rule4_token_split"].items()
            )
            + f" ({'met' if b['rule4'] else 'not met'}).",
            f"- **E3b: {'earned' if b['earned'] else 'not earned'}.**",
            "",
        ]
    out += ["## What the result bounds", "", bounds, "## What remains possible", "", possible, "## Status", ""]
    out += [
        "Nothing graduates by this record. The branch stays as it ran; the",
        "evidence of every attempt is committed under `docs/experiments/e3/runs/`",
        "on the branch with the ledger and the scores, screened before it was",
        "copied. A graduation of either question is a later prep that mints its",
        "amendments (D-21, D-22, D-23, D-35) by their own documentation pull",
        "request and lands the code in the form it ran here (KEY.md, Section 10).",
        "",
    ]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--key-commit", required=True, help="the short sha of the key's commit on the branch")
    parser.add_argument("--bounds", required=True, type=Path, help="markdown for 'What the result bounds'")
    parser.add_argument("--possible", required=True, type=Path, help="markdown for 'What remains possible'")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--allow-unmeasured", default="", help="comma-separated question names allowed to be unmeasured (E3a, E3b)")
    parser.add_argument("--today", default=datetime.now().date().isoformat())
    parser.add_argument("--repo", default=str(REPO), type=Path)
    args = parser.parse_args(argv)
    text = render(
        args.repo, key_commit=args.key_commit, bounds=_load(args.bounds, "the bounds section"),
        possible=_load(args.possible, "the possible section"),
        allow_unmeasured={x.strip() for x in args.allow_unmeasured.split(",") if x.strip()}, today=args.today,
    )
    refusals, dashes = e3.screen_text(text)
    if refusals or dashes:
        raise SystemExit(f"error: the rendered finding fails the screen: {refusals or ''} {dashes} em dash(es)")
    args.out.write_text(text, encoding="utf-8")
    print(f"rendered {args.out} ({len(text.splitlines())} lines, {len(text)} characters)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
