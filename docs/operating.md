# Operating MetricMine: the standard procedures

> Repo path: `docs/operating.md`
> The operator's manual: what the daily commands do and in what order,
> the procedures for the situations that recur (a fresh clone, a cold
> build, a contract change, a new source, an adopted model, a proposer
> run, a release, a source refresh, a review), what every gate means
> when it fails, and a glossary. The specs under `docs/spec/` say what
> the system is; this page says how to run it. Decisions cited as D-nn
> resolve in [the register](decisions/decision-register.md); findings
> cited as F-nn in [the findings](verification/gate_proof_findings.md).

## 0. Orientation

Three planes, one working DuckDB file, three schemas. `contracts/` is
the specification a person reviews. `transform/` executes it as dbt
models. `src/` is hand-written code: the profiler, the engine, the
context compiler, the adoption tools, the two proposers, the serving
module. Bronze is landed, never edited. Silver is human-owned SQL under
contracts. Gold is engine-emitted from mapping contracts and never
edited by hand.

What is generated and what is written:

| You write | A command generates | A gate holds them together |
|---|---|---|
| a fetch script and a README | the extract, the profile | the samples gate |
| a cleanup contract and a model | the properties file (sync, then `enforce-properties`), the singular tests | gates 2 and 3, the scan |
| a mapping contract, a paste into the star contract | the star's models, marts, views, properties, the ownership manifest, the compiled context, the star's singular tests, the emission oracle | the pattern gate, the oracle, the manifest gate |

The shells. Everything in this manual runs keyless except the proposer
stances and the eval lane, which read `ANTHROPIC_API_KEY` from the
environment. Keep one shell for those (load the key there and nowhere
else) and do the rest, including anything a coding agent runs, in a
shell without it. `make demo`, the tests, and CI never need a key.

The exports. The local dbt lanes need two absolute paths in every fresh
terminal; `make doctor` prints them for your clone:

    export DBT_PROFILES_DIR="<clone>/transform"
    export MM_WAREHOUSE_PATH="<clone>/warehouse/metricmine.duckdb"

The daily commands, in the order they depend on each other:

| Command | What it does | Reads | Writes |
|---|---|---|---|
| `make doctor` | checks the platform, uv, the locked toolchain, the isolated `datacontract-cli`, the demo artifact | | nothing |
| `make ingest` | lands every `ingestion.sources` entry into bronze, replace semantics | the committed extracts | the warehouse's bronze schema |
| `make profile ONLY=<schema>.<table>` | measures a table into a committed artifact | the warehouse, read-only | `profiles/<schema>.<table>/vNNNN.json` |
| `make scan` | derives the adoption queue and names the next command per item | the tree, the contracts, the profiles, the warehouse | `proposals/plan.md` (gitignored) |
| `make context` | compiles every governing contract into the next context artifact | `contracts/` | `context/compiled/vNNNN.json` |
| `make regen` | emits the gold star from the mapping contracts | `contracts/`, the newest context | `transform/models/gold/`, the ownership manifest |
| `uv run dbt build --project-dir transform --target local` | builds every model with contract enforcement and runs every test | | the warehouse |
| `uv run datacontract dbt sync contracts/*.odcs.yaml --project-dir transform --target local` | writes the contracts' rules as dbt tests and refreshes properties | `contracts/` | `transform/tests/datacontract_cli/`, properties files |
| `uv run datacontract dbt test contracts/*.odcs.yaml --project-dir transform --target local` | runs the contract tests (gate 3) | | |
| `make audit-gold` | every contract-generated gold test in full-table form | | |
| `make export-demo` | exports the gold schema to the demo artifact and refreshes its digest manifest | the warehouse | `demo/demo.duckdb` (gitignored), `demo/demo.digest.json` |
| `uv run python scripts/check_demo_digest.py` | holds the manifest to the built warehouse's content | | |
| `uv run ruff check .`, `uv run pytest -m "not local" -q`, `uv run pytest -m local -q` | the lint, the unit lane (CI), the local lane (needs the warehouse) | | |

## 1. A fresh clone to a served star

