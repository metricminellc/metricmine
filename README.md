<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/mm_logo_on_dark.png">
    <img src="docs/assets/mm_logo_on_light.png" alt="MetricMine — data mined and refined" width="420">
  </picture>

  <p><strong>A contract-driven data pipeline that ends in an answer, not a table.</strong><br>
  Apache-2.0 &nbsp;·&nbsp; Python 3.12 &nbsp;·&nbsp; dbt + DuckDB &nbsp;·&nbsp; ODCS v3.1.0 &nbsp;·&nbsp; MCP</p>
</div>

![The MetricMine workflow: sources land in bronze and are profiled; an
approved cleanup contract shapes silver; a second profile and an approved
mapping contract feed the auto-modeling engine; the engine emits the gold
unified event star; an MCP server serves it read-only and Claude answers
with data plus meaning](docs/assets/mm_workflow.png)

<div align="center"><sub>Detailed component diagrams, each with a
machine-readable Mermaid twin: <a href="docs/diagrams/">docs/diagrams/</a></sub></div>

## What this is

MetricMine is a contract-driven medallion pipeline that runs end to end on
one machine. Raw data lands in bronze; a deterministic profiler describes
it; machine-readable ODCS contracts — hand-written today, proposed by two
narrow AI agents in Phase 6 — shape silver and gold behind a human approval
gate; and an auto-modeling engine emits the entire gold layer from the
approved contract. The result is a governed dimensional gold layer with a
context registry one join from any payload, served read-only over MCP, so
an AI assistant answers business questions grounded in both the data and
the meaning behind it.

The repository is a deliberate work in progress: it advances in phases that
each exit in a working, demonstrable state. What exists runs, what is ahead
is stated plainly, and the docs folder carries every decision and
specification that got it here. The unified event star at the gold layer is
the experimental centerpiece; the practices around it are industry-standard
end to end.

## What this repository demonstrates

**Strategy you can audit.** Thirty-three binding decisions in a versioned
[decision register](docs/decisions/decision-register.md); specifications
written before code; explicit non-goals; and no claim without a
reproducible command behind it. The plan is not a slide deck. It is a
governed artifact that survives contact with the build, and the repository
carries the whole decision trail.

**An AI-augmented SDLC with real governance.** I architect and plan with an
AI copilot; Claude Code implements through small, reviewed pull requests;
and a three-gate contract CI (lint, compile-time build, generated tests)
judges human and agent changes symmetrically.
[CLAUDE.md](CLAUDE.md) maps every decision, spec, and diagram into the
coding agent's context, so any engineer, human or AI, starts grounded in
project state, methodology, and the end-in-mind vision.

**Industry-standard architecture, end to end.** PyAirbyte ingestion, a dbt
medallion (bronze, silver, gold), ODCS v3.1.0 data contracts enforced from
ingestion through serving, a unified event star with a content-addressed
context registry, and MCP at the serving edge. The agent layer is designed
against GenAIOps practice across PromptOps, RAGOps, and AgentOps,
right-sized for the project and documented like everything else.

> **Agents propose. Code executes. A human approves.**
> Judgment and execution stay separate. Every approval becomes a versioned,
> machine-readable contract that CI enforces from then on. In the age of
> context windows, contracts are how agents get compact, reliable truth —
> and this pipeline makes that governance automatic rather than
> aspirational.

## See it run

The repository ships `demo/demo.duckdb`, a verified ~11 MB gold-only
export, so serving works from a fresh clone with no build step and no
credentials:

```bash
git clone https://github.com/metricminellc/metricmine.git && cd metricmine
uv sync
uv run python -c "from metricmine.query import GoldWarehouse; print(GoldWarehouse().list_fact_categories())"
```

