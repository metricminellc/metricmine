# docs/experiments/

> Repo path: `docs/experiments/README.md`
> The experiments lane's written findings, and the deferred design
> questions the lane keeps. Nothing here binds: a decision is minted only
> in the [decision register](../decisions/decision-register.md), and a
> measured defect only in the
> [findings register](../verification/gate_proof_findings.md).

## The rule

From v1.0.0 the stable core changes only through the decision register.
Experiments live on branches, or here, and end in written findings; a
clone of main at any tag gets a working demo (CLAUDE.md rule 19). An
experiment that would change the serving layer, a gate, a pin, or an
agent's boundary graduates only by its own register amendment, by its
own documentation pull request, and, by the lane's own convention, only
in the form it ran. An experiment that finds a defect at head sends it
to the findings register by that register's own lane.

## What a record holds

The question. The rule the experiment ran under. What was measured, with
the host and its version, the model, the served file, and the commit.
The result, as measured. What the result bounds. What remains possible.
A record never describes a step before it happens, and every number in
it is measured, never predicted.

## The records

| Path | What it is |
|---|---|
| [`e1-consumer-feedback.md`](e1-consumer-feedback.md) | E1, the consumer feedback loop, staged: the canary that gates stage 1, measured on Claude Desktop on October 21, 2026, and what its result bounds. |
| [`experiments-register.md`](experiments-register.md) | The deferred design questions of the gold layer (X-01 to X-06), in the shape they were left when the register was cut on August 27, 2026, before the v1.0.0 tag, with each item's status measured on main at `2f73dfc` at graduation. |
| [`e3-skeleton-and-context.md`](e3-skeleton-and-context.md) | E3, the skeleton and the context channel on the proposers' API path, measured on October 23, 2026, on the branch `experiment/e3-skeleton-and-context` at `cb27197` under a key committed before run one: the skeleton (HW-14) earned its place by the key's rule, the context channel (HW-15) did not in the form it ran, and what the result bounds. The one behavior of head's own path it measured is F-73 in the findings register. |
| [`e1t-consumer-feedback.md`](e1t-consumer-feedback.md) | E1T, the consumer feedback loop a person starts, measured on November 27, 2026, on the branch `experiment/e1t-consumer-feedback` at `1b4ed1e` under a key committed before run one: `prepare_feedback`, a sixth server tool on the branch only, was called every time and every message it returned verified on the producer's build, on Claude Code 2.1.332 (15 of 15) and Claude Desktop 6.28899.6 (9 of 9), and what the result bounds. No defect at head was measured. |