Path A serves the released artifact in two minutes; Path B rebuilds
everything keyless in about eight. Both are in
[docs/demo.md](demo.md) with the Claude Desktop wiring. The short
form:

    git clone https://github.com/metricminellc/metricmine.git && cd metricmine
    uv sync
    make doctor
    make demo-fetch        # Path A: the release asset, verified against the manifest
    make demo              # Path B: ingest, build, export, keyless

Between tags the manifest may name no release; `make demo-fetch` says
so and Path B is the path. `make doctor` reports the demo artifact as
a WARN with the hint until one of the two has run; that is a hint, not
a failure.

## 2. The build loop, and when to build cold

A warm build (`dbt build` over an existing warehouse) is fine while you
iterate on one model. Build cold whenever a contract changed, a
category was added, or you are about to claim a number: remove the
warehouse and the parse cache, land, build.

    rm -f warehouse/metricmine.duckdb warehouse/metricmine.duckdb.wal && rm -rf transform/target
    make ingest
    uv run dbt build --project-dir transform --target local

Why both removals. A warehouse that already carries tables cannot show
what a fresh clone sees: a test that runs before its table exists
passes on a warm warehouse and fails cold (F-51), which is why unified
silver rules name their table through `ref()`. And dbt's partial-parse
cache remembers a test it disabled during a contract bump (the F-13
window) and keeps it disabled after the models arrive, so a build that
reads the cache ends one test short with no warning (F-53). A count one
short of the expected total after a contract bump is a parse-cache
symptom before it is anything else.

The incremental mode (D-38) is one config line: `engine.materialization:
incremental` in `config/default.yaml`, then `make regen`, landed as a
regeneration pull request. The first build is full; later builds
process silver rows above each table's `captured_at` watermark and
insert through content-key anti-joins. Gate a batch with its floor
(`--vars '{mm_batch_floor: "<timestamp>"}'` on the gold tests) and run
`make audit-gold` for the full-table forms on whatever cadence suits.
[docs/scale.md](scale.md) has the measured curve and the steps.

## 3. Adding a source

The whole procedure, validated on a source outside the demo, is
[docs/adding-a-source.md](adding-a-source.md). The shape: a fetch
script and a README; entries under `ingestion.sources` and
`profiling.targets` and a row in `sources.yml`; `make ingest` and
`make profile`; a cleanup contract written from the profile (or drafted
by the cleanup proposer) and a model, with the scan driving the
enforcement wiring; a mapping contract; the three rendered star objects
pasted into the star contract with a minor bump; `make context`,
`make regen`, the oracle refresh, the star's generated tests renewed;
a cold build, the gates, the export. The reasoning behind every
decision the demo sources took is in
[docs/sources-explained.md](sources-explained.md), written as the
pattern to reuse.

## 4. Changing a contract

Contracts change by pull request, contract first, model second (rule
6), with a version bump every time (D-08). A change that narrows a
contract (a required column made optional, a rule removed, a type
widened) is a major bump and is refused by the amend stance without
`ALLOW_RELAXATION=1` and the printed warning. A required addition
enters optional and tightens after the model populates it (F-28).

For a silver contract:

1. Edit the contract (or `make propose-amend TABLE=<table> INTENT="..."`
   in the key-bearing shell and review the draft in the outbox), bump
   the version, lint it. The scan reads `amend` until the model catches
   up.
2. Contract-only pull request; the gates run; merge is approval.
3. On a model branch: the model change if any; `uv run datacontract dbt
   sync contracts/<table>.odcs.yaml --project-dir transform --target
   local` refreshes the properties file in place and writes the new
   version's singular tests; remove the previous version's tests
   (`git rm transform/tests/datacontract_cli/<table>/<table>__<old>__*.sql`,
   F-48); build; gate 3; the scan reads `in_sync`.

For the star contract, the same with two more steps: `make context`
(the compiled context cites the star's version) and `make regen` (the
emitted headers carry it), then the oracle refresh. A bump that adds a
category opens a window (F-13): between the contract landing and the
regeneration landing, dbt disables the registry coverage rule with a
warning naming the missing dimensions, and the build ends one test
short. That warning is the window, not a defect; the regeneration
closes it. Every regeneration refreshes the demo manifest
(`make export-demo`), because the registry digest moves with the
compiled context.

