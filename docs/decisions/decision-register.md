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
D-36 and Amendments K, L, and M; part two lands with Arc 5b (below). Decision
Record 009 (August 28, 2026) carries Amendment N to D-05 and findings
F-30 and F-31. Decision Record 010 (August 29, 2026) carries D-37, the
local enforcement hooks in the SDLC layer, and finding F-32. Decision
Record 008 part two (Arc 5b) carries D-38 through D-40 and Amendments
O, P, and Q, completing the record part one opened. Decision Record
011 (September 2, 2026) carries D-41, the multi-source proof,
Amendments R through W, and findings F-36 through F-53. Decision Record
012 (September 6, 2026) carries D-42, the supported platforms and the task
entry point, and findings F-54 and F-55. Decision Record 013 (October 3,
2026) carries Amendment X to D-04 and D-05 (the dbt Core v2 move),
Amendment Y to D-20 (gate two as run, then test), the confirmation of
D-06 under v2, and finding F-66. Decision Record 014 (October 17, 2026)
carries D-43, governed documents, Amendment Z to D-35 (the scan's
document states), and findings F-68 to F-71. Decision Record 015
(October 19, 2026) carries Amendment AA to D-30 and D-31 jointly
(governed documents served: the compiled-schema bump, the harvest, the
budget, the staleness check), Amendment AB to D-31 (the tools'
annotations and the query tool's gold scope), and finding F-72.
Decision Record 016 (October 26, 2026) carries D-44, governed meaning
(the glossary and ontology registers, the binding by id and content
digest, the change-set command, the module's boundary), and Amendment
AC to D-35 (the scan's meaning states). The
lettering past Z: amendments take two letters in spreadsheet column
order (AA, AB, and so on through AZ, then BA).

**Status meanings.** `adopted`: in force. `proposed`: agreed in working
session, applied by the plans below, formal adoption pending; treat as binding
unless amended.

## Index

| ID | Decision | Status |
|---|---|---|
| [D-01](#d-01) | Repository identity and framing | adopted |
| [D-02](#d-02) | Apache-2.0 license; provenance in NOTICE | adopted |
| [D-03](#d-03) | Working warehouse gitignored; demo export committed | adopted |
| [D-04](#d-04) | dbt Core is the transform plane; v2 with its built-in DuckDB adapter (Amendment X) | adopted |
| [D-05](#d-05) | Version pins; dbt Core v2 adopted (Amendment X), the driver registered, dbt_utils vendored | adopted |
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
| [D-20](#d-20) | Gate-two invocation (run, then test; Amendment Y) and CI profile resolution | adopted |
| [D-21](#d-21) | Proposer invocation architecture | adopted |
| [D-22](#d-22) | Prompt governance and lineage | adopted |
| [D-23](#d-23) | Context discipline: grounding without retrieval | adopted |
| [D-24](#d-24) | Agent UX: propose, review, approve on existing surfaces | adopted |
| [D-25](#d-25) | Evaluation: the golden-profile set | adopted |
| [D-26](#d-26) | Repository public before Phase 5 | adopted |
| [D-27](#d-27) | Bronze lands in CI via make ingest | adopted |
| [D-28](#d-28) | Contract-declared enforcement severity | adopted |
| [D-29](#d-29) | The auto-modeling engine specification | adopted |
| [D-30](#d-30) | Registry population: compiled-context artifact, literal-carrying model; the governed documents harvest (Amendment AA) | adopted |
| [D-31](#d-31) | Serving layer: one shared query module; thin MCP server; served sources (Amendment AA); tool annotations and the gold scope (Amendment AB) | adopted |
| [D-32](#d-32) | MCP SDK: official mcp as a project dependency | adopted |
| [D-33](#d-33) | Demo export: content equality by query, never bytes | adopted |
| [D-34](#d-34) | Proposer model selection: pinned default, allow-listed override | adopted |
| [D-35](#d-35) | Proposer stances and the adoption scan; the scan reports document states (Amendment Z) and meaning states (Amendment AC) | adopted |
| [D-36](#d-36) | The typed surface: a materialized mart by default | adopted |
| [D-37](#d-37) | Local enforcement hooks in the SDLC layer | adopted |
| [D-38](#d-38) | Incremental materialization behind engine.materialization | adopted |
| [D-39](#d-39) | Batch-scoped gates; make audit-gold full-table audit | adopted |
| [D-40](#d-40) | docs/scale.md and the measurement rule | adopted |
| [D-41](#d-41) | The multi-source proof and the star trial | adopted |
| [D-42](#d-42) | Supported platforms: macOS, Linux, Windows x64; the task entry point | adopted |
| [D-43](#d-43) | Governed documents: the register, the binding, the derived state | adopted |
| [D-44](#d-44) | Governed meaning: the glossary and ontology registers, the binding, the change-set command | adopted |

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
the pinned 1.4.3 every two-part `gold.<x>` reference, SELECT and CREATE
alike, fails as ambiguous
([F-25](../verification/gate_proof_findings.md#f-25)). Path only: the
export mechanism, the D-33 content-equality claim, the gitignore
exception, and the D-31 keyless default all follow the new path;
everything else in this decision stands.
Amended September 2, 2026 (Record 011, Amendment S): the demo artifact
leaves git. `demo/demo.duckdb` is a release asset attached to each
tagged release and gitignored; the committed artifact is its digest
manifest, `demo/demo.digest.json` (the artifact's name, release,
sha256, and byte count, plus the content manifest: per-table row
counts and the D-33 ordered digest per typed view). `make demo-fetch`
restores the instant serve path from the release the manifest names;
`make demo` builds the same content keyless from the committed
samples; CI proves the built warehouse against the manifest; doctor
reports an absent artifact as a hint, never a failure. Measured at
the Arc 6 prep ([F-44](../verification/gate_proof_findings.md#f-44)):
three categories make the artifact 106 MB, and every refresh would
add its gzipped size to every clone forever. The working-warehouse
clause, the raw-data clause, and the D-31 keyless default stand.

### D-04
**Transform execution plane.** dbt Core v1 with the dbt-duckdb adapter
executes all contracted transforms as SQL dbt models with
`contract: enforced: true`. The profiler stays standalone deterministic
Python, outside dbt, because its output is a reviewable artifact, not a table.
Three planes organize the repo: `contracts/` (specification), `transform/`
(execution), `src/` (hand-written code).
Amended October 3, 2026 (Record 013, Amendment X, jointly with D-05): the
plane is dbt Core v2, the Rust engine distributed as `dbt-oss` 2.0.x,
whose DuckDB adapter is built in and reaches the warehouse through the
ADBC driver the project registers (D-05 as amended). The substance is
unchanged: contracted transforms are SQL dbt models with
`contract: enforced: true`, the profiler stays outside dbt, and the
three planes stand.

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
Amended October 3, 2026 (Record 013, Amendment X, jointly with D-04): the
dbt line moves to dbt Core v2. `dbt-oss>=2.0,<2.1` (resolved 2.0.5)
replaces `dbt-core>=1.12,<1.13` and `dbt-duckdb>=1.11,<1.12`; the Python
adapter retires with its line; transform/dbt_project.yml mirrors the
range as require-dbt-version [">=2.0.0", "<2.1.0"], a declaration
dbt-oss 2.0.5 reads and does not enforce
([F-66](../verification/gate_proof_findings.md#f-66)), so the pin is
held by uv.lock and `make doctor`. The deferral lifts on the condition
this decision set: 2.0.0 went GA on September 14, 2026, and the move
was proven before it bound: at 2.0.5 the full gate set lands every
lane, gate, the adoption scan, and the D-33 digest at their head values;
the warehouse the engine writes carries storage version 64 and the
library version v1.4.3, the numbers the published asset carries; and
datacontract-cli 1.0.12 (D-06, confirmed below) syncs `updated 0` and
tests clean against it (F-66). Four things the line brings are named
here because rule 1 pins by the lock. The distribution: `dbt-oss` on
PyPI is a 5 KB source distribution whose build step downloads the engine
wheel for the machine's platform (63 to 76 MB, carrying a 172 to 321 MB
engine, by platform; F-66 has the figures) from GitHub releases and
verifies it against the sha256 manifest the sdist embeds, so uv.lock
pins the sdist by hash and the wheel is pinned by that manifest; the
download runs through the project interpreter's own TLS trust (the F-58
class; the demo guide's entry), and wheels exist for macOS x86_64 and
arm64, Linux manylinux 2.28 x86_64 and aarch64, and Windows x64 only.
The driver: v2 reaches DuckDB through an ADBC driver and its pip
distribution ships none; with nothing registered it looks for a driver
on the machine and then downloads one from the dbt Labs CDN, whose
DuckDB version this project does not pin. The project registers its
own: the extension module inside the pinned Python `duckdb` wheel
exports the ADBC entrypoint `duckdb_adbc_init`, and `uv run mm driver`
writes an ADBC driver manifest naming it under the repository-local
`.adbc/` (gitignored, an absolute path, written per clone), which every
dbt line reaches through `ADBC_DRIVER_PATH` (the Makefile exports it,
`mm` passes it to its dbt steps, the contract-gate workflow sets it on
its job, the Windows legs reach it through `uv run mm demo`, and `make
doctor` prints it beside the two F-09 exports). dbt therefore writes
the warehouse with the exact engine the serving layer, the ingest, and
the profiler open it with; the storage version is the Python pin's by
construction; no CDN is reached. The package: v2 resolves packages.yml
against the package hub on every parse and build, not only on `dbt
deps`, so a network that cannot reach hub.getdbt.com could not parse
the project; dbt-labs/dbt_utils 1.3.3 is therefore vendored at
transform/vendor/dbt_utils (the files dbt reads, dbt_project.yml and
macros/, from the tag ef562bac, unmodified apart from one file's CRLF
line endings normalized to LF by the repository's line-ending rule,
with its Apache-2.0 LICENSE beside them and a NOTICE paragraph),
packages.yml names it as a
local package, the committed package-lock.yml carries v2's form, and the
hub is never reached: the hermetic path D-27 chose for bronze, applied
to the package. What v2 refuses: the one column-level `meta` key that
datacontract-cli 1.0.12 wrote
([F-27](../verification/gate_proof_findings.md#f-27)) is refused at
parse and moves under `config`, where the pinned sync leaves it; the
sync-generated singular tests of the level-zero silver tables carry no
dependency edge
([F-51](../verification/gate_proof_findings.md#f-51)) and v2 schedules
them before their models on a cold build, which Amendment Y to D-20
answers at the gate. The lock drops 26 packages with the 1.12 line
(dbt-core, dbt-duckdb, dbt-core-experimental-parser, metricflow, and
their dependencies) and adds one. dbt-core 1.12.5, the newest 1.x, was
measured as a clean within-pin patch on October 2 and is moot under this
amendment; the 1.12 line stays the recorded fallback, reachable by a
further amendment. Rule 2's parse-only probe retires with the 1.12
line; F-30 and F-31 stand as the record of that line.

### D-06
**Contract standard and tooling.** Contracts are authored natively in ODCS
v3.1.0. datacontract-cli, pinned at 1.0.12, is installed as an isolated uv
tool with the `[duckdb]` extra and is never a `pyproject.toml` dependency.
Confirmed under dbt Core v2, October 3, 2026 (Record 013): nothing in this
decision changes. The pinned tool reads the project through the
`manifest.json` v2 still writes and shells out to the project's `dbt`
for its test run
([F-04](../verification/gate_proof_findings.md#f-04),
[F-09](../verification/gate_proof_findings.md#f-09)), so it needs
nothing from the move: `dbt sync` prints `updated 0 YAML files` on all
13 contracts and `dbt test` prints `Tested 13 contract(s): 3 no tests ·
10 passed.` against a v2-built warehouse
([F-66](../verification/gate_proof_findings.md#f-66)). The 1.2.x line
(1.2.2 at this date) lints and tests clean too, but its sync rewrites
all 117 committed singular tests and the one properties key, so a move
there is its own amendment with the generated tests re-committed; it
is not taken. The ODCS v3.2.0 additions (a `context` block,
`synonyms`, new link types) stay unread by the pinned linter; adopting
them is a separate D-05 and D-06 matter.

### D-07
**The engine emits models.** The auto-modeling engine is a contract-driven
dbt model generator: mapping contract in, gold model files out. It never
executes DDL. dbt build materializes gold as `table`, with a documented path
to `incremental`. `materialized_view` is never used (not implemented by
dbt-duckdb; not the portable choice).
Amended at Record 008 part two (Amendment O): the documented path is
built. [D-38](#d-38) governs the incremental mode behind
`engine.materialization`; `table` stays the committed default and
every other clause stands, the never-DDL clause above all.

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
**CI gates.** Every pull request runs the three-gate contract workflow:
gate one `datacontract lint`, run once per contract (the lint command takes a
single location, not a glob); gate two `dbt build` (compile-time shape
enforcement), exact invocation per D-20; gate three per D-16, alongside ruff
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
Amended September 2, 2026 (Record 011, Amendment T): committed samples,
plural. Every source in scope is a public dataset cited in its own
README under `data/samples/<source>/`, licensed for redistribution,
fetched by a committed script pinned to a publisher artifact that
does not move (a repository commit, a published month), with the raw
download gitignored. The script records the raw download's sha256
and refuses to extract from bytes that differ from it, printing the
revision instead: a rerun is byte-identical while the publisher
artifact is unchanged, and a publisher revision is a loud finding,
never a silent re-extract. Budgets: 20 MB for the one event source,
10 MB for every other source, 40 MB for an arc, measured at the
fetch and enforced in the script. The retail sample, the Kaggle
clause, and `source-faker` stand as written.

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
Every review obligation in the clause (sync output as proposal, export
as scaffold only, the duplicateValues deletion rule) stands unchanged on
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
Amended at Record 008 part two (Amendment P): the table-materialization
clause reads, from here, as the committed default rather than the only
mode. [D-38](#d-38) adds `incremental` behind `engine.materialization`
(contract enforcement permits table or incremental, as this decision
has always noted). Every other clause stands.
Amended September 2, 2026 (Record 011, Amendment R): the conformed
calendar. The timeframe group's payload is `{grain, period_start}`
under one fixed manifest for the whole star, `period_start` the
category's declared time column truncated to its declared grain and
rendered canonically, so equal periods at equal grain hash to one row
whichever category minted them. Before this amendment the payload
key was the category's own time column name, and two categories at
the same grain minted different rows for the same day
([F-43](../verification/gate_proof_findings.md#f-43)). The typed
surfaces extract `period_start` into each category's time column.
One regeneration of the existing category carries the change. Every
other clause stands.

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
project splits the guard to per-gate granularity: gate one activates on a
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
Amended October 3, 2026 (Record 013, Amendment Y): gate two is
`uv run dbt run --project-dir transform --target local` followed by
`uv run dbt test --project-dir transform --target local`, in place of
`dbt build`. The singular tests `datacontract dbt sync` generates from
the level-zero silver contracts name their table by schema and carry no
dependency edge
([F-51](../verification/gate_proof_findings.md#f-51)), and dbt Core v2
schedules an edge-less test at once, before the models, so a cold `dbt
build` fails on them (20 to 24 catalog errors per build, the count a
race; [F-66](../verification/gate_proof_findings.md#f-66)). Running the
models first and the tests second keeps every model, every test, and
every red verdict; what changes is that a failing test no longer skips
the models downstream of it inside one command, which no gate relied
on. `make demo` (`uv run mm demo`) runs the same two steps; `make
audit-gold` keeps its test selection. The alternative, measured and not taken: the
seven level-zero silver contracts naming their tables through
`{{ ref() }}` in their quality rules, the F-51 remedy generalized. It
cold-builds clean under v2 and costs seven contract bumps, 34 generated
tests re-versioned, a compiled-context mint, and a regeneration that
fails the D-33 gate until a release carries it; the project's own
amendment classifier reads each rewritten rule as a modified rule, which
narrows by the conservative reading of D-35, although the committed
rule signatures are unchanged. That route stays open by a later
amendment that classifies a reference rewrite as neutral; it is
recorded here, not taken. The CI mechanization and the profile
resolution of Amendment B stand.

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
([`docs/spec/engine/mapping-contract.schema.json`](../spec/engine/mapping-contract.schema.json),
the same JSON Schema the Phase 6 gold mapping proposer emits structured
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
Amended September 2, 2026 (Record 011, Amendment U): the multi-source
fan-in. `engine.mapping_contracts` is a list, one mapping contract
per fact category; the engine emits every category's set and one
star-global set over all of them, in category-name order, and the
shared groups union every category. Each mapping's silver contract
resolves by convention from its `sourceTable` (`silver.<table>` reads
`contracts/<table>.odcs.yaml`). Star-level cross-checks, fail-closed:
unique category names, unique source tables, and `captured_at` on
every mapped silver table. The star-global objects carry a header
naming the star contract and every mapping; the ownership manifest
names every mapping. Engine 0.5.0. Every other clause stands.

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
Amended September 2, 2026 (Record 011, Amendment V): compiled schema
2.0.0. The artifact carries one dimensions entry and one measures
entry per mapping contract, each citing its mapping, and one entry
per shared group, each citing the star contract, because no single
mapping owns a shared schema key. Category entries carry the category
name, its declared time column and grain, its typed surface, and its
conformed keys (`conformed_keys`: the mapped columns that join across
categories and the declared key each carries, harvested from the
silver contract's `conformedKeys`); `sources` lists the star contract
and every mapping and silver contract. The freshness check compares
every governing contract by id and version, so a bump to any of them
keeps the artifact ahead of the emission. Every other clause stands.
Amended September 3, 2026 (Record 011, Amendment W, jointly with D-31):
every registry entry keeps two things apart by name. `data` is what the
columns are, derived from the contracts' typed declarations (per field
the logical type, physical type, mapping role, and required flag, never
a description; for a dimensions entry also the grain, the derived
identifiers, the conformed keys with the star's normalization rule and
`shared_with`, the other categories carrying the same key; the source
table, time column and grain, the typed surface, the served value form,
and where to query). `expert_context` is what people wrote, carried
from the governing contracts unchanged and opened by a note that names
it authored knowledge, never a measurement: the silver contract's
purpose, usage, and limitations; the mapping's purpose, usage, and
limitations; the governing contract citations for all three planes;
`sourceLineage` and `vintage`; the unified tables' structured `joins`
with measured completeness and floor; the star's `crossCategoryJoins`
the category takes part in; the `decisions` of both contracts; and per
field a `meaning` plus a `source_meaning` where the silver column's own
description differs. The shared groups carry the same two sections
framed by the star contract. `role` and `manifest` stay at the top
level where `get_schema` reads them. Compiled schema stays 2.0.0: the
split adds keys under it and removes none the serving layer read.
Amended October 19, 2026 (Record 015, Amendment AA, jointly with D-31):
compiled schema 2.1.0. The compiler harvests the governed documents
register (D-43) at compile time and the artifact carries each certified
binding: per bound field, under `expert_context.fields`, a `sources`
list (the anchor a person bound, verbatim, its locator, and the
document's id); per entry whose fields cite at least one document, a
`documents` block at the top of the compiled context, beside `data` and
`expert_context` (a `note` that labels it, and `cited`, each document
once by id, with its title and its `declared` fields apart from its
`measured` fields). The block sits outside `expert_context` because
Amendment W keeps a measurement out of it, and `role` and `manifest`
stay where `get_schema` reads them. The harvest is deterministic code
inside the compiler
(`src/metricmine/context/harvest.py`): it reads committed files only,
the register under its contract and, for an `in_repo` row, the
committed copy; never `MM_DOCS_ROOT`, never a `public` or
`pointer_only` location, and never a calendar, so the artifact stays
identical on every machine. What is served: never a row whose
certification source is `none`; an `in_repo` row while its committed
copy reads `in_sync` or `changed_anchors_intact` at compile time, with
that state and the digest the compiler read beside the digest the
register records (a merged tree holds both to `in_sync` and equality
through the unit lane); a `public`, `local_path`, or `pointer_only` row
as declared, with what a person's verify run recorded as measured and
`checked_at_compile` false; a location only where the consumer's own
host could open it (`location`, `upstream_url`, and `durable_id` where
the register declares them, for `in_repo` and `public` rows: the
committed copy's path and its commit-pinned upstream URL, or the public
URL; none of the three for `local_path` or `pointer_only`); and never a
document's text beyond the bound quote. `make context` prints each row or binding it leaves out
with the reason; a register that fails its contract's error rules fails
the compile closed. The served fields are the mapped silver contracts'
columns: a binding on a column a mapped contract restates in prose (the
F-62 edge) is reported, never followed, so the mapped column is bound
in its own right. The freshness check compares, beside every governing
contract, the register's digest (sha256 over its canonical rows) and
each served document's text digest, carried under
`sources.documents_register`, so a binding change or a committed
copy's change reads as stale until `make context` runs, with no
contract version moving; an artifact minted before this amendment
cites no register and reads as stale on a tree that carries one. The
budget: the harvest one registry entry carries (its `documents` block
plus every field's `sources` list, as compact JSON) is held to 4,000
characters; a harvest over it fails the compile closed and names the
entry, and the number moves only by amendment. Measured October 19,
2026, at `d53132a` with the demo's binding: the flights measures entry
grew from 9,369 to 11,116 characters of compact JSON, the harvest
1,723 of them (the `documents` block 1,549: the note 751, the cited
document 780, the block's keys the rest; the field's `sources` list
174), so the budget holds the note, one document, and fourteen sources
of the demo's size (3,985), or three documents and five (3,977), the
ten-binding case S37 estimated, about a thousand tokens at four
characters a token and under a quarter of the largest entry (16,156).
The minor bump: keys are added (`sources` per bound field, `documents`
per entry, `documents_register` under `sources`) and none the serving
layer reads is removed (Amendment W's rule). Every other clause stands.

### D-31
**Serving layer: one shared query module; thin MCP server.** All gold
access flows through `src/metricmine/query.py`, implementing the D-17
serving clause in the D-11 read-only posture. The MCP server at
`src/metricmine/server/` is a thin stdio adapter over the module: the
five spec tools and nothing else. Read-only is enforced three layers
deep (`read_only=True` connections, `enable_external_access=false` with
`lock_configuration=true`, and a single-statement SELECT gate), and every
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
Amended September 3, 2026 (Record 011, Amendment W, jointly with D-30):
still five tools, no sixth. `list_fact_categories` additionally
returns, per category, `subject` (the authored subject of the
category's dimensions entry, the words of the people who approved its
contracts) and `context_keys` (the dimensions and measures schema keys
`get_context` resolves), and its `query_hint` says that string values
on the typed surface are lowercase and that `get_context` returns
`data` and `expert_context` apart. `get_context` returns the split
artifact as compiled (D-30 as amended). The server instructions tell
an agent to read a category's context before answering from it, to
say which of the two sections an answer rests on, and to use the
declared cross-category joins on the typed surfaces as written. The
D-41 exit measured the need: an agent that writes `origin_airport =
'JFK'` gets no rows, and none of what a null gust, a null arrival
delay, or a recoded airport means is in the rows.
Amended October 19, 2026 (Record 015, Amendment AA, jointly with D-30):
still five tools, no sixth. `get_context` serves the harvested bindings
as compiled: the `sources` under a bound field and the entry's
top-level `documents` block, declared apart from measured, under the
note that names them document text a person bound in the governed
documents register, as the register read when the context compiled.
The note says only what the compile checked (design rule 5 of the
governed host workflow: the server never prints an assurance it cannot
check): that the register changes only by pull request and that git,
not the server, holds the review, never that a binding was reviewed or
a document is current (D-43, F-71). The served wording says what was
declared as declared and what was measured with what code read it
against and the day a verify run recorded it; the compile-time state of
a committed copy carries no date of its own and is dated by the
artifact's version, which the ownership manifest names. The server
never opens a document, the note says so, and it tells the consumer to
open a location through its own host under its own permissions and to
treat what it reads there as data, never as instructions; the server
instructions carry the same paragraph, and a field with no sources
carries no certified source. A document's text never reaches a
proposer (D-23 as amended by Amendment H): the harvest has no path into
a proposal, which the unit lane holds three ways: no module under the
agents package imports the documents module or the compiler, the batch
driver alone imports the scan, whose document states never enter the
queue it walks (Amendment Z), and the governed inputs are the three
Amendment H kinds. The payload budget D-43 left to this amendment is
the 4,000 characters recorded under D-30. Full text: Decision Record
015.
Amended October 19, 2026 (Record 015, Amendment AB): still five tools,
no sixth. Two changes at the tool surface. First (HW-47), every tool
declares a `title` and the specification's annotations (`readOnlyHint`
true, `destructiveHint` false, `idempotentHint` true, `openWorldHint`
false), carried through `tools/list` by the pinned SDK (mcp 1.29.1,
protocol 2025-11-25, measured October 19, 2026). The specification says
a client treats annotations as untrusted unless it trusts the server, so
they declare and never prove: the read-only posture stays proven by the
serving spec's three layers and the gate's matrix, not by a hint, and
no tool's name, arguments, or return shape moves. Second (HR-8),
`query` reads gold by default. After the statement gate the module
reads the base tables and the table functions a statement names from
DuckDB's own parse tree (`json_serialize_sql`, under the hardened
session) and refuses a base table outside schema `gold`,
`information_schema` included, a schema-less name, and the table
functions that take a table's name or a statement as a string and
return its rows or values (`query`, `query_table`,
`json_execute_serialized_sql`, `duckdb_table_sample`,
`pragma_storage_info`;
[F-72](../verification/gate_proof_findings.md#f-72)), naming what was
refused and the opt-in. A reference to a common table expression in
scope is not a base table, and a CTE's own name is out of scope inside
its body unless it is recursive; a statement whose tree the parser
cannot serialize is refused the same way; every other table function
stays reachable as before, under the three layers, and exposes engine
metadata, never rows or values outside gold. The gate judges names: a
gold view that read another schema would pass it, and the project's
gold views read gold alone. The opt-in is `MM_SERVE_SCOPE=all` in the
environment the server starts with, for the modeler's read path (S36)
against a working warehouse through `MM_SERVE_DB`: then `query` reaches
every schema in the served file, read-only, and raw rows of every layer
can reach the host's model provider, which the server instructions,
written from the scope the process runs with, and the operating manual
say in plain words. `gold` is the only other value and the default; any
other value fails the server at startup, as a missing database does,
and the opt-in is never set in a shared or hosted configuration. The
exported demo asset holds gold only (serving spec §8), so a stranger's
demo is unchanged. Measured October 19, 2026, on a built working
warehouse at `d53132a`: `select count(*) from silver.silver_nyc_flights`
returned the count 166,158 through the server, and under this
amendment's default it is refused with the table and the opt-in named;
the gold count path is unchanged. Full text: Decision Record 015.

### D-32
**MCP SDK selection and pin.** The official `mcp` package at 2.0.x,
added as a project dependency (`mcp>=2.0,<2.1`, resolved 2.0.0 in
uv.lock): the server imports it, so an isolated tool cannot serve
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
Note, October 2026 (a correction note, not an amendment): `uv.lock` has
resolved mcp 1.29.1 since the in-range refresh of September 2, 2026
(#142), a chore under rule 1 of the same class as the 1.11.14 refresh
D-05 records. The figures above are the resolution at the date
Amendment D bound; nothing in the decision changes.

### D-33
**Demo export: content equality by query, never byte equality.**
`make export-demo` builds `demo/gold.duckdb`, the only committed
database artifact, exactly as D-03 has always said, from the keyless
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
Amended September 2, 2026 (Record 011, Amendment S): the exporter
writes the artifact and its digest manifest, `demo/demo.digest.json`,
and the manifest is what git carries (D-03 as amended). The content
manifest is the D-33 claim made portable: per-table row counts and
one ordered content digest per typed view, computed over the rendered
row text with no per-category ordering key, so the same query proves
a fetched artifact, a fresh export, and a built warehouse against
each other. The view digest is recomputed once at the fan-in, when
the ordering changed. Mechanism and claim otherwise stand.

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
Amended October 17, 2026 (Record 014, Amendment Z): the adoption scan
also reports the state of every governed document the register names
([D-43](#d-43)), derived on every run by the governed documents module,
written to the outbox with the plan, and never stored. The plan carries
a Governed documents section beside the queue: the register's standing
(`conforms`, `nonconforming` with the reason, or `absent`), the state
counts in a fixed order, and one item per document with its next
command. The content states are `in_sync` (the text digest equals the
recorded one and every anchor is present), `changed_anchors_intact` (the
text changed and every bound quote is still present; nobody is asked to
re-read the bindings, and an `in_repo` document's pull request refreshes
its standing row), `anchor_broken` (a bound quote is gone; the item
names the bindings), `unreachable` (the location cannot be opened here:
the root is not mapped, no file is at the path, or the path escapes its
root), `unverified_pointer` (a `public` or `pointer_only` location this
slice never opens, and no reading copy was given), `unsupported_format`,
`refused_package` (the extractor refused the file under a safety limit),
and `no_text_layer`; the flags are `review_overdue`, `pending_changes`
(a Word file holds unaccepted redlines; the flag names the bindings an
acceptance would break), `binding_broken` (a binding names a contract or
column `contracts/` does not carry), and `extractor_changed`. The
September 19 probe's `document_moved` is retired: identity is the
extracted text, so a moved or re-saved file whose words are unchanged
reads `in_sync`. Document items never enter the queue the batch driver
walks, and a document state's next command never routes a document's
text into a proposer (D-23 as amended by Amendment H). The plan's
`scan_schema_version` moves to `1.1.0` for the added `documents` key;
the model keys are unchanged. The scan reports and never judges: the
exit code that blocks a merge lives in the module's `verify` command,
which fails on a register that does not conform, a failing
error-severity rule, a broken anchor on an `in_repo` document, or a
binding to a column no contract carries, and reports everything else, an
overdue review included. The calendar is a parameter: the scan derives
the states for the run's UTC day, the two commands that read a calendar
(`bind` and `verify`) take `--today` and default to the same UTC day,
and every test fixes it.
Amended October 26, 2026 (Record 016, Amendment AC): the adoption scan
also reports the state of every glossary and ontology binding the
meaning registers carry ([D-44](#d-44)), derived on every run by the
governed meaning module, written to the outbox with the plan, and never
stored. The plan carries a Governed meaning section beside the queue and
the Governed documents section: each register's standing (`conforms`,
`nonconforming` with the reason, or `absent`), the state counts in a
fixed order, and one item per binding with its next command. The states
are `in_sync` (the term's or the concept's current digest equals the one
the binding recorded and the element is in a committed contract),
`term_changed` and `concept_changed` (the digest moved under a standing
binding; the item names the binding and the re-bind that clears it),
`term_missing` and `concept_missing` (the binding names a row the
register no longer carries), `term_deprecated` and `concept_deprecated`
(the row's status is `deprecated`, served as declared with its
`superseded_by` when one exists), and `binding_broken` (a binding names
a contract or column `contracts/` does not carry); the flag is
`review_overdue`. Meaning items never enter the queue the batch driver
walks, and a meaning state's next command never routes a term or a
concept into a proposer (D-23 as amended by Amendment H). The plan's
`scan_schema_version` moves to `1.2.0` for the added `meaning` key; the
model keys and the `documents` key are unchanged. The scan reports and
never judges: the gate of record is the unit lane's test that every
committed register conforms and every committed binding reads
`in_sync`, and the module's `verify` command is the person's local form
of it, failing on a register that does not conform, a failing
error-severity rule, a `term_changed`, `concept_changed`,
`term_missing`, or `concept_missing` binding, or a `binding_broken`
one, and reporting everything else, a deprecation and an overdue review
included. The calendar is a parameter: the scan derives the states for
the run's UTC day, the commands that read a calendar (`propose` and
`verify`) take `--today` and default to the same UTC day, and every
test fixes it.

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
Amended at Record 008 part two (Amendment Q): the lean shape carries
one further column, `captured_at`, the D-38 incremental watermark
carried from the fact, and the mart's config line follows
`engine.materialization` like every emitted model. Every other
clause stands, the uncontracted derivative posture above all.

### D-37
**Local enforcement hooks in the SDLC layer.** A CLAUDE.md rule that a
script can decide from the tool call alone may be enforced by a Claude
Code hook: deterministic code committed at `.claude/settings.json` with
its script under `.claude/hooks/`, applying to every session that trusts
the repository and to headless runs, so a clone inherits the guard. A
hook only denies or asks; it never allows a call past a permission rule,
never weakens a gate, and never moves a check out of CI, which stays the
gate of record. Each hook enforces exactly one rule, and that rule keeps
its CLAUDE.md line naming the hook, because a hook reads the tool input
and nothing a subprocess does. Hooks run no model and are not agents;
the D-10 count is unchanged. The first hook is the working-tree guard,
enforcing the Conventions rule against reading or writing outside the
repository, adopted on the Arc 1 finding that a prose rule alone did not
keep an agent inside the tree
([F-32](../verification/gate_proof_findings.md#f-32)). Every further
rule migrates one at a time by amendment here, with its issue #53 bucket
recorded. Machine-specific overrides live in the gitignored
`.claude/settings.local.json`; `disableAllHooks` is a per-session
opt-out and is never committed. Full text: Decision Record 010.

### D-38
**Materialization for engine-emitted models: incremental behind
configuration.** Every engine-emitted model carries an explicit
materialization config line governed by `engine.materialization`:
`table`, the committed default and the keyless demo path, or
`incremental` for deployments that load continuously. An unrecognized
value fails closed before anything emits. The emitted SQL is one shape
in both modes: the `is_incremental()` blocks ride every model and are
inert under `table`, so a regeneration that flips modes diffs exactly
one config line per model plus the manifest (measured at this prep).
Under `incremental`, contracted models additionally set
`on_schema_change: 'fail'`, which dbt 1.12 requires on contracted
incremental models and which is the contract-first posture: a shape
change arrives through a contract amendment and a regeneration (D-08,
D-09), never silently at build time. The batch mechanics, measured in
the August 23 pressure test and re-proven end to end at this prep:
silver carries `captured_at`, the bronze capture timestamp
(`_airbyte_extracted_at`) carried forward, additive and optional-first
under the F-28 rule with the declared follow-up tightening to required
once the path is proven populated; the fact, the category values
dimension, and the timeframe values dimension carry `captured_at` as a
plain audit-class column outside every hashed payload (rule 13
unchanged), first-seen (minimum) per distinct payload on the
dimensions and per row on the fact, so full-rebuild and incremental
converge to the same stored value; each silver-derived model filters
its source to `captured_at >=` its own stored high-water mark and
every insert passes an anti-join on its content key (the fact on the
full composite), so the `>=` boundary re-scan is idempotent by content
addressing; the constant source and run groups, the columns dimensions,
and the registry insert-if-absent by anti-join alone. The mart appends
fact rows strictly above its own watermark; an interrupted run between
the fact and the mart is repaired by a full rebuild, which the demo
path exercises on every run. Silver's own incremental variant is a
documented adopter pattern in `docs/scale.md`, not a committed mode:
silver is the human-owned plane by design. Engine version 0.4.0.
Full text: Decision Record 008 part two.

### D-39
**Batch-scoped gates with the full-table audit.** The twelve expensive
gold rules (content-key uniqueness on the two silver-derived
dimensions, fact grain enforcement, the five C2 anti-joins, C4 on the
three `captured_at` objects, and C5) carry a guard in their contract
SQL: when a run passes the dbt var `mm_batch_floor`, each scopes to
rows with `captured_at >=` that floor; with the var unset, every rule
runs in its full-table form, byte-identical in effect to the unguarded
rules. CI and the `table` default never pass the var, so the gates of
record are unchanged; an incremental deployment passes its batch floor
so the per-batch cost tracks the batch, not the table (measured August
23: 0.8 s against 17 to 18 s per check at 21 million rows); and
`make audit-gold` runs every contract-generated gold test in the
unscoped form on demand, so the full-table guarantee stays one command
away. Cross-batch uniqueness is guaranteed by the D-38 anti-join
inserts; the scoped uniqueness rules catch in-batch duplication, and
the audit target proves the global property whenever asked. The
mechanism was probed before this decision bound: `datacontract dbt
sync` at 1.0.12 carries jinja var guards in quality-rule SQL verbatim
into the generated singular tests, and dbt compiles both branches
(F-35). Symmetric gates stay symmetric (D-08): nothing narrows with
the var unset, and the scoped form exists only where the anti-join
mechanics carry the global guarantee. Rules that stay cheap at scale
(C1's two counts, the rowCount library rules, the constant-dimension
checks) never scope. Full text: Decision Record 008 part two.

### D-40
**`docs/scale.md` and the measurement rule.** The scale posture is
documented in one place, `docs/scale.md`: what scales by design and
why (the build linear in rows; the mart answering questions 100 to
2,000 times faster than the view; a 1 percent batch in seconds against
minutes of rebuild), the measured curve with its environment stated,
the disk and memory guidance (roughly 3.5 times bronze bytes plus
spill; a 2 GB DuckDB memory cap completes; rebuild into a fresh file
after a failed run), the dbt-duckdb profile gotcha (`temp_directory`
in profile settings fails after the first spill; leave the default
spill location), and the incremental and audit recipes (D-38, D-39).
The standing rule this decision mints: a performance number is
published only with its environment stated, never as a promise, and
never on the website; throughput claims and SLAs remain non-goals.
The August 23 sandbox curve (45 thousand to 21 million rows, 2 CPUs,
7 GB) is the founding measurement; the Mac re-measure at 1 and 10
million rows lands in the same file with its own environment line at
the Arc 5b sitting. Full text: Decision Record 008 part two.

### D-41
**The multi-source proof and the star trial.** Arc 6 lands seven public
extracts under contracts: the retail sample already committed plus the
aviation family, six files from two publishers (the nycflights13
package at commit `df98ef21`, CC0: flights, hourly weather, carriers,
and aircraft for New York City's three airports in January through June
2013; OurAirports at commit `d27027ba`, public domain: airports and
runways), each cited in its README, licensed for redistribution, and
fetched by a deterministic script pinned to a publisher artifact with
its digest (D-15 as amended by Amendment T; `docs/sources.md` is the
register of them). Bronze lands every source through one PyAirbyte
connector type, many files. Silver stays the human-owned plane: one
cleanup contract per source, hand-authored from the profile it cites
(rule 16), with the cleanup proposer's draft over the same profile
recorded as an eval-lane agreement study against that contract (D-25),
never as the file; conformance settled in silver, in human-owned SQL,
as unified tables (`silver_flights`, `silver_airport_weather`) whose
contracts are hand-authored from the tables' own profiles, each join
declared as structured `joins` with the completeness measured at the
profile and the floor an error-severity rule enforces; conformed keys
declared at the contract plane (`conformedKeys` on each silver contract
that carries one, `conformedKeyRules` on the star contract with the
key's physical type and normalization rule), enforced by an
error-severity normalization rule in each carrying contract and by the
K1 gate (`tests/test_conformed_keys.py`: every declared key typed
identically wherever it appears, guarded by its rule, and carried by at
least two contracts), and surfaced per category in the context registry
(`conformed_keys` with `shared_with`, D-30 as amended by Amendments V
and W). Gold is one star over every category (D-29 as amended by
Amendment U) under one registry and one conformed calendar (D-17 as
amended by Amendment R); three categories at the exit (`invoice_lines`,
`flights`, `airport_weather`). The star contract declares the
cross-category joins the typed surfaces support (`crossCategoryJoins`:
the two categories, the condition aliased by category name, the
conformed keys and calendar grain it rides on, the completeness
measured through the typed surfaces, the floor, a note, a worked
example), and the declared-join gate (`tests/test_declared_joins.py`)
re-measures every silver join by its definition and every
cross-category join through the typed surfaces and through silver,
failing by name when a declaration drifts. The claim: co-location in
gold, conformance in silver, service through the typed surfaces. The
star carries no shared business-entity dimension and a mapping
contract's `entityGroup` stays a registry label.

The trial, written here before the first source landed. The star earns
its place if, at the arc's exit, (M1) every category builds in one `dbt
build` from an empty warehouse with C1 to C5 at error severity, `make
audit-gold` passes full-table, and `make demo` runs keyless with the
demo gate green; (M2) the K1 gate holds, every declared silver join
meets the completeness floor its unified contract declares at error
severity, and every declared cross-category join meets its floor
through the typed surfaces; and (M3) the recorded cross-source
questions (`tests/fixtures/serving_questions.json`, proven through the
serving path by `tests/test_serving_questions.py`) each answer through
the typed surfaces with one `query` statement joining on conformed keys
the registry names, with `list_fact_categories` and `get_context` as
the only guide; all of it with no gold object beyond the engine's
emission and no engine change beyond the fan-in and the conformed
calendar this record mints. The star fails the trial if a question
needs a hand-written gold object, or a conformed entity cannot be
joined across categories through the typed surfaces.

Verdict, recorded at the arc's exit: the trial passes, on numbers
measured at the September 3, 2026 rehearsal and held by the sittings'
own gates before this paragraph landed. M1: 31 models and 303 tests
green in one cold build (PASS=334), the audit and the demo gate green.
M2: the K1 gate holds three keys; the five declared silver joins measure
1.0000, 0.8396, 1.0000, 0.9791, and 1.0000 against floors 1.00, 0.80,
1.00, 0.97, and 1.00; the declared cross-category join (a flight's
weather at its origin in its departure hour) measures 0.9994 through the
typed surfaces and through silver alike against a floor of 0.99, and
every one of the 3,439 departure hours is a calendar row the weather
category minted too. M3: seven questions answer on the typed surfaces
as documented: three join flights to weather across categories on the
conformed airport code and the calendar hour, three more lean on joins
settled in silver (the carrier, the aircraft registry, the airport
reference), and one is the retail control. The measured cost of
per-category dimensions
([F-44](../verification/gate_proof_findings.md#f-44)): the flights
category's values dimension is 59 MB of a 106 MB artifact, the price of
a wide payload chosen so the whole unified row reaches the typed
surface; the register records it as the price of the shape. The standing
non-goal on source types reads, from this decision, as one ingestion
connector type with many files of that type in scope. The release after
the arc is 1.1.0: additive contract semantics, the fact primary key
unchanged. Budgets, windows, and the ladder: Decision Record 011.

### D-42
**Supported platforms and the task entry point.** The supported matrix
is macOS, Linux, and Windows x64 on Python 3.12 (`.python-version`).
Every platform in it is first-class under the stability rule (CLAUDE.md
rule 19): a clone of `main` at any tag gets a working demo there,
keyless. CI proves the demo path on a clean ubuntu checkout
(`contract-gate`) and, from Arc 7, on a fresh Windows runner per change
to the demo path (`demo-windows`: `windows-latest`, a matrix over
PowerShell 7 and Windows PowerShell 5.1, Path A then Path B, the
manifest gate, the test suite; free on the public repository; each run a
fresh virtual machine). `make` is a convenience layer: the demo-path
targets (`doctor`, `demo-fetch`, `ingest`, `demo`, `export-demo`,
`demo-manifest`) are one-line delegations to the task entry point `uv
run mm <target>` (`src/metricmine/tasks.py`, declared under
`[project.scripts]` and installed by `uv sync` into the project venv),
so `make demo` on a Mac and `uv run mm demo` on Windows run the same
code and cannot diverge; a change to a demo-path target lands in the
module, never as a Makefile-only recipe; `tests/test_tasks.py` holds the
module to the keyless rule (D-24) and the dbt invocation convention
(D-11, D-20). Every hint the demo path prints (the preflight, the fetch,
the digest check, the exporter, the serving module's fail-closed
message) names its remedy in the running platform's form through one
helper in that module, so no Windows reader is told to run `make`. Every
other `make` target is the one-line `uv run ...` command the Makefile
shows, and a Windows shell runs that line; widening the entry point is a
later touch on a Windows contributor's report. Windows text on every
public surface runs in Windows PowerShell 5.1 and PowerShell 7 alike:
one command per line and no `&&`, `$env:NAME = "value"` for environment
lines, `.venv\Scripts\python.exe` as the interpreter, backslashes
doubled in JSON, Command Prompt not a target; the runner matrix proves
both shells, and the uv installer line is quoted from Astral's
documentation. Line endings: `.gitattributes` holds every text file to
LF on checkout (`* text=auto eol=lf`) whatever `core.autocrlf` says, so
the bytes a Windows clone hashes (the contracts' canonical hash, the
committed samples' digests, the engine's oracle) are the bytes the Mac
and CI hash; `docs/verification/evidence/**` and `data/samples/**` are
`-text` and keep their bytes verbatim, and no renormalization commit was
needed (measured at `cb2cd07`: 606 tracked text files already LF; a
`core.autocrlf=true` clone fails eight unit tests without the file and
none with it). Outside the matrix, with the reason: Windows on Arm (the
locked `dbt-core-experimental-parser` sdist offers no Windows Arm wheel;
`make doctor` says so and WSL runs the Linux path) and WSL itself (it is
the Linux path, already proven on ubuntu). The Claude Desktop step on
Windows ships documented from the MCP client guide
(`%APPDATA%\Claude\claude_desktop_config.json`, opened from Settings,
Developer, Edit Config; the Store build's virtualized copy is noted
while anthropics/claude-code#26073 stays open). The command that entry
launches is proven over stdio on the runner (`scripts/serve_smoke.py`:
the venv interpreter, `-m metricmine.server`, from outside the
repository with a minimal environment); the click-through itself is
documented, not measured, until a person confirms it on a Windows
desktop; F-55 records that gap and closes when the confirmation lands.
The working-tree guard (D-37) stays POSIX-only and fails safe on Windows
by asking; a Windows guard is a contributor item, not a demo-path item.
`datacontract-cli` on Windows is not part of the demo path (the gates
are CI's), and a `uv run pytest -q` without the tool skips the lint
tests by name instead of failing them (F-54). No pin moves. The release
that closes the arc is 1.1.1: the versioning rule of the operator's
manual follows the contracts, and no contract, model, or demo content
changes. Adopted September 6, 2026 (Decision Record 012).

### D-43
**Governed documents: the register, the binding, the derived state.** A
document a person has certified as the source of a contracted column's
meaning is governed by one sentence: the contract's sentence is the
certified claim, the document is its cited source, a small register
records the binding between them and says where the document's approval
lives, the scan derives the document's state on every run, and the merge
stays the only approval this project gives. Two clocks, two lanes: the
binding changes as rarely as a schema and travels through git; a
document's versions change on the document's own platform and never
touch git. **The register** is two tables, held to an ordinary ODCS
contract (`contracts/documents_register.odcs.yaml`) with no dbt model,
so the gates that judge every contract judge it, gate three records it
as having no model, and its quality rules execute in the module's
`verify` command and the unit lane at the severity each rule declares
(D-28). `documents_standing` holds one row per document: a stable
`document_id` (never the path), the title, the governance class, the
access class, the location, the platform's durable id beside the display
location, the format, the certification source, the gate's strength, for
`platform_governed` the role whose approval publishes the location
(`approver_role`), for `pinned` the platform's label of the certified
version (`pinned_version`) beside the text digest, who declared the row
and when, a review date, the text digest and the extractor that measured
it, what it was verified against and when, and for a committed copy of a
public document its upstream URL, the upstream bytes' sha256, and the
license. `documents_bindings` holds one row per
bound column: the document, the contract id and column, the anchor (a
verbatim quote from the extraction, validated at bind time and on every
scan), a locator for people, the person's intent verbatim with its
sha256 (the Amendment I pattern), and who bound it and when. **The
classes.** Governance is `in_repo` (the merge certifies the binding; the
document changes under the repository's own review), `platform_governed`
(the merge certifies the binding and the arrangement: the location
publishes only through an approval given by a named role), or `pinned`
(the merge certifies the binding and one version; a change asks for a
new pin unless every anchor is intact). Access is independent: `in_repo`
(code reads it, everywhere, CI included), `public`, `local_path` (a path
under the root a person maps through `MM_DOCS_ROOT`, stored as
`${MM_DOCS_ROOT}/...`; a machine without the root reads `unreachable`
and blocks nothing, CI included), or `pointer_only` (nothing here ever
opens it). The certification source is a closed field, `git_merge`,
`platform_approval`, `steward_attestation`, or `none`, and the gate's
strength is `publication_gate`, `attestation_badge`, or `none`; both,
like the two classes and `verified_against`, are held closed by the
contract's own `error` rules, which `verify` and the unit lane execute.
This project records where an approval lives and does not have to own
it. A
row with `none` is allowed and reads as declared (S37 question 3b); the
served wording, when it comes, says what is declared as declared and
never that a document is current (Amendment Z; the served list is a
later D-30 and D-31 matter). **Identity is the extracted text, never the
bytes** ([F-69](../verification/gate_proof_findings.md#f-69)): the
digest is over the text after NFKC and whitespace normalization and
nothing else, and the extractor's id and version travel with it, because
extraction is part of the record and an extractor change re-verifies
every anchor. The extractor set and its versions are recorded: this
slice reads `text`, `markdown`, `docx`, and `pptx` on the standard
library, reading every text part the extractor names (a Word file's
body with its tables and text boxes, each header and footer, footnotes,
endnotes; a deck's slides in presentation order with their tables and
grouped shapes, and each slide's notes through the package's
relationships) and never the convenient one; comments, SmartArt, charts,
layouts, and masters are not read, a Word text box's fallback copy is
skipped so it is read once, and a deck's field text (slide numbers,
dates) stays out of the words; PDF, Excel, and RDF each wait on a
dependency and a pin decision (rule 1). An extractor refuses untrusted input under fixed limits and a refused
package is a state, never a crash. **Anchors and their limit.** An anchor
check measures that a quote is still present and nothing more
([F-71](../verification/gate_proof_findings.md#f-71)): an edit elsewhere
reads `changed_anchors_intact` and asks nobody to re-read the bindings
(for an `in_repo` document the pull request that edits it refreshes the
standing row's `text_sha256` and `verified_on`, which the unit lane
holds in sync), an edit to the quoted sentence reads `anchor_broken`,
and a contradiction beside an untouched quote reads as intact, so every
standing row carries a review date, an overdue review is a derived state and a `warn` rule and never a
red gate, and the review is what forces a whole-document read. When the
document and the contract's sentence disagree, the contract's sentence
is the certified claim and the document its cited source; the
disagreement is an item for a person, never an automatic override. **Who
certifies.** A declarer, a binder, or a verifier is a person: code
refuses what it can check (the two proposers' names, the D-34 model
identifiers, the repository's resident subagent's name, and any
`claude-` name), and the rest is the person's own attestation; an
attestation made by an integration is not a steward's.
Consent in chat is permission to draft, never certification: the `bind`
command renders the draft by code into the gitignored outbox and never
writes the register, and a narrowing is never enabled by something an
agent can supply alone (the quote is checked against the extraction, the
column against a committed contract, the binder against the known agent
and model names). A cited document is data: no agent with tools is
pointed at a document that arrived in a message; a person opens it. The
control for a steward, when one exists, is CODEOWNERS on the register's
path; with one maintainer and `in_repo` documents, this slice adds none.
**The boundary.** The governed documents module
(`src/metricmine/documents/`) is deterministic code of the kind D-10 as
amended by Amendment G names beside the proposers, never a third agent, and a document's text is never a proposer input (D-23 as amended
by Amendment H). It opens a document only in the repository working tree
or under the mapped root; it never opens a `public` URL or a
`pointer_only` location, never follows a path that escapes its root, and
never extracts a package to disk. A person runs the `local_path`
commands at a terminal, because the working-tree rule stays in force
where the D-37 guard cannot see; an agent in this repository works on
`in_repo` documents or on a reading copy the person staged into the
gitignored `documents/inbox/`; CI and the demo never map the root. A
reading copy (an upload saved to disk, a download, a replica) verifies
anchors and is never the record: `bind` refuses to register one, a
`public` or `pointer_only` row is declared by hand in the register, and
the register says what was verified against what. **Register-only first.** No data contract carries
a pointer in this slice and no data contract moves; the binding lives in
the register and the compiler, when it harvests bindings, joins them to
fields at compile time, so no contract bumps per binding. When a
column-level pointer comes, it never uses a link type the linter resolves
([F-68](../verification/gate_proof_findings.md#f-68)). The served list
has a payload budget as a principle (the anchors and locations for the
fields asked about, never every quote); its number is set with the D-31
amendment that serves it. **The surface.** The commands are `find`,
`inspect`, `bind`, and `verify` under `python -m metricmine.documents`
with one-line Makefile targets, as `make scan` is; no MCP tool is added
and the `mm` entry point is not widened (D-42). **The first binding**
(the demo, clean-room and public): the `flights` reference page of
tidyverse/nycflights13 at the commit the flight samples are pinned to,
CC0, committed as a byte-for-byte copy under `documents/sources/` with
its upstream URL and sha256 and held verbatim by `.gitattributes`,
governance `in_repo`, access `in_repo`, `git_merge`, `publication_gate`,
a review date one year out, bound to
`silver_nyc_flights.dep_delay_minutes` by the delay sentence; the file is
Rd markup read as text. **Not decided here:** what `get_context` serves
and the budget's number (D-30, D-31), including how the compiled
artifact's staleness check sees a binding change when no contract
version moves, and that a served anchor is document text a person bound
and a merge reviewed; whether ODCS v3.2.0's `context` block changes
where authored meaning lives (D-05, D-06); an upstream contribution;
document change kinds in the context proposal path. Full
text: Decision Record 014.

### D-44
**Governed meaning: the glossary and ontology registers, the binding,
the change-set command.** A business term or a concept a person has
certified as the label of a contracted element is governed by one
sentence: the contract's sentence stays the certified claim, the term or
the concept is its label, a register records each label with a content
digest and records the binding between a label and a contract element,
the scan derives each binding's state on every run, and the merge stays
the only approval this project gives. Meaning is descriptive only: a
term or a concept labels an element and never drives a join, a key, a
type, or a transform, and the shared business-entity dimensions the
[D-41](#d-41) verdict kept out of gold stay out. **The two registers**
take the documents register's shape ([D-43](#d-43)): two ordinary ODCS
contracts with no dbt model, `contracts/glossary_register.odcs.yaml`
(`glossary_terms`, `glossary_bindings`) and
`contracts/ontology_register.odcs.yaml` (`ontology_concepts`,
`ontology_bindings`), their rows as committed YAML under
`meaning/glossary/` and `meaning/ontology/`, held to their contracts by
the module's loader, and their quality rules executed in the module's
`verify` command and the unit lane at the severity each rule declares
(D-28). `glossary_terms` holds one row per term: a stable `term_id`
(lowercase, underscores; never the label), the term as people say it,
the definition in the owner's words, the synonyms (separated by `; `;
a synonym belongs to one term and never equals a term's label), the
owner (a person or a team, never an agent or a model name), the status
(`active` or `deprecated`, a closed field), for a deprecated term the
`superseded_by` id of the term that replaces it when one exists, who
declared the row and when, and a review date. `glossary_bindings` holds
one row per contract element a term labels: the term's id, the contract
id, the column name (the empty string for the table itself), the term's
content digest as the term read when the binding was made, the person's
intent verbatim with its sha256 (the Amendment I pattern), and who bound
it and when. `ontology_concepts` holds one row per concept: a stable
`concept_id`, the label, the parent concept's id or none at a root, the
definition, the owner, the status, `superseded_by`, who declared it and
when, and a review date; `ontology_bindings` holds one row per element a
concept labels, with the concept's digest in place of the term's, and an
element carries one concept: a table's concept is its entity type and a
column's concept is what the column carries. The contracts' `error`
rules hold the closed fields, the unique ids and labels, the synonym
ownership, `superseded_by` (only a deprecated row names one, and it
names a row the register carries), the parent (a concept the register
carries, never the concept itself, and a parent graph with no cycle,
measured by a recursive rule), every binding naming a row the register
carries, and a binding's digest and uniqueness; the review date is a
`warn` rule, never a red gate. **Identity is a stable id and a content
digest.** A term's digest is the sha256 of the canonical bytes of its
`term_id`, `term`, and `definition` after NFKC and whitespace
normalization and nothing else; synonyms are served and never hashed,
so adding or removing one moves no binding. A concept's digest is a node
digest over its `concept_id`, `label`, `parent_id`, and `definition`: a
parent change re-asks the bindings of the concept whose parent moved and
not its descendants' (the ancestor path is not hashed). A re-wrapped or
differently normalized definition keeps its digest; a changed word moves
it. **A register, never a source.** A glossary kept as a spreadsheet is
a table and an ontology is a graph, and both are governed as registers
and never as documents, but neither lands through the ingestion path:
the samples gate asks every landed sample for a publisher's source and
license and a pinned digest, which a steward's own glossary does not
have; a landed table is a profiling target and its samples are a
proposer's input ([D-23](#d-23) as amended by Amendment H), where a
glossary's text is pasted text; and a source moves the configuration,
the profile, a silver contract and model, the landing's counts and
digests, the README, the source and demo pages, the samples gate, the
Windows workflow, and the website's source counts, where a register row
moves none of them (the samples gate's refusal measured and the
surfaces counted by reading, October 26, 2026). A register's rows change by
pull request under the register's digest with no contract version bump
of their own; the register contract's version moves when its schema or
its rules move (D-08 as usual). **The binding lives in the register
first.** No data contract carries a pointer in this slice and no data
contract moves per binding; the compiler, when it harvests bindings,
joins them to fields at compile time. When a column-level pointer comes
it is rendered from the register by its own slice and never uses a link
type the linter resolves
([F-68](../verification/gate_proof_findings.md#f-68)): the pinned linter
accepts `authoritativeDefinitions` entries of type `glossary`, `ontology`,
and a custom type at the table and the column level and `businessName`
at both levels (measured October 26, 2026, twice at 1.0.12 and once at
1.2.8), and it refuses `apiVersion: v3.2.0`, a `context` block under
v3.1.0, and any `relationships` type but `foreignKey`, so the pin holds
(D-05, D-06). A contract pull request that renames a bound element
carries the register's re-pointed rows, because the rows are neither
contract nor transform and the unit lane holds every committed binding
to a column a committed contract carries. **The change set and the
command.** A context proposal is a declared change set: a file in the
gitignored outbox (`proposals/meaning/<name>.changes.yaml`) listing
changes in a closed vocabulary, each with its fields and its rationale,
and two fields the person supplies, `by` (the person's name) and
`intent` (the person's words, verbatim). The vocabulary is, for the
glossary, `add_term`, `amend_definition`, `rename_term`, `add_synonym`,
`remove_synonym`, `deprecate_term`, `drop_term`, `bind`, and `unbind`;
for the ontology, `add_concept`, `amend_concept` (the definition or the
parent), `relabel`, `deprecate_concept`, `drop_concept`, `bind_concept`,
and `unbind_concept`; and for governed documents, `add_document`,
`bind_document`, `unbind_document`, `recertify_document`, and
`retire_document`, which take the same command, record, and pull request
when the slice that serves meaning lands them (until then a document
change beyond `bind` is a hand edit a reviewer reads). The command,
`python -m metricmine.meaning propose <file>` with a one-line Makefile
target, validates by code: every kind is in the vocabulary; every bound
element exists in a committed contract (`contracts/` is read, never the
warehouse); every term or concept named exists in the register or is
added in the same set; a label or a synonym owned elsewhere is refused;
an amended definition equal to the current one is refused; a deprecation
names a successor the register carries or the set adds, or none; a drop
is refused while a binding stands, while the item is not yet deprecated,
or, for a concept, while a child names it as parent; a parent change
that would close a cycle is refused; `by` is a person. It classifies
every change: additive (no existing binding's digest moves), changing
(a term's or a concept's digest moves, and the command re-binds every
binding that cites it under the set's intent, `by`, and day, listing
each by name), or removing (a deprecation first, additive in its
mechanics and served as declared; then a drop; HW-35, deprecate then
drop). It renders into `proposals/meaning/<name>/`, named from the
change-set file so a repeated draft overwrites itself and no clock is
read, the four register files as they would read after the set, the
re-bound rows carrying this set's intent and day, `record.json` (the set
verbatim, the intent verbatim and hashed, the classification per change,
the re-bound elements by name, the register digests before and after,
who and when), and `summary.md` for the pull request body. It touches
nothing under `meaning/` or `contracts/`, and it has no flag that
certifies anything and no flag that relaxes a check. The person copies
the rendered files onto a branch and opens the pull request; the
reviewer reads the definition diff and each re-bound element beside it;
the unit lane holds the registers to their contracts and every binding
to its term; the merge is the only approval, and `make context` runs in
the same pull request once the compiled context harvests the registers
(F-29). A changed definition is never neutral: a binding whose term
moved without a re-bind reads `term_changed` (Amendment AC) and blocks
the merge. **Who certifies.** As D-43: a declarer, a binder, or the
`by` of a change set is a person; code refuses the names it can check
(the two proposers' names, the D-34 model identifiers, the resident
subagent's name, and any `claude-` name) and the rest is the person's
own attestation, a value in a file or on a make line being something an
agent can supply exactly as `bind --by` is today. Consent in chat is
permission to draft, never certification; what a person approves into
the record is rendered by code; text gathered from a chat or a pasted
document is untrusted, labeled authored, never executed, and read by a
person before merge. The control for a steward, when one exists, is
CODEOWNERS on `meaning/`; with one maintainer this slice adds none.
**The host door is a command, not a tool.** The host's agent reads what
exists (the register files, the module's `find`, and the served context
through the five tools), drafts the change set, asks for consent, and
runs the command; no MCP tool is added, the `mm` entry point is not
widened (D-42), and a sixth tool would need a [D-31](#d-31) amendment
and a measured need, which no host measured so far supplies (a chat host
without a shell cannot run a command, and a host that drops the server's
instructions cannot be steered to one). The command is host-neutral and
model-neutral: every check that matters is code. **The boundary.** The
governed meaning module (`src/metricmine/meaning/`) is deterministic
code of the kind D-10 as amended by Amendment G names beside the
proposers, never a third agent; a glossary term or an ontology concept
is never a proposer input (D-23 as amended by Amendment H), the governed
inputs stay the three Amendment H kinds, and the unit lane holds that no
module under the agents package imports the meaning module or the
compiler, as it holds for documents. The carried-by list (which elements
carry a term) is derived from the bindings, never authored. The demo's
terms and concepts come from the two public sources, nycflights13 and
OurAirports, in the steward's own words. The server never prints an
assurance it cannot check: when a term is served, the note says what the
compile checked and never that a term is current. Two truths: when a
term's definition and a contract's sentence disagree, the contract's
sentence is the certified claim and the term is its label; no state
detects the disagreement, the review date is what forces a read, and the
disagreement is an item for a person, never an automatic override
(D-43's rule, restated for terms). **The slices.** The decision mints by
this documentation pull request. The implementing slice lands the two
register contracts by their own pull request, then the module, the
scan's section (Amendment AC), the tests, the demo's registers, and the
spec (`docs/spec/meaning.md`) with the CLAUDE.md edits that name the
module; the serving slice amends D-30 and D-31. **Not decided here:**
what `get_context` serves and the budget's number (a `meaning` block
beside `documents`, declared apart from measured, under a note; the
per-field `terms` and `concept` lists; the served edges in Amendment
AA's shape; a recommended budget of 6,000 characters of compact JSON per
entry, set and measured by the amendment that serves it; the freshness
check's two new sources; the compiled schema's next version); the
contract-plane pointer rendered from the register; an import of a
spreadsheet glossary or a SKOS file into the outbox; the origin of a
draft's words per change (HW-23); the silver contracts' naming
convention (a Backlog item), which touches the same contracts a glossary
binds; and ODCS v3.2.0's
`context` block, which changes where authored meaning lives only when
the pin moves (D-05, D-06). Full text: Decision Record 016.

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
| 1 (pins; amendment required) | D-05 (Amendment X), D-06 |
| 2 (dbt Core v2 is the engine; the registered driver; gate two as run, then test) | D-04 and D-05 (Amendment X), D-20 (Amendment Y), evidence [F-66](../verification/gate_proof_findings.md#f-66) |
| 3 (profiler uncontracted; transforms contracted SQL) | D-04 |
| 4 (contracts all-or-nothing) | D-06, D-08 |
| 5 (only not_null trusted; tests for the rest) | D-12, evidence [F-06](../verification/gate_proof_findings.md#f-06)/[F-08](../verification/gate_proof_findings.md#f-08) |
| 6 (never weaken a contract) | D-08, D-28 |
| 7 (no materialized views; incremental behind configuration) | D-07 (Amendment O), D-38 |
| 8 (ownership-manifest checksums) | D-09 |
| 9 (engine emits models, never DDL; mapping-contract placement; one mapping per category, the fan-in) | D-07, D-29 (Amendment U), D-41 |
| 10 (gate three under uv run; top-level `datacontract test` unused) | D-12, D-16; gate-two mechanics per D-20 |
| 11 (properties hand-authored on the silver plane; sync-created at adoption; engine-emitted on gold; sync output reviewed) | D-16 (Amendments C, J), D-29, evidence [F-02](../verification/gate_proof_findings.md#f-02)/[F-05](../verification/gate_proof_findings.md#f-05)/[F-14](../verification/gate_proof_findings.md#f-14)/[F-27](../verification/gate_proof_findings.md#f-27) |
| 12 (unified event star; the conformed calendar; conformance in silver, declared at the contract plane; the declared cross-category joins; materialization modes; the typed mart default; projections; batch-scoped gates) | D-17 (Amendments P, R), D-36 (Amendment Q), D-38, D-39, D-41 |
| 13 (canonical_key v2, deterministic payloads) | D-18 |
| 14 (registry binding; fact key; declared grain) | D-19 |
| 15 (proposer runtime: one structured call; proposal schema projection; allow-listed model override; governed inputs per stance; no tools/MCP/loops; outbox-only; the deterministic code named beside the proposers; a term or a concept never a proposer input) | D-21 (Amendment F), D-23 (Amendment H), D-34, D-35, D-43, D-44, evidence [F-26](../verification/gate_proof_findings.md#f-26) |
| 16 (versioned prompts; contract provenance incl. proposerStance and amendsContract; pattern-derived absence rule) | D-22 (Amendment I), D-29 |
| 17 (human-only draft-to-contract flow; no relaxation without the flag; report-and-stop on fail-closed; keyless make demo) | D-24, D-08, D-10 (Amendment G), D-35 |
| 18 (serving boundary: shared module, three-layer read-only, capped results, the typed-surface steer; the data and expert-context split; the served sources and their budget; the gold scope and the tools' annotations; the demo artifact as a release asset) | D-31 (Amendments W, AA, AB), D-32, D-33 (Amendment S), D-03 (Amendment S), D-30 (Amendments W, AA), D-43, evidence [F-72](../verification/gate_proof_findings.md#f-72) |
| Conventions (never read or write outside the working tree; enforced by the working-tree guard hook; who runs a command over the governed documents root) | D-37, D-13, D-43, evidence [F-32](../verification/gate_proof_findings.md#f-32) |
| Toolchain (the supported matrix; `make` over `uv run mm`; the Windows text rules; line endings, the committed document copies included) | D-42, D-43 |
| Architecture boundaries (the governed documents module: deterministic code, identity as extracted text, never a private location, the register changed only by pull request; the context compiler's harvest of the register, committed files only and never a calendar; the governed meaning module: deterministic code, identity as a stable id and a content digest, the registers changed only by pull request, a change set rendered to the outbox and never to the registers) | D-43, D-35 (Amendments Z, AC), D-10 (Amendment G), D-30 (Amendment AA), D-44 |

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
August 28, 2026 revision (Decision Record 009), and D-37 as of the
August 29, 2026 revision (Decision Record 010), and D-38 through D-40
(with Amendments O, P, and Q) as of the Decision Record 008 part two
revision landed with Arc 5b, and D-41 (with Amendments R through W)
as of the September 2, 2026 revision (Decision Record 011), and D-42 as
of the September 6, 2026 revision (Decision Record 012), and Amendments
X and Y as of the October 3, 2026 revision (Decision Record 013), and
D-43 (with Amendment Z to D-35) as of the October 17, 2026 revision
(Decision Record 014), and Amendments AA and AB as of the October 19,
2026 revision (Decision Record 015), and D-44 (with Amendment AC to
D-35) as of the October 26, 2026 revision (Decision Record 016). D-20's
substance
is encoded directly in
[`.github/workflows/contract-gate.yml`](../../.github/workflows/contract-gate.yml)
and, since Amendment Y, named in CLAUDE.md rule 2,
and its guard-split obligation lands with the pull request that initializes
the dbt project. Like D-20, D-26 through D-28 carry no dedicated CLAUDE.md
rule: D-26 lives in the repository settings and branch protection, D-27 in
the workflow's bronze-landing step, and D-28 in the contracts' severity
declarations (evidence
[F-08](../verification/gate_proof_findings.md#f-08)).
Implementation of D-17 through D-19 lands in the gold phase
and D-21 through D-25 in Phase 6; adoption is not contingent on it.
