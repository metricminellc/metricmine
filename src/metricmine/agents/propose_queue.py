"""The batch driver: walk the derived queue, one call per item (D-35).

NOT an agent (D-10 Amendment G, CLAUDE.md rule 15): deterministic
sequencing of one-call proposers, the same posture as the eval lane. The
queue is DERIVED here on every run through the scan's own inventory and
ordering (scan.inventory and scan.queued_models), never read from a
stored plan, which could rot; nothing is stored: each proposer run
writes its own draft and record to the outbox, and this module only
sequences and reports.

The walk: queued `adopt` items run the describe stance; queued `amend`
items run the amend stance and REQUIRE the operator's batch intent
(D-23 Amendment H: amend consumes a human-typed intent, recorded
verbatim per proposal); without INTENT they are listed with their exact
per-item command and never invoked. The cap is explicit (MAX, never
defaulted). The first fail-closed proposer exit stops the batch, and a
failed item is never re-invoked unattended (Amendment G): report and
stop is the whole contract. Every other queue state waits for its
deterministic next command and is never driven from here.

This is a CLI, not the stdio server: stdout carries the run report and
stderr the diagnostics.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from metricmine.adoption import scan
from metricmine.agents import harness, silver_proposer
from metricmine.agents.render import (
    amends_contract_stamp,
    canonical_contract_bytes,
)

DRIVEN_STATES = ("adopt", "amend")


def run_queue(
    repo_root: Path,
    max_items: int,
    *,
    intent: str | None = None,
    model_flag: str | None = None,
    client: Any = None,
    lint_runner: Any = None,
) -> int:
    """Walk the queue's driven items in plan order. 0 = every invoked
    item wrote a draft (including an empty walk); 1 = a refusal or a
    fail-closed exit stopped the batch."""
    inventory = scan.inventory(repo_root)
    queued = scan.queued_models(inventory["models"])
    driven = [m for m in queued if m["state"] in DRIVEN_STATES]
    waiting = [m for m in queued if m["state"] not in DRIVEN_STATES]

    print(f"queue: {len(queued)} item(s); driven states: {len(driven)}")
    if not driven:
        print(
            "nothing to invoke: the queue holds no adopt or amend items. "
            "Other states wait for their deterministic next command "
            "(re-run make scan for the plan)."
        )
        return 0

    skipped_for_intent = [
        m for m in driven if m["state"] == "amend" and intent is None
    ]
    to_walk = [m for m in driven if m not in skipped_for_intent]
    for model in skipped_for_intent:
        print(
            f"skipped (no INTENT): {model['name']} at amend; run it "
            f"yourself: {model['next_command']}"
        )
    for model in waiting:
        print(
            f"not driven: {model['name']} at {model['state']}; "
            f"next: {model['next_command']}"
        )
    if not to_walk:
        print(
            "nothing to invoke: every driven item needs the operator "
            '(pass INTENT="..." to walk amend items in this batch).'
        )
        return 0

    walked = 0
    total_in = 0
    total_out = 0
    total_cost = 0.0
    total = min(max_items, len(to_walk))
    for model in to_walk:
        if walked >= max_items:
            print(
                f"cap reached: MAX={max_items}; "
                f"{len(to_walk) - walked} driven item(s) left in the queue"
            )
            break
        name = model["name"]
        stance = "describe" if model["state"] == "adopt" else "amend"
        print(
            f"item {walked + 1}/{total}: {name} "
            f"({model['state']} -> {stance} stance)"
        )
        report: dict = {}
        if stance == "describe":
            spec = silver_proposer.build_describe_spec(repo_root, name)
            code = harness.run_proposer(
                spec,
                repo_root,
                model_flag=model_flag,
                client=client,
                lint_runner=lint_runner,
                report=report,
                quiet=True,
            )
        else:
            target = repo_root / "contracts" / f"{name}.odcs.yaml"
            if not target.exists():
                # The queue is derived fresh, but the tree can move
                # between the derivation and this item: a stale reading
                # is reported, never walked around.
                print(
                    f"error: {name} reads amend but "
                    f"contracts/{name}.odcs.yaml does not exist; re-run "
                    f"make scan",
                    file=sys.stderr,
                )
                return 1
            spec, committed, committed_bytes = (
                silver_proposer.build_amend_spec(repo_root, name)
            )
            # The committed contract and the batch intent bind exactly
            # as the amend CLI binds them (D-22 Amendment I, D-23
            # Amendment H): raw bytes hashed, intent recorded verbatim.
            bound = harness.GovernedInput(
                kind="committed_contract",
                path=str(target),
                content_hash=canonical_contract_bytes(committed_bytes),
                schema_version=str(committed.get("version", "")),
            )
            code = harness.run_proposer(
                spec,
                repo_root,
                model_flag=model_flag,
                client=client,
                lint_runner=lint_runner,
                report=report,
                quiet=True,
                extra_inputs=[(bound, committed_bytes.decode("utf-8"))],
                intent=intent,
                provenance_extras={
                    "amendsContract": amends_contract_stamp(
                        committed, committed_bytes
                    )
                },
            )
        walked += 1
        record = report.get("record")
        if code != 0 or record is None:
            print(
                f"stopped: {name} exited {code} "
                f"({'failed closed' if code == 2 else 'refused'}); a "
                f"failed item is never re-invoked unattended (Amendment "
                f"G). Review the record, fix the cause, re-run the item "
                f"yourself."
            )
            return 1
        usage = record["usage"]
        total_in += usage["input_tokens"]
        total_out += usage["output_tokens"]
        total_cost += record["cost_usd_estimate"]
        print(f"  draft: {record['draft_path']}")
        print(
            f"  tokens in {usage['input_tokens']}, out "
            f"{usage['output_tokens']}; cost "
            f"~${record['cost_usd_estimate']:.4f}; "
            f"attempts {record['validation']['attempts']}"
        )
    print(
        f"walked {walked} item(s); tokens in {total_in}, out {total_out}; "
        f"total cost ~${total_cost:.4f}"
    )
    print(
        "review each draft in the editor; approval stays one contract "
        "per PR (D-24: merge is approval)."
    )
    return 0
