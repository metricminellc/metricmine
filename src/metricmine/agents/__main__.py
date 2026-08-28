"""CLI: propose silver | mapping | describe | amend (D-24, D-35).

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
from metricmine.agents import (
    harness,
    mapping_proposer,
    propose_queue,
    render,
    silver_proposer,
    validate,
)


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
        choices=["silver", "mapping", "describe", "amend"],
        help="silver: cleanup stance over the bronze profile; "
        "mapping: propose stance over the silver profile; "
        "describe: describe stance over an existing silver table's own "
        "profile (D-35; requires --table); "
        "amend: amend stance over a contracted silver table (D-35; "
        "requires --table and --intent)",
    )
    propose.add_argument(
        "--table",
        default=None,
        help="describe and amend: the existing silver table; the "
        "profile directory and the target contract derive from it",
    )
    propose.add_argument(
        "--intent",
        default=None,
        help="amend only: the operator's intent for this amendment, "
        "recorded verbatim in the proposal record and bound as a "
        "governed input (D-22 Amendment I, D-23 Amendment H)",
    )
    propose.add_argument(
        "--allow-relaxation",
        action="store_true",
        help="amend only: permit a NARROWING change set; it renders at "
        "a major version bump with the printed rule-6 warning (D-35, "
        "D-08)",
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
    queue = subparsers.add_parser(
        "propose-queue",
        help="walk the derived queue's adopt and amend items, one call "
        "per item, capped (D-35); deterministic sequencing, never an "
        "agent; needs a key when items run",
    )
    queue.add_argument(
        "--max",
        default=None,
        help="the explicit cap on invoked items (required; make "
        "propose-queue MAX=<n>)",
    )
    queue.add_argument(
        "--intent",
        default=None,
        help="the operator's batch intent for amend items, recorded "
        "verbatim per proposal (D-22 Amendment I); without it amend "
        "items are listed, never invoked",
    )
    queue.add_argument(
        "--model",
        default=None,
        help="allow-listed model ID override (D-34), the same precedence "
        "as propose",
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
    if args.command == "propose-queue":
        return _run_queue(repo_root, args)
    if args.command == "eval":
        return eval_lane.run_eval(
            repo_root, model_flag=args.model, labels=args.fixture
        )
    if args.proposer == "describe":
        return _run_describe(repo_root, args)
    if args.proposer == "amend":
        return _run_amend(repo_root, args)
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


def _run_queue(repo_root: Path, args: argparse.Namespace) -> int:
    """The batch driver: an explicit cap, an optional batch intent.

    The cap is never defaulted (D-35 names it: the driver walks the
    queue WITH a cap; S-Q-prep-5), so an empty MAX from make is a
    refusal, the same posture as an empty TABLE. The intent gate lives
    in the driver: an amend item without an operator intent has no
    governed reason to run (D-23 Amendment H)."""
    raw = (args.max or "").strip()
    if not raw.isdigit() or int(raw) < 1:
        print(
            "error: propose-queue requires an explicit positive cap "
            "(make propose-queue MAX=<n>); the cap is part of the D-35 "
            "contract, never a default",
            file=sys.stderr,
        )
        return 1
    intent = (args.intent or "").strip() or None
    return propose_queue.run_queue(
        repo_root, int(raw), intent=intent, model_flag=args.model
    )


def _run_amend(repo_root: Path, args: argparse.Namespace) -> int:
    """The amend stance: refusal gates, three governed inputs, one run.

    Amend evolves a COMMITTED contract (D-35), so it refuses when no
    contract with the table's id exists and points at describe, the
    mirror of describe's duplicate-id refusal. The operator's intent is
    required and non-empty: an amendment without a stated intent has no
    governed reason to exist (D-23 Amendment H). After a draft lands,
    the declared change directions and the derived bump print so the
    reviewer reads the D-08 posture before opening the draft.
    """
    table = (args.table or "").strip()
    if not table:
        print(
            "error: amend requires --table "
            '(make propose-amend TABLE=<model> INTENT="...")',
            file=sys.stderr,
        )
        return 1
    intent = (args.intent or "").strip()
    if not intent:
        print(
            "error: amend requires a non-empty --intent; the operator's "
            "intent is a governed input recorded verbatim in the "
            'proposal record (make propose-amend TABLE=<model> INTENT="...")',
            file=sys.stderr,
        )
        return 1
    target = repo_root / "contracts" / f"{table}.odcs.yaml"
    if not target.exists():
        relative = target.relative_to(repo_root)
        print(
            f"error: {relative} does not exist; amend evolves a "
            "committed contract (D-35). The describe stance is the "
            "adoption path for an uncontracted table: "
            f"make propose-describe TABLE={table}",
            file=sys.stderr,
        )
        return 1
    spec, committed, committed_bytes = silver_proposer.build_amend_spec(
        repo_root, table, allow_relaxation=args.allow_relaxation
    )
    bound = harness.GovernedInput(
        kind="committed_contract",
        path=str(target),
        content_hash=render.canonical_contract_bytes(committed_bytes),
        schema_version=str(committed.get("version", "")),
    )
    stamp = render.amends_contract_stamp(committed, committed_bytes)
    report: dict = {}
    code = harness.run_proposer(
        spec,
        repo_root,
        profile=args.profile,
        model_flag=args.model,
        report=report,
        extra_inputs=[(bound, committed_bytes.decode("utf-8"))],
        intent=intent,
        provenance_extras={"amendsContract": stamp},
    )
    if code == 0:
        proposal = json.loads(
            (Path(report["run_dir"]) / "proposal.json").read_text(
                encoding="utf-8"
            )
        )
        changes = proposal["changes"]
        directions = sorted(
            {validate.classify_change(change) for change in changes}
        )
        bump = validate.derive_bump(changes)
        draft_version = yaml.safe_load(
            Path(report["record"]["draft_path"]).read_text(encoding="utf-8")
        ).get("version")
        print(
            f"amendment direction: {', '.join(directions)}; {bump} bump "
            f"to {draft_version} over {committed.get('version')} "
            f"(amends {stamp.split('#')[0]})"
        )
        if "narrowing" in directions:
            print(
                "rule 6 warning: this amendment NARROWS the contract; "
                "--allow-relaxation was passed, it renders at a MAJOR "
                "bump, and the reviewer owns the consequence (D-35, "
                "D-08)."
            )
    return code


if __name__ == "__main__":
    sys.exit(main())
