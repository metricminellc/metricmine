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