## 5. Adopting an existing model

The bottom-up path for a hand-written silver model that has no
contract: [docs/adoption.md](adoption.md). `make scan` classifies every
model (`adopt`, `amend`, `unenforced`, `contract_ahead`,
`needs_profile`, `needs_build`, `in_sync`, and the jurisdictional
skips) and names the exact next command; `make propose-describe
TABLE=<model>` drafts the contract from the model's own profile;
`make verify-grain TABLE=<model> KEYS=<a,b>` measures the proposed
grain; sync creates the properties file from the approved contract and
`make enforce-properties TABLE=<model>` adds the two keys sync omits.
`make propose-queue MAX=<n>` walks the queue in batch, one structured
call per item, stopping at the cap or the first fail-closed exit.

## 6. Running the proposers

Two agents exist: the silver cleanup proposer (stances cleanup,
describe, amend) and the gold mapping proposer (stances propose,
amend). Each run is one structured API call over one governed, hashed
artifact (the profile; for amend, the committed contract and your
intent), validated against the proposal schema, rendered to a contract,
linted, and written only to the gitignored `proposals/` outbox. Nothing
under `contracts/` moves without you.

    make propose-silver SOURCE=<bronze table> [TARGET=<contract id>] [ORACLE=<contract path>]
    make propose-mapping TABLE=<silver table> [TARGET=<contract id>] [ORACLE=<contract path>]
    make propose-describe TABLE=<silver table>
    make propose-amend TABLE=<table> INTENT="<the change, in a sentence>"
    make propose-queue MAX=<n> [INTENT="..."]
    make eval-agents

The model is `claude-sonnet-5` by default and may be overridden per run
to an allow-listed id (`MODEL=` or `MM_PROPOSER_MODEL`; D-34); the
model used is recorded in the proposal record and stamped into the
contract's provenance. Validation failures retry at most twice, then
the run fails closed with nothing written; on a fail-closed exit,
read the record, fix the cause, and run it yourself; never re-invoke
unattended. The harness prints tokens and cost per call. The review is
yours: read the draft against the profile, trim anything the model
declared beyond your intent (D-24), copy it into `contracts/` on a
branch, bump, open the contract-only pull request. `make eval-agents`
runs every fixture in the eval configuration against its recorded
oracle and reports agreement; it needs the key and never runs in CI.

## 7. The gates, and what a failure means

| Gate | Command | A failure means | What to do |
|---|---|---|---|
| Gate 1, lint | `uv run datacontract lint <contract>` | the contract is not valid ODCS or the mapping violates its schema | fix the contract; never the gate |
| Gate 2, build enforcement | `uv run dbt build ...` | a model's shape disagrees with its contract (a column missing, a type drifted, a not_null violated) or a test failed | fix the model, or amend the contract with a bump; never weaken a contract to pass |
| Gate 3, contract tests | `datacontract dbt sync` then `datacontract dbt test` | a contract's quality rule fails in the warehouse (a grain duplicate, a regex miss, a completeness under its floor, a conservation break) | read the named rule; the fix is in the data path or a deliberate amendment |
| The unit lane | `uv run pytest -m "not local" -q` | a keyless invariant broke: the emission oracle, the pattern gate, K1, provenance, the samples gate, the compiler's tests, the query module | see the named test; the oracle and the pattern gate name the object |
| The local lane | `uv run pytest -m local -q` | a warehouse-backed invariant broke: a declared join drifted, conservation, the serving questions, the server round trip | rebuild cold first; then read the named assertion |
| The audit | `make audit-gold` | a full-table gold rule fails where the batch-scoped run passed | the batch floor hid it; the data path is wrong |
| The manifest gate | `uv run python scripts/check_demo_digest.py` | the committed manifest does not describe the built warehouse | `make export-demo` after a regeneration; commit the manifest |
| The engine's drift guard | `make regen` | an emitted file was edited by hand (rule 8) | discard the edit; change the contract instead |
| The scan | `make scan` | not a failure: a queue of what is out of sync, each with its next command | follow the command |

