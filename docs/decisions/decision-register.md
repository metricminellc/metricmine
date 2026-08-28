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
through D-28 and Amendments A and B to Record 001. Decision Record 004
(August 1, 2026) carries D-29 and D-30 and Amendment C to D-16. Decision
Record 005 Rev. 2 (August 13, 2026) carries D-31 through D-33, the serving
layer, and Amendment D to D-32. Decision Record 006 (August 14, 2026)
carries Amendment E to D-03 and D-33. Decision Record 007 (August 22,
2026) carries D-34, D-35, Amendments F through J, and findings F-26
through F-28. Decision Record 008 part one (August 24, 2026) carries
D-36 and Amendments K, L, and M; part two follows with Arc 5b. Decision
Record 009 (August 28, 2026) carries Amendment N to D-05 and findings
F-30 and F-31.

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
| [D-05](#d-05) | Version pins; dbt 1.12 adopted (Amendment N); Core v2 deferred | adopted |
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
| [D-29](#d-29) | The auto-modeling engine specification | adopted |
| [D-30](#d-30) | Registry population: compiled-context artifact, literal-carrying model | adopted |
| [D-31](#d-31) | Serving layer: one shared query module; thin MCP server | adopted |
| [D-32](#d-32) | MCP SDK: official mcp as a project dependency | adopted |
| [D-33](#d-33) | Demo export: content equality by query, never bytes | adopted |
| [D-34](#d-34) | Proposer model selection: pinned default, allow-listed override | adopted |
| [D-35](#d-35) | Proposer stances and the adoption scan | adopted |
| [D-36](#d-36) | The typed surface: a materialized mart by default | adopted |

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
Amended August 14, 2026 (Record 006, Amendment E): the committed artifact
is `demo/demo.duckdb`. A directly opened DuckDB database takes its
catalog name from the file stem, so the originally named
`demo/gold.duckdb` opens as catalog `gold` holding schema `gold`, and at
the pinned 1.4.3 every two-part `gold.<x>` reference — SELECT and CREATE
alike — fails as ambiguous
([F-25](../verification/gate_proof_findings.md#f-25)). Path only: the
export mechanism, the D-33 content-equality claim, the gitignore
exception, and the D-31 keyless default all follow the new path;
everything else in this decision stands.

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
Amended August 28, 2026 (Record 009, Amendment N): the dbt line moves to
1.12. dbt-core `>=1.12,<1.13` (resolved 1.12.3) with dbt-duckdb
`>=1.11,<1.12` (resolved 1.11.0); transform/dbt_project.yml mirrors the
range as require-dbt-version [">=1.12.0", "<1.13.0"]. The condition this
decision set is met: 1.12.0 went GA on July 16, 2026, 1.11 leaves
critical support on December 18, 2026, and dbt-duckdb 1.11.0 is the
adapter line developed against 1.12. The move was proven before it
bound: the full gate re-proof at 1.12.3 lands every lane, gate, the
adoption scan, and the D-33 digest at their head values with zero
deprecations, and datacontract-cli 1.0.12 (D-06, unchanged) shells out
to the project's dbt and needs nothing
([F-30](../verification/gate_proof_findings.md#f-30)). Two dependencies
arrive with the line and are named here because rule 1 pins by the
lock: dbt-core-experimental-parser, the v2 parser binary dbt-core 1.12
requires at a pre-release (2.0.0b2 in uv.lock, pinned by the sdist hash
and by that sdist's own wheel digest, fetched from GitHub releases at
install time), and metricflow. Neither is a project dependency, neither
is invoked by any target, and both move only with the dbt-core lock.
dbt Core v2 stays deferred: the 1.12 `--use-v2-parser` flag is a
parse-only probe for this project, never a build path
([F-31](../verification/gate_proof_findings.md#f-31)), and the
2.0.0-beta.2 engine's own build of the emitted project reproduces the
digest with its packaging and driver gaps recorded. The deferral lifts
only by a further amendment on a verified GA. The 1.11.14 lock refresh
that preceded this amendment was a chore inside the previous range and
needed no amendment (rule 1).

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
Amended August 22, 2026 (Record 007, Amendment G): the count is of named
proposers, each one process with one prompt lineage and one provenance
identity. Stances (D-35) are modes and add no agent; the adoption scan
and the batch driver are deterministic sequencing and add no agent; a
third named proposer, a runtime tool, or a runtime loop still does. The
SDLC clause permits Claude Code to invoke a proposer on a human's
instruction and report the result; it does not permit unattended
re-invocation around a fail-closed exit.

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
Amended August 1, 2026 (Record 004, Amendment C): the hand-authored
properties clause is scoped to the human-owned silver plane. Engine-owned
gold models carry engine-emitted properties files at the sync fixed point
per [`docs/spec/engine.md`](../spec/engine.md) §6
([F-14](../verification/gate_proof_findings.md#f-14)), reviewed as
generated code in regeneration PRs under the D-09 ownership manifest.
Every review obligation in the clause — sync output as proposal, export
as scaffold only, the duplicateValues deletion rule — stands unchanged on
both planes.
Amended August 22, 2026 (Record 007, Amendment J): at adoption, the
human-owned silver properties file may be CREATED by `datacontract dbt
sync` from an approved contract, which writes exact DuckDB data types
([F-27](../verification/gate_proof_findings.md#f-27)), and completed by
the deterministic `enforce-properties` helper, which writes only the two
keys the contract already implies (`contract.enforced: true`; `not_null`
constraints on required columns). The file stays human-owned and is
reviewed in the model PR; every review obligation above applies
unchanged.

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
Amended August 24, 2026 (Record 008, Amendment K): the
materialized-marts clause is superseded by [D-36](#d-36). The engine
emits the typed surface per category as a materialized mart by default
behind `engine.marts`, with the projection view kept beside it in the
committed default. Every other clause stands: table materialization for
contracted objects, the uncontracted derivative posture of the typed
surface, and the serving clause.

### D-18
**Keying scheme v2.** All record and schema keys use
`canonical_key` v2: payloads parse and serialize compact with sorted keys,
lowercase, SHA-256, hex; scalars and manifests cast to text, lowercase,
whitespace stripped, hyphens preserved. Deterministic, case-, whitespace-,
and order-insensitive. A deliberate, documented delta from the 2023 baseline
scheme (which was insertion-order sensitive and hyphen-stripping); the
rebuild carries zero legacy data, so no key migration exists. Baseline
record: [`docs/spec/current-state/data-capture-baseline.md`](../spec/current-state/data-capture-baseline.md).
Amended August 24, 2026 (Record 008, Amendment M): the canonical text is
also the served text. Stored value payloads are the canonical lowercased
serialization, so every value read through the star, its projections,
and its marts is lowercased text. This is deliberate and stated at the
serving surface ([`docs/spec/serving.md`](../spec/serving.md) §2 and the
server instructions), not a defect. The key scheme is unchanged. A
case-preserving served payload was weighed against the August 23
pressure measurements and declined for the v1.0.0 line; reopening it is
a register decision and a post-tag experiment candidate.

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
Amended August 22, 2026 (Record 007, Amendment F): two clauses. First,
the SDK pin binds at `anthropic>=1.0,<1.1` (resolved 1.0.0 in uv.lock),
a normal project dependency from the harness PR onward; the July
citation of 0.116.0 is superseded, the 0.x line being legacy as of
August 20, 2026, and the 1.0 surface (`output_config.format`,
`output_config.effort`; `temperature` removed) is the surface this
decision describes. Co-resolution with the committed lock was probed
before the pin bound, and the live call was proved on the Mac before
this amendment merged
([evidence](../verification/evidence/2026-08-21_preN_probe_transcript.md),
[live](../verification/evidence/2026-08-22_sessionN_probe_p3_live.log)).
Recorded fallback, exercised only on a documented live failure:
`anthropic>=0.125,<1`. Second, the structured-output schema each
proposer emits against is its PROPOSAL schema under
`docs/spec/agent-layer/`, a structured-outputs-compatible projection of
the contract shape; deterministic render produces the ODCS document, and
the frozen mapping-contract schema validates the rendered output rather
than travelling to the API, which cannot compile it
([F-26](../verification/gate_proof_findings.md#f-26)). Everything else
in the decision stands; the default model is now governed by D-34.

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
Amended August 22, 2026 (Record 007, Amendment I): `proposedBy` gains no
values. Every proposed contract additionally carries `proposerStance`
(D-35); amendment proposals carry `amendsContract` as
`<id>@<version>#sha256:<hash>` over the committed contract's canonical
bytes. The proposal record carries the stance, the ordered governed
inputs with their hashes, and the operator's intent verbatim.

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
Amended August 22, 2026 (Record 007, Amendment H): "sole context" reads,
from here, as the sole evidence context. A stance (D-35) receives a
fixed, configured list of governed inputs and no others: the versioned
profile artifact; for `amend`, the single committed contract named by
configuration and the operator's intent string. Every input is injected
complete, selected by path and never by search, hashed, and bound into
the proposal; any hash moving between read and write fails staleness. No
retrieval is introduced.

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

### D-29
**The auto-modeling engine specification is adopted.**
[`docs/spec/engine.md`](../spec/engine.md) governs the engine end to end:
the mapping contract shape with every mapping element first-class and its
frozen machine schema
([`docs/spec/engine/mapping-contract.schema.json`](../spec/engine/mapping-contract.schema.json)
— the same JSON Schema the Phase 6 gold mapping proposer emits structured
output against per D-21, discharging the agent layer's Phase 4 schema
obligation); flat placement of mapping contracts in `contracts/` under
the category-naming rule, with quality rules banned in mapping contracts
as dead letters; the dual-implementation keying rule (record keys in SQL
at build time, schema keys in Python at emission time, a committed golden
vector set, and a SQL-versus-Python consistency test; payload values
render as canonical text; payload nulls are included as JSON null);
emission mechanics (generated-by headers naming both source contracts,
a timestamp-free ownership manifest, write-if-changed atomic writes,
fail-closed validation, drift refusal per D-09 and rule 8); emission at
the sync fixed point; conservation enforcement as error-severity sql
rules in the gold star contract per D-28 (C1 arithmetic, C2 anti-joins,
C3 registry coverage, C4 payload validity, grain enforcement); and
provenance for pattern-derived contracts (profileHash absent with a
provenanceNote, extending the agent-layer Appendix B pattern). Evidence:
[F-11](../verification/gate_proof_findings.md#f-11) through
[F-14](../verification/gate_proof_findings.md#f-14). Ratified in Decision
Record 004.

### D-30
**Registry population: compiled-context artifact plus a literal-carrying
emitted model.** The context compiler merges the governing contracts and
their harvested context fields into a committed, versioned, deterministic
compiled-context artifact (`context/compiled/vNNNN.json` with a meta
sidecar, the profiles/ artifact discipline: canonical JSON, deterministic
content only, write-if-changed, immutable monotonic versions). The engine
emits `context_registry` as a dbt model whose rows are SQL VALUES
literals carried from that artifact at emission time. Consequences, and
why this mechanism won: every warehouse write stays inside `dbt build`
(D-07); there are no build-time file reads, so the
[F-09](../verification/gate_proof_findings.md#f-09) working-directory
class cannot reach the registry; the demo path stays keyless and
byte-reproducible; C3 stays a gate-capable test; and registry changes
arrive as reviewable regeneration pull requests under the ownership
manifest (D-09, D-19). Ratified in Decision Record 004.

### D-31
**Serving layer: one shared query module; thin MCP server.** All gold
access flows through `src/metricmine/query.py`, implementing the D-17
serving clause in the D-11 read-only posture. The MCP server at
`src/metricmine/server/` is a thin stdio adapter over the module: the
five spec tools and nothing else. Read-only is enforced three layers
deep — `read_only=True` connections, `enable_external_access=false` with
`lock_configuration=true`, and a single-statement SELECT gate — and every
query result is row-capped with an explicit truncation flag. The database
resolves `MM_SERVE_DB` first, then `demo/demo.duckdb` (D-03 as amended,
Amendment E), keeping the keyless posture. The D-31 number was reserved and left unminted at
Record 004 for the rule-11 scope; it mints here, keeping the numbering
dense and the history honest. Full design:
[`docs/spec/serving.md`](../spec/serving.md).
Amended August 24, 2026 (Record 008, Amendment L, jointly with D-32):
the five-tool surface gains no tool. `list_fact_categories`
additionally returns, per category, `typed_table` (the materialized
mart when emitted, else the projection view, else null),
`typed_columns` (its columns in ordinal order), and `query_hint` (one
paragraph steering analytical questions to the typed surface and naming
the star tables as the provenance layer for `lookup_record` and audit).
The server instructions open with the same steer and state the D-18
served-case posture (Amendment M). The compiled context carries a
`typed_surface` pointer on the category-group entries (the D-30
artifact gains the key; compiled schema_version 1.1.0), so
`get_context` and `list_fact_categories` agree by construction.
Evidence: the August 23 pressure findings measured an agent exploring
the star unaided through this server; the steer is the direct remedy.
Full text: Decision Record 008.

### D-32
**MCP SDK selection and pin.** The official `mcp` package at 2.0.x,
added as a project dependency (`mcp>=2.0,<2.1`, resolved 2.0.0 in
uv.lock) — the server imports it, so an isolated tool cannot serve
(contrast D-06). 2.0 is the current stable line and tracks the current
MCP specification. Probe P1 verified the stdio server, type-hint
schemas, structured output (a concrete TypedDict return is required; a
bare dict yields none), and a live Claude Desktop discovery-plus-round-
trip on the Mac at 2.0.0 before this pin bound (August 13, 2026). The
recorded fallback, exercised only on a live failure and documented as a
finding: `mcp>=1.28,<2` on the maintenance line. Never `latest` (rule 1).
Amended August 13, 2026 (Record 005 Rev. 2, Amendment D): the 2.0.x pin is
superseded by the recorded fallback, `mcp>=1.28,<2`, resolved 1.29.0 in
uv.lock. The 2.0 pin is unsatisfiable in this project: PyAirbyte (D-15)
requires `fastmcp>=3.0`, and every fastmcp 3.x caps `mcp<2.0`, so
`mcp>=2.0` and `airbyte>=0.53` cannot co-resolve
([F-22](../verification/gate_proof_findings.md#f-22)). Every probed fact
in the decision above holds at 1.29.0, re-measured before this amendment
bound: protocol `2025-11-25`, unchanged from 2.0.0; a concrete TypedDict
return yields an output schema and structured content, a bare dict yields
neither. The server class is `FastMCP` from `mcp.server.fastmcp`, not the
2.0 `MCPServer`. Everything else in the decision stands, the
project-dependency posture above all.
Amended August 24, 2026 (Record 008, Amendment L, jointly with D-31):
the serving steer rides the pinned SDK surface unchanged. The added
`FactCategory` fields serialize through the same TypedDict mechanism
this decision verified, and the steer paragraph travels through the
`FastMCP` instructions parameter already in use. No SDK change, no pin
change, no new tool.

### D-33
**Demo export: content equality by query, never byte equality.**
`make export-demo` builds `demo/gold.duckdb` — the only committed
database artifact, exactly as D-03 has always said — from the keyless
replay path: attach the working warehouse read-only, copy the gold
tables, recreate the typed view from the catalog SQL re-anchored to the
export's own catalog, checkpoint, verify. Verification is per-table
equal counts plus symmetric EXCEPT zero, and an ordered content digest
over the typed view compared across direct per-file connections. A
DuckDB file embeds storage details, so byte-level determinism is a claim
this project does not need and will not make. Refresh only at
gold-content changes: regeneration merges and tags. Mechanism and probed
measurements: [`docs/spec/serving.md`](../spec/serving.md) §8.
Amended August 14, 2026 (Record 006, Amendment E): the export target is
`demo/demo.duckdb`, following D-03 as amended
([F-25](../verification/gate_proof_findings.md#f-25)). Mechanism and
claim stand unchanged; the re-anchored view and the module's two-part
`gold.<x>` SQL both bind cleanly in the non-colliding catalog `demo`,
verified on every serving path before this amendment bound.

### D-34
**Proposer model selection: pinned default, allow-listed override.** The
proposers call `claude-sonnet-5` by default, a pinned snapshot ID that
moves only by amendment here. An operator may swap the model for a run,
in this precedence: `--model ID` on the command line, then
`MM_PROPOSER_MODEL` in the environment, then the default. The allow-list
is `claude-sonnet-5`, `claude-opus-5`, and `claude-fable-5`; membership
is measured, not preferred: an ID must support both structured outputs
and the effort parameter, carry a pinned rate row in
`src/metricmine/agents/models.py`, and have answered a live structured
call on this project's account (verified August 22, 2026; Haiku 4.5 is
excluded because it lacks effort support). An unlisted ID, an alias, or
`latest` fails closed before any API call, naming the allow-list. The
model actually used is stamped as `modelId` in the contract's provenance
(D-22) and recorded with its source (`default`, `env`, or `flag`) and its
rate row in the proposal record, so cost and authorship audit from the
record alone. Prompts are model-agnostic: a model swap never bumps a
prompt version. The live eval lane (D-25) honors the same override,
which enables comparison without performing it. Adding or removing a
model is a register amendment in its own documentation PR (rule 1
discipline). Full text: Decision Record 007.

### D-35
**Proposer stances and the adoption scan.** Each proposer (D-10) may run
in a fixed set of governed stances: `cleanup`, `describe`, `amend` for
the silver cleanup proposer; `propose`, `amend` for the gold mapping
proposer. A stance is a mode, not an agent: same process, harness,
single call, retry budget, and outbox, adding only a versioned prompt, a
proposal schema, a validator branch, and a provenance stamp. Every
stance is human-invoked and writes only to the outbox. `describe`
consumes the target table's own profile artifact and refuses when a
contract with that id already exists. `amend` consumes the profile, the
committed contract it amends, and a human-typed intent, recorded
verbatim; it emits a declared change set that deterministic code applies
as a patch over the committed document, so the diff is the declared set
by construction; additions enter optional with a declared follow-up
tightening ([F-28](../verification/gate_proof_findings.md#f-28)). No
stance emits quality-rule severities, classifications, SLAs, or
ownership; templated rules render by code at the severities the
committed contracts established. An amendment never weakens a contract
(D-08): the validator classifies every change as widening, neutral, or
narrowing; narrowing is refused unless `--allow-relaxation` is passed,
and then renders at a major bump with a printed rule-6 warning. Grain
proposed by any stance is unverified until `make verify-grain` measures
it ([F-10](../verification/gate_proof_findings.md#f-10)). The adoption
scan is deterministic code, never an agent: it derives a review queue
from the model tree, the contracts, the profiles, the configuration, and
the read-only catalog on every run, writes it to the outbox, and stores
nothing; the batch driver walks that queue with a cap, one call per
item, never re-invoking a failed item. The vanilla scope at adoption:
the silver plane and the committed sample; foreign gold marts (rule 12)
are reported, never adopted. Evidence: the August 21 to 22 adoption lab
([F-27](../verification/gate_proof_findings.md#f-27),
[F-28](../verification/gate_proof_findings.md#f-28)). Full text:
Decision Record 007.

### D-36
**The typed surface: a materialized mart by default.** For every fact
category the engine emits a materialized typed mart,
`mart_<category>_typed`, governed by the `engine.marts` configuration:
`table` emits the mart, `view` emits the projection view (the pre-D-36
set), `both` emits both, and `both` is the committed default. An
unrecognized value fails closed before anything emits. The mart is the
typed projection's SELECT materialized as a dbt `table`, lean: the
typed business columns plus `fact_hash_id` as the provenance pointer
back to the star, resolvable by `lookup_record`. Derived identifiers
stay inside the dimension payload and are not carried. Rows are ordered
by the declared time column so zone maps prune time-window scans. The
mart is uncontracted and derivative exactly as the view is (D-17 as
amended, Amendment K), carries the derivative generated-by header,
lands under the ownership manifest (D-09), and joins the byte oracle
and the demo artifact. `mart_` joins the reserved model-name prefixes
in the frozen mapping-contract schema, the proposal validator, and the
engine reader. At transaction grain the mart is one row per fact row,
so `COUNT(*)` is the row count there. Evidence, environment stated: in
a 2-CPU sandbox at 1 to 21 million synthetic rows (August 23, 2026),
analytical questions answered 100 to 2,000 times faster against the
mart than through the view, for a one-time mart build of 61 to 151
seconds; at the committed sample the demo content digest is unchanged
and `dbt build` gains one node. Full text: Decision Record 008.

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
| 2 (v2 deferred; the 1.12 parser flag is parse-only) | D-05 (Amendment N), evidence [F-31](../verification/gate_proof_findings.md#f-31) |
| 3 (profiler uncontracted; transforms contracted SQL) | D-04 |
| 4 (contracts all-or-nothing) | D-06, D-08 |
| 5 (only not_null trusted; tests for the rest) | D-12, evidence [F-06](../verification/gate_proof_findings.md#f-06)/[F-08](../verification/gate_proof_findings.md#f-08) |
| 6 (never weaken a contract) | D-08, D-28 |
| 7 (no materialized views) | D-07 |
| 8 (ownership-manifest checksums) | D-09 |
| 9 (engine emits models, never DDL; mapping-contract placement) | D-07, D-29 |
| 10 (gate three under uv run; top-level `datacontract test` unused) | D-12, D-16; gate-two mechanics per D-20 |
| 11 (properties hand-authored on the silver plane; sync-created at adoption; engine-emitted on gold; sync output reviewed) | D-16 (Amendments C, J), D-29, evidence [F-02](../verification/gate_proof_findings.md#f-02)/[F-05](../verification/gate_proof_findings.md#f-05)/[F-14](../verification/gate_proof_findings.md#f-14)/[F-27](../verification/gate_proof_findings.md#f-27) |
| 12 (unified event star; tables; the typed mart default; projections) | D-17, D-36 |
| 13 (canonical_key v2, deterministic payloads) | D-18 |
| 14 (registry binding; fact key; declared grain) | D-19 |
| 15 (proposer runtime: one structured call; proposal schema projection; allow-listed model override; governed inputs per stance; no tools/MCP/loops; outbox-only) | D-21 (Amendment F), D-23 (Amendment H), D-34, D-35, evidence [F-26](../verification/gate_proof_findings.md#f-26) |
| 16 (versioned prompts; contract provenance incl. proposerStance and amendsContract; pattern-derived absence rule) | D-22 (Amendment I), D-29 |
| 17 (human-only draft-to-contract flow; no relaxation without the flag; report-and-stop on fail-closed; keyless make demo) | D-24, D-08, D-10 (Amendment G), D-35 |
| 18 (serving boundary: shared module, three-layer read-only, capped results, the typed-surface steer) | D-31, D-32, D-33 |

All decisions in this register are adopted: D-01 through D-20 as of the
July 11, 2026 revision (Decision Record 001 Rev. 3), D-21 through D-25 as
of the July 12, 2026 revision (Decision Record 002), D-26 through D-28
as of the July 31, 2026 revision (Decision Record 003), D-29 and D-30
(with Amendment C to D-16) as of the August 1, 2026 revision (Decision
Record 004), D-31 through D-33 as of the August 13, 2026 revision
(Decision Record 005), D-34 and D-35 (with Amendments F through J)
as of the August 22, 2026 revision (Decision Record 007), and D-36
(with Amendments K, L, and M) as of the August 24, 2026 revision
(Decision Record 008 part one), and Amendment N to D-05 as of the
August 28, 2026 revision (Decision Record 009). D-20 has no
dedicated
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
