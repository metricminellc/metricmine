# Decision Register

> Repo path: `docs/decisions/decision-register.md`
> The authoritative in-repo index of project decisions. Commit bodies and docs
> cite decisions by ID (`D-0x`); every ID cited anywhere in this repository
> resolves to an entry here. Changing a pinned version, a gate, or an
> architecture boundary requires amending this register in its own
> documentation pull request before the implementing change lands.

Decisions were made in working sessions during July 2026 and are condensed
here in full operational substance. D-01 through D-14 were settled July 10 to
11; D-15 through D-20 were adopted in the July 11 decision-record revision.
Extended context and analysis live in project records maintained outside the
repository; nothing in this repo depends on those records. Decision Record 002
(July 12, 2026) carries D-21 through D-25; Decision Record 001 Rev. 3 carries
D-01 through D-20 unchanged. Decision Record 003 (July 31, 2026) carries D-26
through D-28 and Amendments A and B to Record 001.

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
| [D-15](#d-15) | Committed sample dataset: Online Retail II | adopted |
| [D-16](#d-16) | Gate-three mechanism: sync then test under uv run | adopted |
| [D-17](#d-17) | Gold is the unified event star | adopted |
| [D-18](#d-18) | Keying scheme v2 (canonical_key v2) | adopted |
| [D-19](#d-19) | Context binds by content address (schema-key registry) | adopted |
| [D-20](#d-20) | Gate-two invocation and CI profile resolution | adopted |
| [D-21](#d-21) | Proposer invocation architecture | adopted |
| [D-22](#d-22) | Prompt governance and lineage | adopted |
| [D-23](#d-23) | Context discipline: grounding without retrieval | adopted |
| [D-24](#d-24) | Agent UX: propose, review, approve on existing surfaces | adopted |
| [D-25](#d-25) | Evaluation: the golden-profile set | adopted |
| [D-26](#d-26) | Repository public before Phase 5 | adopted |
| [D-27](#d-27) | Bronze lands in CI via make ingest | adopted |
| [D-28](#d-28) | Contract-declared enforcement severity | adopted |

## The decisions

### D-01
**Repository identity and framing.** This repository is
`metricminellc/metricmine`, a reference implementation designed to run
locally, end to end, on one command. Private until the serving demo is
presentable, then public with a `v0.1.0` tag. Any future cloud deployment is a
separate repository that depends on this one, never a fork.
Amended July 31, 2026 (Record 003, Amendment A): the publication-timing
clause is superseded by [D-26](#d-26); every other clause stands.

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
cleanup proposer and the gold mapping proposer. Both emit ODCS
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
gate one `datacontract lint`, run once per contract (the lint command takes a
single location, not a glob); gate two `dbt build` (compile-time shape
enforcement), exact invocation per D-20; gate three per D-16 — alongside ruff
and pytest. The toolchain was proven end to end in a scratch gate-proof
session before Phase 1 exit; findings in
[`docs/verification/gate_proof_findings.md`](../verification/gate_proof_findings.md).

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
**Committed sample dataset.** Online Retail II (Daqing Chen, UCI
Machine Learning Repository, CC BY 4.0): a deterministic, complete-invoice,
one-month extract under 5 MB, produced by a committed fetch script; the raw
download stays gitignored. The Kaggle mirror is acceptable with UCI cited.
`source-faker` remains the keyless synthetic path.

### D-16
**Gate-three mechanism.** Gate three is
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
**Gold is the unified event star.** The terminal gold layer is the
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
**Keying scheme v2.** All record and schema keys use
`canonical_key` v2: payloads parse and serialize compact with sorted keys,
lowercase, SHA-256, hex; scalars and manifests cast to text, lowercase,
whitespace stripped, hyphens preserved. Deterministic, case-, whitespace-,
and order-insensitive. A deliberate, documented delta from the 2023 baseline
scheme (which was insertion-order sensitive and hyphen-stripping); the
rebuild carries zero legacy data, so no key migration exists. Baseline
record: [`docs/spec/current-state/data-capture-baseline.md`](../spec/current-state/data-capture-baseline.md).

### D-19
**Context binds by content address.** Business context and
contract references attach to data through schema keys in the
`context_registry` table: one row per schema key carrying the entity group,
the governing contract name and version, and the compiled context. Contracts
are never embedded in payloads. The context compiler owns the registry; the
MCP context tools read it.

### D-20
**Gate-two invocation and CI profile resolution.** Gate two is
`uv run dbt build --project-dir transform --target local`, parallel to gate
three. The contract-gates CI job sets `DBT_PROFILES_DIR=transform`:
`--project-dir` governs only where dbt finds `dbt_project.yml`, while dbt
resolves `profiles.yml` from the working directory and then `~/.dbt/` unless
the profiles directory is set, and `profiles.yml` lives inside `transform/`
per D-11 while CI runs from the repository root. Every gate step is guarded
to skip cleanly while `contracts/` is empty or `transform/dbt_project.yml` is
absent. Standing obligation: the pull request that initializes the dbt
project splits the guard to per-gate granularity — gate one activates on a
contract alone, gate two on the dbt project alone, gate three on both.
Clarifies D-12; complements D-16.
Amended July 31, 2026 (Record 003, Amendment B): decision text unchanged;
the CI mechanization is recorded as an absolute DBT_PROFILES_DIR (#41), the
profile database path env-resolved via MM_WAREHOUSE_PATH with a
repo-root-relative default (#42; `datacontract dbt test` re-invokes dbt
from inside the project directory,
[F-09](../verification/gate_proof_findings.md#f-09)), and the
bronze-landing step ([D-27](#d-27)) ordered before the gates. The relative
forms are recorded failure modes.

### D-21
**Proposer invocation architecture.** Each proposer is one structured
call to the Messages API: claude-sonnet-5, pinned (the model ID is a
fixed snapshot); GA structured outputs (output_config.format
json_schema), so the response cannot violate the proposal schema; effort
explicit, max_tokens capped; the anthropic SDK is a locked dependency
from Phase 6. The model emits a structured proposal; deterministic code
renders canonical ODCS YAML with stable key order. Validation failures
retry at most twice with errors fed back, then fail closed with nothing
written; writes are atomic. No tools, no MCP, no loops: a proposer reads
one profile artifact and writes only to the gitignored proposals/ outbox.
Full text: Decision Record 002; design: docs/spec/agent-layer.md.

### D-22
**Prompt governance and lineage.** Prompts are versioned repository
artifacts at src/metricmine/agents/prompts/ with semver-and-changelog
headers read at runtime, changed only by pull request under D-14, rolled
back by revert. Every proposed contract stamps provenance into ODCS
customProperties (proposedBy, proposerVersion, promptVersion, modelId,
profileHash, proposedAt); hand-written contracts carry the same keys with
proposedBy: human from Phase 3 onward. Full request detail lives in a
local proposal record. The injection posture is stated: profile sample
values are untrusted data; defense is layered (delimiting,
schema-constrained output, validator, lint, human gate); contracts are
never executed as code. Prompt text is authored in Phase 6, after the
spine.

### D-23
**Context discipline: grounding without retrieval.** The proposers use no
retrieval: no vector store, no embeddings, no similarity search. The
versioned profile artifact is the sole context, injected complete. The
profiler owes the agents deterministic serialization, a schema_version
field, a content hash, and token-budget caps (requirements for
docs/spec/profiler.md). A deterministic validator gates every proposal:
groundedness (every referenced column exists in the profile; hallucinated
columns enforced to zero), staleness (bound to the profile hash),
completeness (grain declared per category), and datacontract lint.

### D-24
**Agent UX: propose, review, approve on existing surfaces.** make
propose-silver and make propose-mapping write a validated draft contract
plus proposal record to proposals/ (gitignored) and print a rationale
summary with profile evidence, plus a diff against the current contract
on regeneration. Review and edit happen in the editor; business context
added there lands in the contract fields the context compiler harvests.
Approval is the existing contract-only pull request with a version bump
(D-08); merge is approval; rejected drafts never leave the outbox. make
demo stays keyless replay; a regenerate path chains the proposers live.
No new UI surface in the MVP.

### D-25
**Evaluation: the golden-profile set.** Committed fixture profiles (Online
Retail II per D-15, faker, optionally one pathological case) under
tests/agents/. Offline assertions run keyless in the pytest lane every CI
run (render path against recorded proposals, validator against
constructed inputs). A manual live lane, make eval-agents, reports
first-attempt lint pass rate and first-attempt groundedness pass rate
with cost actuals, echoing the generate-and-verify posture D-10 keeps in
the SDLC loop.
LLM-as-judge and automated optimization are deferred by intent. Phase 6
exits with fixtures committed, offline assertions green, and one recorded
live run.

### D-26
**Repository public before Phase 5.** Public as of July 30, 2026, with branch
protection, PR-only squash-only merges, and the two required status
contexts mechanized first, plus the on-push main trigger so every merge
earns its own public check. The v0.1.0 tag remains a Phase 5 milestone;
publication no longer waits for it. Clean-room and provenance rules are
unaffected: NOTICE stands, the 2023 repository stays private. Supersedes
D-01's publication-timing clause (Amendment A); every other D-01 clause
stands. Ratified in Decision Record 003.

### D-27
**Bronze lands in CI via make ingest.** The contract-gates job lands bronze
with the same command a laptop runs, guarded to run only when gate two or
gate three will run, ordered before the gates. The Makefile pre-provisions
the pinned connector venv (airbyte-source-file 0.3.15, numpy<2,
uv-provisioned CPython 3.10), so the step runs with AIRBYTE_OFFLINE_MODE=1:
no Airbyte registry dependency, no telemetry, deterministic from the
committed sample (D-15). Rejected alternatives: a pinned seed script (a
second loading path CI trusts but no laptop runs) and dbt-duckdb
external_location (diverges from bronze-as-landed). Measured cost about 30
seconds per gated PR. Mechanized at PR #42. Ratified in Decision Record 003.

### D-28
**Contract-declared enforcement severity.** Every quality rule intended to
gate declares severity: error inside the contract. At datacontract-cli
1.0.12 sync-generated tests default to warn and the composite primaryKey
uniqueness test is hardcoded warn (evidence F-08), so contract-declared
severity is the only gate-capable channel; the tool honors
error/critical/high/fatal on quality rules carrying a query. The warn
composite test is a non-gating advisory twin. Weakening a severity is
weakening a contract and falls under D-08's version-bump discipline. Rule 5
unchanged: uniqueness lives in tests, never trusted constraints. Exercised
at contract v1.1.0 (#43); proven green at #44 and red at #45. Ratified in
Decision Record 003.

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
| 5 (only not_null trusted; tests for the rest) | D-12, evidence [F-06](../verification/gate_proof_findings.md#f-06)/[F-08](../verification/gate_proof_findings.md#f-08) |
| 6 (never weaken a contract) | D-08, D-28 |
| 7 (no materialized views) | D-07 |
| 8 (ownership-manifest checksums) | D-09 |
| 9 (engine emits models, never DDL) | D-07 |
| 10 (gate three under uv run; top-level `datacontract test` unused) | D-12, D-16; gate-two mechanics per D-20 |
| 11 (properties hand-authored; sync output reviewed) | D-16, evidence [F-02](../verification/gate_proof_findings.md#f-02)/[F-05](../verification/gate_proof_findings.md#f-05) |
| 12 (unified event star; tables; projections as views) | D-17 |
| 13 (canonical_key v2, deterministic payloads) | D-18 |
| 14 (registry binding; fact key; declared grain) | D-19 |
| 15 (proposer runtime: one structured call; no tools/MCP/loops; outbox-only) | D-21, D-23 |
| 16 (versioned prompts; contract provenance) | D-22 |
| 17 (human-only draft-to-contract flow; keyless make demo) | D-24, D-08 |

All decisions in this register are adopted: D-01 through D-20 as of the
July 11, 2026 revision (Decision Record 001 Rev. 3), D-21 through D-25 as
of the July 12, 2026 revision (Decision Record 002), and D-26 through D-28
as of the July 31, 2026 revision (Decision Record 003). D-20 has no dedicated
CLAUDE.md rule; its substance
is encoded directly in
[`.github/workflows/contract-gate.yml`](../../.github/workflows/contract-gate.yml),
and its guard-split obligation lands with the pull request that initializes
the dbt project. Like D-20, D-26 through D-28 carry no dedicated CLAUDE.md
rule: D-26 lives in the repository settings and branch protection, D-27 in
the workflow's bronze-landing step, and D-28 in the contracts' severity
declarations (evidence
[F-08](../verification/gate_proof_findings.md#f-08)).
Implementation of D-17 through D-19 lands in the gold phase
and D-21 through D-25 in Phase 6; adoption is not contingent on it.