The symptom table:

| Symptom | Meaning |
|---|---|
| `Catalog Error` on a singular test in a cold build | the test ran before its table existed; the rule must name the table through `ref()` (F-51) |
| the build ends one test short after a contract bump | the parse cache (F-53); remove `transform/target` and build again |
| a `WARNING` that a test was disabled, naming dimensions | the F-13 window; the regeneration closes it |
| sync "updated N YAML files" on a gold model | the ephemeral in-place edit (F-20b); `git checkout -- transform/models/gold/` restores the emitted file, or regenerate |
| the previous version's singular tests still present after a bump | sync names tests by contract version and never removes the old ones (F-48); `git rm` them |
| a code column landed as a number, a date, or missing | the reader inferred it; pin the column to `str` in `reader_options`, and turn `keep_default_na` off when a value is `NA` or another default marker (F-50) |
| `--only names targets not in config/default.yaml` | the profiler's target list is separate from the ingestion list; add the target |
| `test_emission_matches_golden_fixtures` fails after a regeneration | the oracle needs refreshing (copy the emitted set into `tests/golden/emitted/` and review the diff) |
| the demo gate fails after a regeneration | the registry digest moved; `make export-demo` and commit the manifest |
| `make demo-fetch` declines with "no published demo artifact yet" | between tags the manifest names no release; `make demo` builds the content |
| `make doctor` reports the demo artifact as WARN | neither fetched nor built yet; a hint |
| a query result carries `truncated: true` | by design; aggregate or narrow instead of raising the cap |
| a proposer exits with "fail-closed" | validation failed twice after the first attempt; nothing was written; read the record and run it yourself |
| the K1 gate names an undeclared key, a single carrier, or a missing rule | conformance is decoration until the star declares the key, two contracts carry it, and each holds its column to the rule |

## 8. Regeneration and the ownership manifest

`make regen` is deterministic: the same contracts produce the same
files, byte for byte, and the ownership manifest records a checksum
for every emitted file. A regeneration lands as its own pull request
under the manifest (D-09), reviewed as generated code: the diff is the
review. The emission oracle under `tests/golden/emitted/` is the same
set, held byte for byte by the unit lane; after a regeneration you
refresh it and read the diff. The engine refuses to overwrite a file
whose bytes diverged from the manifest, naming it: a hand edit to an
emitted model is never the fix, the contract is.

## 9. Serving

One shared module (`src/metricmine/query.py`) reads the gold star over
a read-only connection three layers deep; the MCP server
(`uv run python -m metricmine.server`) is a thin stdio adapter over it
with exactly five tools (`list_fact_categories`, `get_schema`,
`get_context`, `lookup_record`, `query`). The served database is
`MM_SERVE_DB` if set, else `demo/demo.duckdb`. Wire it into Claude
Desktop as [docs/demo.md](demo.md) shows.

How to read what it serves: every registry entry keeps `data` (derived
declarations) apart from `expert_context` (what the contracts' authors
wrote, labeled authored). `list_fact_categories` names each category's
typed surface, its subject, and its registry keys; analytical questions
belong to the typed marts (`mart_<category>_typed`), and the star's
`fact_*` and `dim_*` tables are the provenance layer. String values on
the typed surface are lowercase text: write literals in lowercase. The
query tool accepts one SELECT, caps rows (default 100, hard cap 500),
and announces truncation. To check a served build against the recorded
answers, run `uv run pytest -m local -q tests/test_serving_questions.py`
with the warehouse in `MM_WAREHOUSE_PATH`.

## 10. Releasing

A release is a tag on a clean `main`, an asset built from that commit,
and a manifest that names the asset.

1. On `main` at the commit to tag: build cold, `make export-demo`,
   `uv run python scripts/check_demo_digest.py` (PASS). The export
   rewrites only the manifest's artifact block (the sha256 and bytes of
   this build's file); leave it uncommitted.