The full walkthrough — wiring the MCP server into Claude Desktop, the
questions to ask, the complete keyless replay from raw data to a fresh
export, and troubleshooting — is **[docs/demo.md](docs/demo.md)**, about
ten minutes end to end. A recording of the demo is attached to the
[latest release](https://github.com/metricminellc/metricmine/releases/latest).

## Architecture at a glance

Three planes organize the repository: `contracts/` is the specification
(ODCS data contracts a human approves), `transform/` is the dbt execution
project, and `src/` is hand-written Python — the profiler, the
auto-modeling engine, the context compiler, the shared query module, and
the MCP server. Data moves bronze → silver → gold in one local DuckDB
file. Gold is terminal and machine-emitted: a source-invariant,
content-addressed star, so a new source adds rows, not schema. Serving is
read-only three layers deep, through five MCP tools over one shared query
module. Designs: the
[gold layer spec](docs/spec/gold-unified-event-star.md), the
[serving spec](docs/spec/serving.md), and the
[agent layer spec](docs/spec/agent-layer.md).

## Built small, designed to scale

The demo runs end to end on one machine, on DuckDB by design. Portability
is delegated to dbt profiles, with Snowflake named as the swap target, and
the patterns that matter — contracts, symmetric gates, ownership
manifests, human-gated agents — are the same ones that run at enterprise
scale on any cloud. Nothing here depends on the demo staying small.

## Proof, committed

The contract gates were broken deliberately, in both directions, and the
evidence is committed. A shape defect — a renamed column — fails at
compile time, before any DDL runs: proven live in
[break-demo PR #45](https://github.com/metricminellc/metricmine/pull/45),
opened against the real pipeline and closed unmerged by design, its red
check permanent. A content defect — data violating a declared rule —
builds, then fails as an error-severity contract test:

![PR #45: the shape gate fails red in CI](docs/verification/evidence/2026-07-31_pr45_break_demo_red_check.png)

![A content defect fails as a contract test](docs/verification/evidence/2026-07-11_gate3_content_failure.png)

The signature property (D-17) is the payoff, demonstrated rather than
asserted: adding the reserved `country` dimension took one
mapping-contract amendment and one regeneration. No engine code changed,
no physical schema changed, no gold contract amendment — 23 emitted files
moved, one schema key appeared, and row conservation held to the digit
(44,721 in, 44,721 out). The full narrative, with the staleness-guard and
ownership-drift refusals captured live, is
[docs/verification/signature-test.md](docs/verification/signature-test.md).

One more property is documented rather than discovered: the star's hash
keys are content addresses, not row identifiers. The counting rules, and
the trade they record, live in the gold spec's *Reading the star* section
and in findings
[F-23](docs/verification/gate_proof_findings.md#f-23) and
[F-24](docs/verification/gate_proof_findings.md#f-24).

## Go deeper

| If you want | Read |
|---|---|
| The demo, step by step | [docs/demo.md](docs/demo.md) |
| Every architectural decision, versioned | [docs/decisions/decision-register.md](docs/decisions/decision-register.md) |
| The layer specs, ingestion through serving | [docs/spec/](docs/spec/) |
| The evidence: findings, the signature test, gate breaks | [docs/verification/](docs/verification/) |
| The diagrams, SVG with Mermaid twins | [docs/diagrams/](docs/diagrams/) |
| The guardrails the coding agent works under | [CLAUDE.md](CLAUDE.md) |

## Status and roadmap

v0.1.0 is the first tagged release: Phases 0 through 5 complete — the
scaffold and pinned toolchain, bronze ingestion, the profiler and
contracted silver, the engine-emitted unified event star, and the serving
layer with the committed demo artifact. Phase 6, the two proposer agents,
is next. The live roadmap is the
[Issues tab](https://github.com/metricminellc/metricmine/issues).

## Toolchain

dbt-core 1.12.x with the dbt-duckdb 1.11.x adapter runs the transforms.
datacontract-cli 1.0.12, installed as an isolated uv tool, executes the
contracts. DuckDB 1.4.3 is the local warehouse. PyAirbyte handles
ingestion. The MCP server runs on the official `mcp` SDK, pinned to the
1.x maintenance line (D-32 as amended; the register records why). The code
is Python 3.12, managed with uv. Every pin is a register entry; none of
them is `latest`.

## Non-goals

Multi-tenancy, auth, billing, any UI beyond the optional read-only demo,
streaming, Redshift, orchestration platforms, autonomous multi-step
agents, more than one or two source types, petabyte or throughput claims,
and production SLAs.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
