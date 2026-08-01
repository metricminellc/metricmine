# MetricMine

A reference implementation of a contract-driven medallion pipeline, designed to
run locally end to end on one command (D-01).

## What it is

MetricMine is legibility-first and governance-forward. I built it as a portfolio
reference implementation: every transform is governed by a data contract, every
contract is approved by a human, and every decision is recorded. It lands data,
profiles it, proposes contracts I approve, models the result, and answers
questions about it, on one machine with one command.

## Status

Phases 1 through 3 are complete. Built so far: the repository scaffold, the
pinned toolchain, the three-gate contract CI workflow (with bronze landed in
CI), the CLAUDE.md guardrails, the decision register, the gold layer design
spec and diagram, the ingestion, profiler, and agent-layer specs, a seeded
roadmap, the committed Online Retail II sample (D-15) with its fetch script,
the PyAirbyte bronze landing (`make ingest`), the deterministic profiler
(`make profile`) with its committed v0001 artifact, and the first contracted
silver model (`silver_invoice_lines`, contract v1.1.0) with all three gates
live end to end. Bronze through contracted silver runs end to end locally
and in CI; gold is the next phase. The live roadmap is
the [Issues tab](https://github.com/metricminellc/metricmine/issues).

## Architecture

Three planes organize the repository.

- `contracts/` is the specification: ODCS data contracts.
- `transform/` is the dbt execution project: contracted SQL models.
- `src/` is hand-written Python: the profiler, the auto-modeling engine, and the
  shared query module.

Data moves through the medallion layers. Bronze holds raw landed data. Silver
holds cleaned, contracted models. Gold is the terminal layer. Gold is the unified
event star: a source-invariant, content-addressed star schema, so a new source
adds rows, not schema. See the
[gold layer spec](docs/spec/gold-unified-event-star.md) and the
[diagrams](docs/diagrams/).

### The two agents

Exactly two runtime agents, both contract proposers: the silver cleanup
proposer (bronze profile in, ODCS cleanup contract out) and the gold mapping
proposer (silver profile in, ODCS mapping contract out). Each is one
structured API call against a pinned model; a deterministic validator
enforces that every proposal is grounded in the profile it consumed, and
approval is a contract-only pull request through the same three gates as
any human change. Agents propose, code executes, a human approves.
`make demo` replays committed contracts with no API key; a regenerate path
invokes the agents live. Design: [docs/spec/agent-layer.md](docs/spec/agent-layer.md).
The agents land in Phase 6; the spine runs on hand-written contracts first.

## Governance and discipline

Governance is the point, not an afterthought. I record every architectural
decision in the [decision register](docs/decisions/decision-register.md). The
[CLAUDE.md](CLAUDE.md) guardrails fix the hard rules before any agent-assisted
work touches the repository. The contract gates judge output, not authorship, and
apply symmetrically to humans and agents: both pass or fail the same way. History
is squash-only, and every change lands as a reviewed pull request.

## The gate, demonstrated

The contract gates were broken deliberately, in both directions, and the
evidence is committed. A shape defect — a renamed column — fails at compile
time, before any DDL runs: proven in the pre-Phase-1 gate proof and again
live in [break-demo PR #45](https://github.com/metricminellc/metricmine/pull/45),
opened against the real pipeline and closed unmerged by design, its red
check permanent:

![PR #45: the shape gate fails red in CI](docs/verification/evidence/2026-07-31_pr45_break_demo_red_check.png)

A content defect — data violating a declared rule — builds, then fails as
an error-severity contract test (the grain-enforcement rule, exercised in
rehearsal):

![A content defect fails as a contract test](docs/verification/evidence/2026-07-11_gate3_content_failure.png)

The full captures, logs, and the DuckDB constraint enforcement matrix live
in [docs/verification/](docs/verification/).

## Toolchain

dbt-core 1.11.x with the dbt-duckdb 1.10.x adapter runs the transforms.
datacontract-cli 1.0.12, installed as an isolated uv tool, executes the
contracts. DuckDB is the local warehouse. PyAirbyte handles ingestion. The code
is Python 3.12, managed with uv.

## Non-goals

Multi-tenancy, auth, billing, any UI beyond the optional read-only demo,
streaming, Redshift, orchestration platforms, autonomous multi-step agents, more
than one or two source types, petabyte or throughput claims, and production SLAs.

## Provenance

This repository was built fresh from an independent written specification. No
source code from the 2023 MetricMine prototype was read, imported, or adapted. No
employer data, architecture diagrams, or platform documentation appear in this
repository or its history.