2. `git tag -a vX.Y.Z -m "..."` and push the tag; create the release
   with `demo/demo.duckdb` as its one asset.
3. On a branch: `make demo-manifest RELEASE=vX.Y.Z` pins the uploaded
   asset's name, sha256, and size; commit the manifest and the release
   line in the README; pull request; merge.
4. From a fresh clone, `make demo-fetch` restores the asset and
   verifies it against the manifest. That is the release's own test.

Versioning follows the contracts (semantic: additive changes are minor,
a narrowing change or a key change is major) and the stability rule
(CLAUDE.md rule 19): a clone of `main` at any tag gets a working demo.

## 11. Refreshing a source

A fetch script refuses raw bytes whose digest is not the pinned one and
prints both digests. That refusal is the procedure's first step, never a
silent re-extract.

1. Read the publisher's change. Decide whether the new bytes are the
   window you want.
2. Re-pin `RAW_SHA256`, re-run the script, rewrite the README's
   retrieval, rows, bytes, and extract digest lines; the samples gate
   holds them.
3. `make ingest`; `make profile ONLY=bronze.<dataset>` mints the next
   profile version; `make scan` reads `amend` where the evidence moved.
4. Amend the cleanup contract with the new profile's hash and any
   changed measurement (a join completeness, a null rate), bump, land
   contract first; then the model if the shape changed.
5. If the source feeds a unified table, re-measure the joins (the
   declared-join gate does it) and amend the declared completeness if
   it moved; the floors decide whether the refresh is acceptable.
6. Build cold, gates, `make export-demo`, commit the manifest.

## 12. Reviewing a pull request

Three checks run on every pull request (lint and unit; the contract
gates, which land the samples, build cold, sync, and test; the DCO) and
"no checks reported" is a wait state, never a pass. Beyond the checks:

- A contract pull request: the version bump is present and right
  (minor for additive, major for narrowing); every measurement in the
  prose matches the profile it cites; every `decision*` is a decision
  you agree with; provenance is honest (`proposedBy`, `profileHash`, or
  the absence note for a pattern-derived contract); no rule was
  weakened to pass a gate.
- A model pull request: one typed SELECT per table; no rows dropped
  without a decision; the properties file human-owned and reviewed;
  the generated tests read; the previous version's tests gone.
- A regeneration pull request: the diff of the emitted set is the
  review; the manifest, the oracle, and the context artifact moved
  together; the demo manifest refreshed.
- A source pull request: the README states the license, the pin, the
  raw digest, the window, the extract digest; the script pins the raw
  digest and declares its budget.

## 13. Glossary

- **Bronze, silver, gold**: the landed layer (as published), the
  human-owned contracted layer, the engine-emitted star.
- **Category**: one fact category of the star, from one mapping
  contract over one silver table.
- **Typed surface**: the per-category mart (`mart_<category>_typed`)
  and projection view an agent queries; typed columns, lowercase
  strings.
- **Conformed key**: a code shared across sources, normalized by one
  rule declared on the star and carried by at least two silver
  contracts.
- **Conformed calendar**: the star's one timeframe dimension, a row
  per (grain, period start), shared by every category.
- **Registry**: `context_registry`, the table that binds every schema
  key to its contract and its compiled context; `data` and
  `expert_context` are its two halves.
- **Compiled context**: the committed artifact `make context` mints
  from the contracts, carried into the registry as literals.
- **Ownership manifest**: the checksum ledger of every emitted gold
  file; the engine's boundary.
- **The oracle**: `tests/golden/emitted/`, the emitted set the unit
  lane holds byte for byte.
- **Stance**: a mode of one of the two proposers (cleanup, describe,
  amend; propose, amend).
- **The outbox**: `proposals/`, gitignored, where drafts and records
  land and nothing else does.
- **The scan**: `make scan`, the derived queue of what is out of sync.
- **The window (F-13)**: the state between a star bump that adds a
  category and the regeneration that emits it.
- **Cold build**: an empty warehouse and no parse cache, then land and
  build; what CI does.
- **Amendment**: a change to a decision in the register, minted by its
  own documentation pull request before the implementing change lands.
