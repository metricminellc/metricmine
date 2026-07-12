# Decision Register

> Repo path: `docs/decisions/decision-register.md`
> The authoritative in-repo index of project decisions. Commit bodies and docs
> cite decisions by ID (`D-0x`); every ID cited anywhere in this repository
> resolves to an entry here. Changing a pinned version, a gate, or an
> architecture boundary requires amending this register in its own
> documentation pull request before the implementing change lands.

Decisions were made in working sessions during July 2026 and are condensed
here in full operational substance. Extended context and analysis live in
project records maintained outside the repository; nothing in this repo
depends on those records.

**Status meanings.** `adopted` — in force. `proposed` — agreed in working
session, applied by the plans below, formal adoption pending; treat as binding
unless amended.

## Index

| ID | Decision | Status |
|---|---|---|
| [D-01](#d-01) | Repository identity and framing | adopted |
| [D-02](#d-02) | Apache-2.0 license; provenance in NOTICE | adopted |
| [D-03](#d-03) | Working warehouse gitignored; demo export committed | adopted |
| [D-04](#d-04) | dbt Core + dbt-duckdb is the transform plane | adopted |
| [D-05](#d-05) | Version pins; dbt 1.12 and Core v2 deferred | adopted |
| [D-06](#d-06) | ODCS v3.1.0 contracts; datacontract-cli as isolated tool | adopted |
| [D-07](#d-07) | The engine emits dbt models, never DDL | adopted |
| [D-08](#d-08) | Symmetric gates; contracts never weakened to pass | adopted |
| [D-09](#d-09) | Regeneration via PR under an ownership manifest | adopted |
| [D-10](#d-10) | Exactly two pipeline agents; authoring loop in the SDLC | adopted |
| [D-11](#d-11) | Portability via dbt profiles; thin read-only protocol | adopted |
| [D-12](#d-12) | CI is the three-gate contract workflow; gate proof first | adopted |
| [D-13](#d-13) | CLAUDE.md guardrails fixed before agent contact | adopted |
| [D-14](#d-14) | Commit and pull request conventions | adopted |
| [D-15](#d-15) | Committed sample dataset: Online Retail II | proposed |
| [D-16](#d-16) | Gate-three mechanism: sync then test under uv run | proposed |
| [D-17](#d-17) | Gold is the unified event star | proposed |
| [D-18](#d-18) | Keying scheme v2 (canonical_key v2) | proposed |
| [D-19](#d-19) | Context binds by content address (schema-key registry) | proposed |

## The decisions

### D-01
**Repository identity and framing.** This repository is
`metricminellc/metricmine`, a reference implementation designed to run
locally, end to end, on one command. Private until the serving demo is
presentable, then public with a `v0.1.0` tag. Any future cloud deployment is a
separate repository that depends on this one, never a fork.

### D-02
**License and provenance.** Apache-2.0, chosen for the NOTICE vehicle. NOTICE
carries the clean-room provenance statement: built fresh from an independent
specification; no prior-implementation code read or imported; no third-party
proprietary data or diagrams anywhere in the history.

### D-03
**Warehouse file strategy.** The working database lives at
`warehouse/metricmine.duckdb`, holds the bronze, silver, and gold schemas, and
is gitignored along with dbt's `target/`, `dbt_packages/`, and `logs/`. The
committed artifact is `demo/gold.duckdb`, a purpose-built export of gold plus
context produced by `make export-demo` from the committed sample data. Raw
data never enters git.

### D-04
**Transform execution plane.** dbt Core v1 with the dbt-duckdb adapter
executes all contracted transforms as SQL dbt models with
`contract: enforced: true`. The profiler stays standalone deterministic
Python, outside dbt, because its output is a reviewable artifact, not a table.
Three planes organize the repo: `contracts/` (specification), `transform/`
(execution), `src/` (hand-written code).

### D-05
**Pins and deferrals.** dbt-core `>=1.11,<1.12` (resolved 1.11.12);
dbt-duckdb `>=1.10,<1.11` (resolved 1.10.1). dbt 1.12 waits for GA. dbt Core
v2 is deliberately deferred. Upgrading any pin requires amending this register
first (CLAUDE.md rule 1).

### D-06
**Contract standard and tooling.** Contracts are authored natively in ODCS
v3.1.0. datacontract-cli, pinned at 1.0.12, is installed as an isolated uv
tool with the `[duckdb]` extra and is never a `pyproject.toml` dependency.

### D-07
**The engine emits models.** The auto-modeling engine is a contract-driven
dbt model generator: mapping contract in, gold model files out. It never
executes DDL. dbt build materializes gold as `table`, with a documented path
to `incremental`. `materialized_view` is never used (not implemented by
dbt-duckdb; not the portable choice).

### D-08
**Symmetric gates.** The gates judge output, not authorship; humans and
agents pass or fail identically. Never weaken a contract to make a failing
build pass. A shape-changing edit routes to a contract amendment in its own
pull request with a version bump; the implementation change lands after it.
(Enforced as CLAUDE.md rule 6.)

### D-09
**Regeneration safety.** The engine never writes to `main`; regeneration
lands only as pull requests. An ownership manifest records a checksum for
every emitted file and a generated-by header naming the source contract and
version. A diverged checksum marks a file human-owned: the engine leaves it
alone and flags the drift. (Enforced as CLAUDE.md rule 8.)

### D-10
**Agent boundary.** Exactly two agents exist in the pipeline: the silver
cleanup proposer and the fact-and-dimension mapping proposer. Both emit ODCS
contracts; neither writes code, touches data, or runs transformations. The
generate-and-verify authoring loop lives in the AI-assisted SDLC layer as
reviewed pull requests, never as a third runtime agent.

### D-11
**Portability delegation.** Warehouse portability belongs to dbt profiles;
`transform/profiles.yml` carries the local DuckDB target and a
Snowflake target expressed through environment variables. A thin read-only
protocol (~5 methods) in `src/metricmine/warehouse/` covers the two consumers
dbt does not: the profiler reading bronze and the shared query module serving
gold. The README claims only the isolation that exists.

### D-12
**CI gates.** Every pull request runs the three-gate contract workflow —
gate one `datacontract lint`, gate two `dbt build` (compile-time shape
enforcement), gate three per D-16 — alongside ruff and pytest. The toolchain
was proven end to end in a scratch gate-proof session before Phase 1 exit;
findings in [`docs/verification/gate_proof_findings.md`](../verification/gate_proof_findings.md).

### D-13
**Guardrails before contact.** CLAUDE.md carries a fixed guardrail set
(the hard rules) before any agent-assisted work touches the repository.
Guardrail changes are documentation pull requests citing the governing
decision.

### D-14
**Commit and PR conventions.** Conventional Commits subjects; bodies explain
why and cite the governing D-0x from this register when one applies; PR
descriptions carry Summary, What changed, Why. Squash-only merges;
delete-branch-on-merge. The PR title and description become the permanent
commit on `main`.

### D-15
**Committed sample dataset (proposed).** Online Retail II (Daqing Chen, UCI
Machine Learning Repository, CC BY 4.0): a deterministic, complete-invoice,
one-month extract under 5 MB, produced by a committed fetch script; the raw
download stays gitignored. The Kaggle mirror is acceptable with UCI cited.
`source-faker` remains the keyless synthetic path.

### D-16
**Gate-three mechanism (proposed).** Gate three is
`uv run datacontract dbt sync ...` followed by
`uv run datacontract dbt test ...`. The `uv run` prefix is mandatory (the
isolated tool cannot find dbt on PATH). The top-level `datacontract test`
command is not used against DuckDB (server type unsupported at 1.0.12) and is
distinct from the gate's `datacontract dbt test` subcommand. Sync-generated
tests are reviewed before merge, never auto-trusted; dbt properties files are
hand-authored; `export dbt-models` output is scaffold and drift check only.
Evidence: findings F-01 to F-07 in
[`docs/verification/gate_proof_findings.md`](../verification/gate_proof_findings.md).

### D-17
**Gold is the unified event star (proposed).** The terminal gold layer is the
unified event star: content-addressed values and columns dimensions,
category-parameterized fact tables, and a context registry, all emitted by
the engine as dbt models per D-07 and materialized as tables (contract
enforcement requires table or incremental). The engine additionally emits one
uncontracted typed projection view per fact category, labeled derivative.
Materialized columnar marts are out of scope, documented as a future
increment. Gold serves consumers only through the shared query module, with
the MCP server primary. Full design:
[`docs/spec/gold-unified-event-star.md`](../spec/gold-unified-event-star.md).

### D-18
**Keying scheme v2 (proposed).** All record and schema keys use
`canonical_key` v2: payloads parse and serialize compact with sorted keys,
lowercase, SHA-256, hex; scalars and manifests cast to text, lowercase,
whitespace stripped, hyphens preserved. Deterministic, case-, whitespace-,
and order-insensitive. A deliberate, documented delta from the 2023 baseline
scheme (which was insertion-order sensitive and hyphen-stripping); the
rebuild carries zero legacy data, so no key migration exists. Baseline
record: [`docs/spec/current-state/data-capture-baseline.md`](../spec/current-state/data-capture-baseline.md).

### D-19
**Context binds by content address (proposed).** Business context and
contract references attach to data through schema keys in the
`context_registry` table: one row per schema key carrying the entity group,
the governing contract name and version, and the compiled context. Contracts
are never embedded in payloads. The context compiler owns the registry; the
MCP context tools read it.

## Session-decision and finding IDs

IDs of the form `A<n>` (working-session decisions, e.g. A4) and `F-0x`
(empirical findings F-01 to F-07) originate from the scratch gate-proof
session. Their durable substance is codified in D-16 and in
[`docs/verification/gate_proof_findings.md`](../verification/gate_proof_findings.md),
where each finding carries its own anchor
([F-01](../verification/gate_proof_findings.md#f-01) through
[F-07](../verification/gate_proof_findings.md#f-07)); an `A<n>` citation
resolves there too. New durable rules always graduate into a D-number here or
a CLAUDE.md rule.

## CLAUDE.md rule crosswalk

CLAUDE.md hard rules are the enforcement surface; decisions are the
authority. The mapping:

| CLAUDE.md rule | Governing decision(s) |
|---|---|
| 1 (pins; amendment required) | D-05, D-06 |
| 2 (1.12 / v2 deferred) | D-05 |
| 3 (profiler uncontracted; transforms contracted SQL) | D-04 |
| 4 (contracts all-or-nothing) | D-06, D-08 |
| 5 (only not_null trusted; tests for the rest) | D-12, evidence [F-06](../verification/gate_proof_findings.md#f-06) |
| 6 (never weaken a contract) | D-08 |
| 7 (no materialized views) | D-07 |
| 8 (ownership-manifest checksums) | D-09 |
| 9 (engine emits models, never DDL) | D-07 |
| 10 (gate three under uv run; top-level `datacontract test` unused) | D-12, D-16 |
| 11 (properties hand-authored; sync output reviewed) | D-16, evidence [F-02](../verification/gate_proof_findings.md#f-02)/[F-05](../verification/gate_proof_findings.md#f-05) |
| 12 (unified event star; tables; projections as views) — planned | D-17 |
| 13 (canonical_key v2, deterministic payloads) — planned | D-18 |
| 14 (registry binding; fact key; declared grain) — planned | D-19 |

Rules marked planned land with the gold specification pull requests.
