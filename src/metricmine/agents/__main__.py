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
from metricmine.agents import e3
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
        "profile directory and the target contract derive from it. "
        "mapping: the silver table whose profile the propose stance "
        "reads (profiles/silver.<table>/; default: the configured table)",
    )
    propose.add_argument(
        "--source",
        default=None,
        help="silver only: the bronze table whose profile the cleanup "
        "stance reads (profiles/bronze.<source>/; default: the "
        "configured table)",
    )
    propose.add_argument(
        "--target",
        default=None,
        help="silver and mapping: the target contract id "
        "(contracts/<target>.odcs.yaml; default: silver_<source> or "
        "gold_<category>_mapping, or the configured target)",
    )
    propose.add_argument(
        "--intent",
        default=None,
        help="amend only: the operator's intent for this amendment, "
        "recorded verbatim in the proposal record and bound as a "
        "governed input (D-22 Amendment I, D-23 Amendment H)",
    )
    propose.add_argument(
        "--context",
        default=None,
        help="every stance (E3a, experiment branch; docs/experiments/e3/"
        "KEY.md): the operator's context, a few sentences, bound as the "
        "last governed input, hashed and recorded verbatim",
    )
    propose.add_argument(
        "--context-file",
        default=None,
        metavar="PATH",
        help="every stance: read the operator's context from a committed "
        "file, recording its path beside its hash",
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
        help="describe: bypass the duplicate-id refusal and score the "
        "draft against this committed contract as an n=1 agreement "
        "study (D-25). silver and mapping: score the draft against this "
        "committed contract the same way (the multi-source study, D-41)",
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
    queue.add_argument(
        "--context",
        default=None,
        help="the operator's batch context, bound verbatim to every item "
        "the batch invokes (E3a, experiment branch)",
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
    evaluate.add_argument(
        "--arm",
        default=None,
        help="E3 (experiment branch): run one arm of docs/experiments/e3/"
        "arms.yaml as a batch with repeats, the ledger, and the bound; "
        "without it the lane runs as at head",
    )
    evaluate.add_argument(
        "--repeats",
        type=int,
        default=None,
        help="E3: attempts per fixture in the arm (default: the arm's)",
    )
    evaluate.add_argument(
        "--rerun-technical",
        action="store_true",
        help="E3: re-invoke, once, the attempts the ledger marks technical; "
        "a result is never re-run",
    )
    evaluate.add_argument(
        "--continue-lost",
        default=None,
        metavar="LABEL",
        help="E3: run the remaining attempts of one fixture whose latest "
        "result failed closed, on a person's instruction after the record "
        "was read (D-10 Amendment G); never set unattended",
    )
    evaluate.add_argument(
        "--dry-run",
        action="store_true",
        help="E3: print what each fixture's call would carry, with no call",
    )
    subparsers.add_parser(
        "e3-leakage",
        help="E3: count the oracle column names each context text carries",
    )
    subparsers.add_parser(
        "e3-score",
        help="E3: score the committed ledger and evidence; write scores.json",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[3]
    if args.command == "propose-queue":
        return _run_queue(repo_root, args)
    if args.command == "e3-leakage":
        e3.leakage(repo_root)
        return 0
    if args.command == "e3-score":
        e3.score(repo_root)
        return 0
    if args.command == "eval":
        if args.arm:
            return e3.run_arm(
                repo_root,
                args.arm,
                repeats=args.repeats,
                model_flag=args.model,
                rerun_technical=args.rerun_technical,
                continue_lost=args.continue_lost,
                dry_run=args.dry_run,
            )
        return eval_lane.run_eval(
            repo_root, model_flag=args.model, labels=args.fixture
        )
    context, context_path = _context_arguments(args)
    if context is None and context_path == "":
        return 1
    if args.proposer == "describe":
        return _run_describe(repo_root, args, context, context_path)
    if args.proposer == "amend":
        return _run_amend(repo_root, args, context, context_path)
    oracle_path = Path(args.oracle) if args.oracle else None
    if oracle_path is not None and not oracle_path.exists():
        print(f"error: oracle {oracle_path} does not exist", file=sys.stderr)
        return 1
    if args.proposer == "silver":
        spec = silver_proposer.build_spec(
            repo_root, source=args.source, target=args.target
        )
        scorer = (agreement.score, agreement.summary_lines)
    else:
        spec = mapping_proposer.build_spec(
            repo_root, table=args.table, target=args.target
        )
        scorer = (agreement.score_mapping, agreement.summary_lines_mapping)
    report: dict = {}
    code = harness.run_proposer(
        spec,
        repo_root,
        profile=args.profile,
        model_flag=args.model,
        report=report,
        context=context,
        context_path=context_path,
    )
    if code == 0 and oracle_path is not None:
        _score_against_oracle(report, oracle_path, *scorer)
    return code


def _context_arguments(args: argparse.Namespace) -> tuple[str | None, str | None]:
    """The operator's context from --context or --context-file (E3a):
    (text, path). (None, "") signals a refusal already printed."""
    text = getattr(args, "context", None)
    path = getattr(args, "context_file", None)
    if text is not None and path is not None:
        print("error: pass --context or --context-file, not both", file=sys.stderr)
        return None, ""
    if path is not None:
        source = Path(path)
        if not source.exists():
            print(f"error: context file {source} does not exist", file=sys.stderr)
            return None, ""
        # Bytes, decoded: the hash the harness records is the hash the
        # staleness re-check computes over the file, byte for byte.
        return source.read_bytes().decode("utf-8"), str(source)
    if text is not None and not text.strip():
        print("error: --context is empty; omit it to run with no context", file=sys.stderr)
        return None, ""
    return text, None


def _score_against_oracle(report: dict, oracle_path: Path, score, lines) -> None:
    """The recorded n=1 agreement study (D-25): score the written draft
    against the oracle contract, print the block, and leave
    agreement.json beside the record in the run directory."""
    draft = yaml.safe_load(
        Path(report["record"]["draft_path"]).read_text(encoding="utf-8")
    )
    oracle = yaml.safe_load(oracle_path.read_text(encoding="utf-8"))
    result = score(draft, oracle)
    for line in lines(result):
        print(line)
    run_dir = Path(report["run_dir"])
    out = run_dir / "agreement.json"
    tmp = run_dir / "agreement.json.tmp"
    tmp.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(out)
    print(f"agreement: {out}")


def _run_describe(
    repo_root: Path,
    args: argparse.Namespace,
    context: str | None = None,
    context_path: str | None = None,
) -> int:
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
        context=context,
        context_path=context_path,
    )
    if code == 0 and oracle_path is not None:
        _score_against_oracle(
            report, oracle_path, agreement.score, agreement.summary_lines
        )
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
    context = (args.context or "").strip() or None
    return propose_queue.run_queue(
        repo_root, int(raw), intent=intent, model_flag=args.model, context=context
    )


def _run_amend(
    repo_root: Path,
    args: argparse.Namespace,
    context: str | None = None,
    context_path: str | None = None,
) -> int:
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
        context=context,
        context_path=context_path,
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
