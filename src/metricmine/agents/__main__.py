"""CLI: propose silver | propose mapping | propose describe (D-24, D-35).

Spec: docs/spec/agent-layer.md §4. The interaction surface is the CLI,
the editor, and the pull request; this module is the CLI half of
propose. It refuses to run without the stance's prompt file (the prompt
PR lands the bodies) and honors the D-34 model override via --model.
`--help` works keyless; no client is constructed before the harness
preconditions pass.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from metricmine.agents import agreement
from metricmine.agents import eval as eval_lane
from metricmine.agents import harness, mapping_proposer, silver_proposer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m metricmine.agents",
        description=(
            "Run a proposer against the newest committed profile artifact "
            "and write a draft contract plus its record to the gitignored "
            "proposals/ outbox (D-24: merge is approval)."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    propose = subparsers.add_parser(
        "propose", help="run one proposer, one structured call (D-21)"
    )
    propose.add_argument(
        "proposer",
        choices=["silver", "mapping", "describe"],
        help="silver: cleanup stance over the bronze profile; "
        "mapping: propose stance over the silver profile; "
        "describe: describe stance over an existing silver table's own "
        "profile (D-35; requires --table)",
    )
    propose.add_argument(
        "--table",
        default=None,
        help="describe only: the existing silver table to describe; the "
        "profile directory and the target contract derive from it",
    )
    propose.add_argument(
        "--oracle",
        default=None,
        metavar="PATH",
        help="describe only: bypass the duplicate-id refusal and score "
        "the draft against this committed contract as an n=1 agreement "
        "study (D-25)",
    )
    propose.add_argument(
        "--profile",
        default=None,
        help="explicit profile artifact path (default: the newest vNNNN)",
    )
    propose.add_argument(
        "--model",
        default=None,
        help="allow-listed model ID override (D-34); precedence "
        "--model, then MM_PROPOSER_MODEL, then the pinned default",
    )
    evaluate = subparsers.add_parser(
        "eval",
        help="the live eval lane over the golden-profile set (D-25); "
        "needs a key",
    )
    evaluate.add_argument(
        "--model",
        default=None,
        help="allow-listed model ID override (D-34), the same precedence "
        "as propose",
    )
    evaluate.add_argument(
        "--fixture",
        action="append",
        default=None,
        metavar="LABEL",
        help="run only the named fixture label(s) from agents.eval.fixtures",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[3]
    if args.command == "eval":
        return eval_lane.run_eval(
            repo_root, model_flag=args.model, labels=args.fixture
        )
    if args.proposer == "describe":
        return _run_describe(repo_root, args)
    build = (
        silver_proposer.build_spec
        if args.proposer == "silver"
        else mapping_proposer.build_spec
    )
    spec = build(repo_root)
    return harness.run_proposer(
        spec, repo_root, profile=args.profile, model_flag=args.model
    )


def _run_describe(repo_root: Path, args: argparse.Namespace) -> int:
    """The describe stance: refusal gate, one run, optional oracle study.

    Describe refuses when a contract with the table's id already exists
    (D-35): a contracted table's path is the amend stance, and shadowing
    a committed contract would invite exactly the weakening rule 6
    forbids. An explicit --oracle PATH bypasses the refusal for the
    recorded n=1 agreement study (D-25) and scores the draft against
    that committed contract on profile-evidenced elements only.
    """
    table = (args.table or "").strip()
    if not table:
        print(
            "error: describe requires --table "
            "(make propose-describe TABLE=<model>)",
            file=sys.stderr,
        )
        return 1
    oracle_path = Path(args.oracle) if args.oracle else None
    if oracle_path is not None and not oracle_path.exists():
        print(f"error: oracle {oracle_path} does not exist", file=sys.stderr)
        return 1
    spec = silver_proposer.build_describe_spec(repo_root, table)
    if spec.target_contract.exists() and oracle_path is None:
        relative = spec.target_contract.relative_to(repo_root)
        print(
            f"error: {relative} already exists; describe adopts "
            "uncontracted tables and refuses to shadow a committed "
            "contract (D-35). The amend stance is the path for a "
            "contracted table. For the recorded n=1 agreement study, "
            "pass an explicit oracle: make propose-describe "
            f"TABLE={table} ORACLE={relative}",
            file=sys.stderr,
        )
        return 1
    report: dict = {}
    code = harness.run_proposer(
        spec,
        repo_root,
        profile=args.profile,
        model_flag=args.model,
        report=report,
    )
    if code == 0 and oracle_path is not None:
        draft = yaml.safe_load(
            Path(report["record"]["draft_path"]).read_text(encoding="utf-8")
        )
        oracle = yaml.safe_load(oracle_path.read_text(encoding="utf-8"))
        result = agreement.score(draft, oracle)
        for line in agreement.summary_lines(result):
            print(line)
        run_dir = Path(report["run_dir"])
        out = run_dir / "agreement.json"
        tmp = run_dir / "agreement.json.tmp"
        tmp.write_text(
            json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        tmp.replace(out)
        print(f"agreement: {out}")
    return code


if __name__ == "__main__":
    sys.exit(main())
