# Gate Proof Findings: Verified Toolchain Behavior

Scratch gate proof run July 11, 2026, prior to Phase 1 exit (Decision
[D-12](../decisions/decision-register.md#d-12)).
Toolchain: dbt-core 1.11.12 · dbt-duckdb 1.10.1 · DuckDB engine 1.4.3 ·
datacontract-cli 1.0.12 (isolated uv tool). All findings below were observed
directly, not inferred from documentation. The gate path was re-proven at
dbt-core 1.12.3 with dbt-duckdb 1.11.0 at Arc 1 ([F-30](#f-30)) and at
dbt Core v2 (dbt-oss 2.0.5) in October 2026 ([F-66](#f-66)); every
finding stands. They supersede any conflicting
guidance in older references. Governing rules: CLAUDE.md rules 10 and 11.

Findings carry canonical IDs of the form **F-nn**, cited from the
[decision register](../decisions/decision-register.md) and from commit bodies.
IDs are stable; the layout below is topical, so IDs appear out of numeric
order by design.

| ID | Finding | Section |
|---|---|---|
| [F-01](#f-01) | Export interface changed at v0.12.0 | Command surface |
| [F-02](#f-02) | Export emits generic types; properties are hand-authored | Properties files |
| [F-03](#f-03) | Top-level `datacontract test` unsupported for DuckDB | Command surface |
| [F-04](#f-04) | PATH requirement: `uv run` prefix is mandatory | Command surface |
| [F-05](#f-05) | Sync edits in place; known mistranslation bug | Gate-three mechanism |
| [F-06](#f-06) | Constraint enforcement matrix | Constraint matrix |
| [F-07](#f-07) | Break evidence, both directions | Two-gate asymmetry |
| [F-08](#f-08) | Generated tests are warn-only; enforcement lives in contract severities | Model rung |
| [F-09](#f-09) | `datacontract dbt test` runs dbt from inside the project directory | Model rung |
| [F-10](#f-10) | Profile duplicate metrics cannot see near-duplicates | Model rung |
| [F-11](#f-11) | DuckDB key-function semantics at the pinned engine | Engine rung |
| [F-12](#f-12) | Model-less contracts skip cleanly; collisions fail loudly | Engine rung |
| [F-13](#f-13) | Partially-modeled multi-object contracts hold the gate green | Engine rung |
| [F-14](#f-14) | The sync fixed point exists and is reachable by emission | Engine rung |
| [F-15](#f-15) | json_valid gates VARCHAR canonical payloads | Contracts rung |
| [F-16](#f-16) | canonical_key v2 SQL and Python agree at function level | Contracts rung |
| [F-17](#f-17) | Sync twins single-column primaryKey flags with unique tests | Contracts rung |
| [F-18](#f-18) | Sync canonicalizes properties YAML project-wide | Contracts rung |
| [F-19](#f-19) | Singular tests without ref() break fresh builds | Contracts rung |
| [F-20](#f-20) | A star-contract bump re-keys singular tests and re-edits properties | Contracts rung |
| [F-21](#f-21) | A mapping bump is gate-quiet; blast radius is the emission set | Contracts rung |
| [F-22](#f-22) | A probe in an isolated venv proves the SDK, never the pin | Serving rung |
| [F-23](#f-23) | At transaction grain the category dimension is 1:1 by construction | Serving rung |
| [F-24](#f-24) | fact_hash_id addresses the measure payload, never the row | Serving rung |
| [F-25](#f-25) | A demo artifact named for its schema collides with its own catalog | Serving rung |
| [F-26](#f-26) | The frozen mapping-contract schema is not a structured-outputs schema | Agent rung |
| [F-27](#f-27) | `datacontract dbt sync` creates the properties file for a contracted model that has none | Agent rung |
| [F-28](#f-28) | The contract-before-model window admits optional additions and rejects required ones | Agent rung |
| [F-29](#f-29) | A governing-contract version bump closes the F-28 window at the compiled-context freshness gate | Agent rung |
| [F-30](#f-30) | dbt 1.12 lands clean; the line brings a lock-pinned binary the register must name | Toolchain rung |
| [F-31](#f-31) | The v2 parser gate is parse-only for a contract-enforced project; the beta engine builds it | Toolchain rung |
| [F-32](#f-32) | A prose working-tree rule needs a PreToolUse hook; the guard is measured | SDLC rung |
| [F-33](#f-33) | A working-tree guard must allow the tool's own state and a runner's action directory; the prep's stdin cases could not see either | SDLC rung |
| [F-34](#f-34) | Contracted incremental models require on_schema_change at dbt 1.12 | Incremental rung |
| [F-35](#f-35) | Sync carries jinja var guards in quality-rule SQL verbatim | Incremental rung |
| [F-36](#f-36) | Under `uv run`, `shutil.which("uv")` finds the venv's locked uv, not the operator's | SDLC rung |
| [F-37](#f-37) | The devcontainer installs uv unpinned at create | SDLC rung |
| [F-38](#f-38) | GitHub's GraphQL `issueTemplates` field lists no YAML issue forms | SDLC rung |
| [F-39](#f-39) | `loaded_at` and `captured_at` are build stamps; demo equality holds at the content layer | SDLC rung |
| [F-40](#f-40) | uv.lock bytes vary with the uv version that wrote them | SDLC rung |
| [F-41](#f-41) | A `pull_request` workflow added by a pull request runs on that pull request | SDLC rung |
| [F-42](#f-42) | The star is category-parameterized: a new category adds five objects and a contract amendment | Multi-source rung |
| [F-43](#f-43) | The timeframe group did not conform across categories; the conformed calendar does | Multi-source rung |
| [F-44](#f-44) | Hex hash text dominates the star's storage; block size is not a lever | Multi-source rung |
| [F-45](#f-45) | Profile artifacts embed capture-time values; a full run re-mints every artifact | Multi-source rung |
| [F-46](#f-46) | The committed silver profile predates `captured_at`; the scan reads it as an amend item | Multi-source rung |
| [F-47](#f-47) | The local-marked pytest lane was red at v1.0.0 and CI could not see it | Multi-source rung |
| [F-48](#f-48) | Sync names generated tests by contract version; a bump leaves the old files | Multi-source rung |
| [F-49](#f-49) | A measured zero-null column declared optional is a scan disagreement; new contracts declare `captured_at` required | Multi-source rung |
| [F-50](#f-50) | The source-file connector's pandas defaults read "NA" as missing | Multi-source rung |
| [F-51](#f-51) | Sync-generated singular tests carry no dependency edge; a silver model built from other silver models names itself through `ref()` in its rules | Multi-source rung |
| [F-52](#f-52) | YAML 1.1 boolean words as mapping keys: `on` parses as `True` and breaks canonical sorting | Multi-source rung |
| [F-53](#f-53) | dbt's partial-parse cache keeps a test disabled across the F-13 window; the regeneration build clears `transform/target` | Multi-source rung |
| [F-54](#f-54) | The local lint lane fails on a machine without the isolated `datacontract` tool; the module skips by name | Windows rung |
| [F-55](#f-55) | A hosted Windows runner proves the stdio launch of the server, never the desktop client's click-through | Windows rung |
| [F-56](#f-56) | A Windows tool answer stalled inside DuckDB's lazy pandas import, whose numpy load runs an OpenBLAS DLL that calls `fstat(0)` and serializes behind the reader's pending stdin read; the server imports the native modules at startup, before the transport | Windows rung |
| [F-57](#f-57) | A heavily non-ASCII sample failed the connector's check on Windows, which reads a CSV in the platform default (cp1252) when the reader options name none; the ourairports samples declare `encoding: utf-8` (the earlier file-URI reading was wrong and reverted) | Windows rung, Path B |
| [F-58](#f-58) | Three keyless download paths built no SSL context, so a python.org macOS build with an empty OpenSSL trust store failed every fetch before anything built; they now add certifi's bundle to the machine's own trust, which naming a cafile would have replaced | Toolchain rung, continued |
| [F-59](#f-59) | The Git for Windows installer asks for elevation and winget's user scope does not avoid it, so "no step needs administrator rights" held only after the two installs | Chore rung |
| [F-60](#f-60) | `make demo` reaches the Airbyte connector registry unless `AIRBYTE_OFFLINE_MODE=1` is set, and nothing a stranger runs sets it | Chore rung |
| [F-61](#f-61) | `make export-demo` and `make demo` rewrite the committed digest manifest to the local build, and `make demo-fetch` then refuses until it is restored from git | Chore rung |
| [F-62](#f-62) | A governed amendment corrected a silver description and left its restatement in the mapping contract stale; the served context carried both sentences, and the class is every edge where one contract restates another's column | Chore rung |
| [F-63](#f-63) | A committed `.mcp.json` is loaded without asking by every non-interactive Claude Code session, so its launch line installs nothing and fails fast on a clone that was never synced | Chore rung |
| [F-64](#f-64) | The Microsoft Store build of Claude Desktop runs the terminals it opens under app-package virtualization, so `uv sync` from one fails on uv's Python link; two uv variables move the install out of `AppData` | Chore rung |
| [F-65](#f-65) | Three compiler tests made a symlink that Windows grants to administrators and Developer Mode only, so the runners passed and a per-user machine failed them; the fixture falls back to a copy | Chore rung |
| [F-66](#f-66) | dbt Core v2 builds the project after one properties-key move, resolves the package hub on every parse unless the package is local, schedules the edge-less generated tests before their models on a cold build, and ships no DuckDB driver; the engine downloads at install and the driver at first run unless the project registers its own | dbt Core v2 rung |

## Command surface (datacontract-cli 1.0.12)

### F-01
**Export interface changed at v0.12.0.** `--format` was REMOVED from `export`
at v0.12.0. Use subcommands:
`datacontract export dbt-models <contract> --output <file>`
(also: `dbt-sources`, `dbt-staging-sql`).

### F-04
**PATH requirement: the `uv run` prefix is mandatory.** All
`datacontract dbt ...` commands MUST run as `uv run datacontract dbt ...`.
The isolated tool cannot find dbt on PATH by itself; bare invocation fails
with "dbt not found on PATH". This applies in CI too.

### F-03
**Top-level `datacontract test` is unsupported for DuckDB.**
`datacontract test <contract>` does NOT work against DuckDB at 1.0.12
("Server type duckdb not yet supported"). It parses the contract and lists
checks but executes none. Never use it as a gate. It is a different command
from the gate's `datacontract dbt test` subcommand (CLAUDE.md rule 10).

## Gate-three mechanism (Decision [D-16](../decisions/decision-register.md#d-16))

1. `uv run datacontract dbt sync <contract> --project-dir transform --target local`
2. `uv run datacontract dbt test <contract> --project-dir transform --target local`

### F-05
**Sync edits in place, preserves hand-authored content, and carries one known
mistranslation bug.** Observed sync behavior at 1.0.12:

- Edits the hand-authored model .yml IN PLACE (no separate generated dir).
- PRESERVES hand-authored data_types and constraint placement.
- Translates `sql` and `rowCount` quality rules into correct singular tests
  under tests/datacontract_cli/.
- BUG: mistranslates `duplicateValues mustBe 0` into an `accepted_values: [0]`
  column test ("field equals 0") at severity warn. It fires as a warning on
  every row. Delete this test whenever sync generates it. Keep uniqueness as
  a `data_test: unique` on the column.
- Consequence: sync output is a PROPOSAL. Review its yml diff and generated
  tests in every PR before trusting them
  ([D-08](../decisions/decision-register.md#d-08)/[D-09](../decisions/decision-register.md#d-09)
  applied to generated code).

## Properties files (A4 decision)

### F-02
**Export emits generic types; dbt properties files are hand-authored.**
`export dbt-models` without a server flag emits GENERIC types
(NUMBER/FLOAT/TIMESTAMP_TZ) that mismatch DuckDB and fail the compile-time
contract gate falsely. It also renders single-column PK uniqueness as a
constraint, conflicting with rule 5. Therefore: dbt properties files are
hand-authored; export output is scaffold/drift-check only, never committed
as the properties file. The observed drift diff is preserved at
[`evidence/2026-07-11_export_drift_diff.txt`](evidence/2026-07-11_export_drift_diff.txt).

## Constraint enforcement matrix (empirical)

### F-06
**All five constraint types are enforced by DuckDB at build time; rule 5
stands as a portability stance.** Full probe method, per-constraint error
signatures, and the reconciliation narrative:
[`duckdb_constraint_matrix.md`](duckdb_constraint_matrix.md).

| Constraint  | Accepted | In DDL | Enforced at build | Notes |
|-------------|----------|--------|-------------------|-------|
| not_null    | yes      | yes    | yes               | model step errors on violation |
| unique      | yes      | yes    | yes               | same mechanism as primary_key |
| primary_key | yes      | yes    | yes               | "PRIMARY KEY or UNIQUE" error |
| check       | yes      | yes    | yes               | `expression:` key works |
| foreign_key | yes      | yes    | yes, conditional  | referenced table must carry a PK/unique key, else Binder Error at CREATE |

DuckDB enforces all five locally. Rule 5 still holds because it is a
PORTABILITY stance: only not_null is enforced across all target adapters,
so uniqueness and referential integrity live in tests regardless. Do not
"simplify" tests away on the grounds that DuckDB enforces the constraint.

## Two-gate asymmetry (proven)

### F-07
**Break evidence, both directions.**

- Shape defect (renamed column): fails at COMPILE time, before any DDL,
  error names the column, all tests skip.
- Content defect (broken dedupe): model BUILDS, then the uniqueness test fails.
- Fix defects in the SQL. Never weaken a contract to make a build pass
  ([D-08](../decisions/decision-register.md#d-08)).
  Contract changes are separate PRs with a version bump.

Full narrative: Session A Gate Proof Findings, Rev. 1 (a project record,
maintained outside the repository; nothing here depends on it).

## Model rung (Session F, Sitting 2, July 31, 2026)

Findings observed while landing the first contracted silver model
(contract v1.1.0, PRs #42 to #44) and in the live break demo (PR #45, closed
unmerged by design). Same pinned toolchain as above.

### F-08
**All `datacontract dbt sync` generated tests carry severity warn at
1.0.12, and the composite primaryKey uniqueness test is HARDCODED warn in
the generator.** Enforcement therefore lives in contract-declared
`severity: error` quality rules, honored via the tool's severity
normalization (error/critical/high/fatal normalize to an error-severity dbt
test; everything else generates warn); the warn composite test is a
non-gating twin. Verified in the installed tool source and end to end.

One behavioral nuance observed live at the #45 break demo: `sql` quality
rules compile to schema-qualified raw SQL, not `ref()`, so when the model
itself fails to build in a fresh warehouse they RUN and fail on a catalog
error rather than skipping (3 errors, 9 skips at #45,
[`evidence/2026-07-31_pr45_gate2_failure.log`](evidence/2026-07-31_pr45_gate2_failure.log)).
Louder red, same verdict; ref-based tests skip as [F-07](#f-07) describes.

### F-09
**`datacontract dbt test` re-invokes dbt from INSIDE the project
directory.** Both `DBT_PROFILES_DIR` and any path inside `profiles.yml`
must be absolute or env-resolved there. The profile's relative db path
failed exactly this way in rehearsal (resolving to `transform/warehouse/`,
the same failure class as the #41 `DBT_PROFILES_DIR` fix one level deeper)
and was fixed by `MM_WAREHOUSE_PATH` env indirection: CI pins it absolute;
the default preserves repo-root runs.

### F-10
**Profile-level duplicate metrics cannot see near-duplicates.** v0001's
`duplicate_row_rate` counted exact duplicates only, while a within-invoice
clock-drift pair (invoice 492807, one minute apart) violated the declared
grain and falsified the v1.0.0 uniqueness claim. Grain claims need direct
measurement against bronze, not profile inference alone.

## Engine rung (Phase 4 planning and prep probes, August 1, 2026)

Findings from the planning session's live function-semantics probe
(duckdb 1.4.3, the pinned engine) and the prep session's three toolchain
probes, run on a fresh clone at head 7345e4e with the CI job environment
replicated verbatim (absolute `DBT_PROFILES_DIR` and `MM_WAREHOUSE_PATH`,
bronze landed offline via `make ingest`, all gates green at baseline).
Full transcript:
[`evidence/2026-08-01_prep_probe_transcript.md`](evidence/2026-08-01_prep_probe_transcript.md).
These findings are load-bearing for
[`docs/spec/engine.md`](../spec/engine.md).

### F-11
**DuckDB key-function semantics at the pinned engine (1.4.3), verified
live.** `sha256()` exists in core, returns VARCHAR, 64-char lowercase hex,
and matches Python `hashlib` byte-for-byte on shared vectors. `to_json()`
over structs emits COMPACT JSON and preserves INSERTION order; it does
not sort, so sorted payload fields are an EMISSION-time property, never
assumed from the engine. `lower()` is unicode-safe over serialized JSON
text (ä, ß verified) and parity with Python `str.lower()` is
vector-checked. `json_valid()` and `json_extract()`/`json_extract_string()`
behave as C4 and the typed projections need. `to_json(list)` yields
compact JSON arrays (the manifest mechanism). VARCHAR casts are
scale-preserving for DECIMAL ("2.50", never "2.5") and render TIMESTAMP
as "YYYY-MM-DD HH:MM:SS", so the Python keying reference must render
decimals via `decimal.Decimal`, never float repr, and the golden vectors
must include decimal, timestamp, and unicode cases. NULL inside a struct
payload serializes as JSON null; the keying spec rules include-as-null
explicitly. Same semantics THROUGH dbt-built models: deliberately
unverified here; lands at the pre-regeneration rehearsal.

### F-12
**A model-less contract in `contracts/` is skipped cleanly by gate 3;
a model-name collision fails loudly and fail-safe.** Sync resolves each
schema object to a dbt model BY NAME and skips unmatched objects with a
stderr warning before any quality-rule translation: `Synced 0 models`,
`no tests` in the per-contract results, exit 0, zero files written, zero
effect on sibling contracts in the same glob, even when the unmatched
object carries query-bearing error-severity quality rules (they are never
half-applied; equally, they are never applied, so rules on a permanently
model-less contract are dead letters and are banned by the engine spec's
JSON Schema). When a schema object name COLLIDES with a model another
contract claims, sync and test both exit 1 (`Cannot sync — overlapping
dbt models`) and write nothing. Flat placement of mapping contracts is
therefore permanent-safe at the pin, under the engine spec's naming rule.
ODCS lint at 1.0.12 tolerates the mapping contract's additive first-class
keys (object-level entityGroup/sourceTable/timeColumn/timeGrain/grain,
property-level mappingRole): verified, and frozen by the pin.

### F-13
**A partially-modeled multi-object contract holds the gate green.** With
one schema object modeled and built and a second object unmodeled (the
second carrying a C3-shaped query rule against its nonexistent table),
sync syncs the matched object (properties updated, singular test written)
and skips the unmatched one; test runs the matched object's tests and
reports the contract PASSED; exit 0 end to end. Consequence for the
ladder: the registry amendment window (contract-first, model one PR
later) is safe in the preferred order. Stated honestly: a skipped
object's rules are declared but NOT enforced until its model lands;
skip is no coverage, not passing coverage.

### F-14
**The sync fixed point exists and is reachable by emission.** Over a
properties file emitted the way a naive emitter would write it, the
pass-1 delta was MEASURED as a unified diff against a preserved pre-sync
fixture carrying deliberately divergent texts
([`evidence/2026-08-01_probe_p3b_pass1_delta.log`](evidence/2026-08-01_probe_p3b_pass1_delta.log)):
(1) the model description AND every column description replaced with the
governing contract's text, verbatim; (2) per `required: true` column, a
`data_tests: - not_null:` block at severity warn carrying
`datacontract_cli` meta (`check: <model>__<column>__field_required`,
`include_in_tests: true`, `contract_versions: [<version>]`,
`generated: true`) and the description `Check that field <column> has no
missing values`; (3) per query-bearing rule on a MATCHED object, a
singular test under `transform/tests/datacontract_cli/<contract_id>/`
with the AUTO-GENERATED header, the contract-declared severity, and the
`WITH _dc_metric` wrapper. Comment headers survive in-place editing, so
generated-by headers are sync-safe. Nothing else changed at this fixture
shape; the pre-regeneration rehearsal re-checks the delta over the real
emitted star. Over the post-sync state, a second sync reports zero
updated files and `sha256sum -c` confirms the model yml and the singular
test byte-identical. An emitter that emits this shape directly produces
files sync leaves untouched; ownership-manifest checksums are defined
over that state ([`docs/spec/engine.md`](../spec/engine.md) §6).

### F-15
**json_valid gates and json_extract projects over VARCHAR canonical
text.** At duckdb 1.4.3, a VARCHAR column holding canonical JSON text (object,
object with a null member, unicode content, and compact-array
manifest forms) returns json_valid true, while garbage and truncated
JSON return false; `COUNT(*) ... WHERE NOT json_valid(payload)` counts
exactly the invalid rows, which is the C4 rule shape the gold star
contract declares at error severity. json_extract and
json_extract_string project payload fields from the same VARCHAR text,
and a projected numeric string casts cleanly to DECIMAL(10,2), the
typed-projection path. Payload and manifest columns therefore declare
`physicalType: VARCHAR` (canonical JSON text, the registry precedent in
[`docs/spec/engine.md`](../spec/engine.md) §4); no JSON physical type is
needed anywhere in the star.
([`evidence/2026-08-08_probe_json_valid_varchar.log`](evidence/2026-08-08_probe_json_valid_varchar.log))

### F-16
**canonical_key v2: the SQL and Python paths agree byte-for-byte at
function level.** The committed golden vectors
(`tests/golden/canonical_key_v2.json`: 16 payload, 5 manifest, 4 scalar
cases, with the canonical serialization stored beside every key) were
recomputed through DuckDB SQL at the pinned engine
(`lower(to_json(struct_pack(...)))` over VARCHAR-cast members in
lowercase-sorted field order, then `sha256()`; manifests via
`lower(to_json([...]))`) and compared against the Python reference
(`src/metricmine/keys.py`): 18 payload and 6 manifest serializations
checked, zero disagreements. Coverage exercised through SQL: unicode
lowercasing (ü/ä/ß), DECIMAL scale-preserving rendering ("2.50",
"5.00"), TIMESTAMP "YYYY-MM-DD HH:MM:SS" with its interior space
preserved, include-as-null, boolean rendering, embedded-quote escaping,
hyphen preservation, the empty string (digest equal to hashlib's), and
the form-(b) derived line_identity composition over the real silver
grain tuple types. The scalar path pins Python only: schema keys embed
as emission-time literals by design. The dbt-path half (the same
semantics THROUGH dbt-built models) deliberately remains with the
pre-regeneration rehearsal ([`docs/spec/engine.md`](../spec/engine.md)
§3).
([`evidence/2026-08-08_probe_sql_python_parity.log`](evidence/2026-08-08_probe_sql_python_parity.log);
the vector generator and parity probe are staged beside it as
`2026-08-08_gen_vectors.py` and `2026-08-08_probe_sql_parity.py`)

### F-17
**Sync generates a per-column `unique:` data_test twin for single-column
primaryKey flags.** At datacontract-cli 1.0.12, `datacontract dbt sync`
writes, beyond the §6-listed `not_null` block, a sync-shaped `unique:`
data_test (severity warn, `check: <model>__<column>__field_unique`,
description `Check that field <column> has no duplicate values`) on every
column flagged `primaryKey: true` ALONE; a composite primaryKey generates
only the sync-owned `unique_combination` singular test. Measured over the
real emitted star at the pre-I rehearsal: the eight single-column PK
dimension keys gained the twin, the four-column fact composite did not.
The engine emits the unique twin as part of the fixed point; the spec §6
delta list carries the amendment.
([`evidence/2026-08-08_prei_sync_pass1_canonicalization.log`](evidence/2026-08-08_prei_sync_pass1_canonicalization.log))

### F-18
**Sync canonicalizes properties-file YAML formatting project-wide, even
under contracts with zero matched models.** Pass 1 over hand-styled but
semantically correct properties files rewrote all nine into the tool's
canonical form (reported as "updated 9 YAML files" under the MAPPING
contract's pass, which matches no model at all); pass 2 reported
"updated 0" for every contract with all files byte-identical. The fixed
point is therefore canonical-FORM-dependent, not just content-dependent,
and the engine emits sync-canonical bytes directly. The form is
reproduced byte-exactly by `yaml.safe_dump(doc, sort_keys=False,
allow_unicode=True, width=2000, default_flow_style=False)` with
descriptions parsed from folded `>` contract scalars (value ends with a
newline) emitted single-quoted and stripped, all others plain.
Generated-by headers survive sync verbatim, re-confirming F-14 over the
real star.
([`evidence/2026-08-08_prei_sync_pass1_canonicalization.log`](evidence/2026-08-08_prei_sync_pass1_canonicalization.log);
[`evidence/2026-08-08_prei_yaml_writer_probe.log`](evidence/2026-08-08_prei_yaml_writer_probe.log))

### F-19
**Contract-declared singular tests without ref() join the DAG root layer
and break fresh-warehouse builds.** Sync passes contract quality-rule SQL
through verbatim, a property this finding both exposed and now exploits.
Raw schema-qualified references (`gold.<table>`) give dbt no dependency
edge, so the generated singular tests schedule in the ROOT layer, before
the models they query exist on a first-ever build. A warmed warehouse
masks the hazard completely (early tests find the previous build's
tables), which is why local runs and the pre-I rehearsal were green while
CI's fresh build errored 12 of the 20 no-ref tests with catalog errors
(PR #64, closed unmerged as this finding's primary evidence; the eight
that passed cold did so only by root-layer ordering luck; all twenty
were unordered). The fix, verified at the pinned toolchain over a fresh
warehouse: gold references in quality SQL use `{{ ref('<model>') }}`;
sync passes the Jinja through verbatim into the generated tests
(measured, not assumed), dbt gains real edges, and the cold build goes
green end to end (the fact model built at node 61, its C1 test ran at
node 78; PASS=95 WARN=0 ERROR=0). C1's silver reference stays
schema-qualified: the F-08 louder-red design is preserved, and the edge
through the fact suffices because the fact depends on silver. Minted
alongside, a rehearsal rule: every pre-sitting rehearsal ends with a
fresh-warehouse cold build (rm warehouse, ingest, dbt build), because
warmed state hides ordering hazards by construction.
([PR #64 CI failure](evidence/2026-08-08_f19_pr64_ci_failure.log);
[`evidence/2026-08-08_f19_coldbuild_pass95.log`](evidence/2026-08-08_f19_coldbuild_pass95.log);
[`evidence/2026-08-08_f19_sync_ref_passthrough.log`](evidence/2026-08-08_f19_sync_ref_passthrough.log))


### F-20
**A contract version bump over a live star regenerates singular tests
under new version-prefixed filenames and re-edits committed properties;
neither effect cleans up after itself.** Measured at the pinned toolchain
during the pre-J rehearsal, with the gold contract amended to v1.2.0 over
the committed v1.1.0 star. (a) Sync writes a full fresh singular-test set
under `<contract>__1_2_0__...` filenames (byte-identical to the 1_1_0
set modulo version strings) and never deletes the stale files; both sets
coexist and `datacontract dbt test` still passes, but a plain `dbt build`
would run both. The transition is therefore sync-owned work committed
post-review in the amendment PR: regenerate, review against the rehearsal
reference, delete the stale set. (b) The same sync run updates every
committed engine-emitted properties file in place (contract_versions
1.1.0 to 1.2.0, the only delta), which on a working tree MUST be
reverted (`git restore transform/models/gold/`), never committed: the
files are engine-owned at the old fixed point, and committing sync's edit
would diverge their ownership-manifest checksums and trip the engine's
rule-8 drift refusal at the next regeneration. In every CI workspace
between the amendment merge and the regeneration merge, gate 3 therefore
reports `updated 9 YAML files` ephemerally and still passes end to end
(the F-13 skip covers the not-yet-modeled registry object); the fixed
point returns when the regeneration lands. Re-verified in the same
rehearsal: the fixed point holds over the EXTENDED emission; the
engine-emitted registry properties synced `updated 0` on the first pass,
and the minimal uncontracted projection properties survived the F-18
project-wide canonicalization byte-identically.
([`evidence/2026-08-09_prej_pr23_window_shapes.log`](evidence/2026-08-09_prej_pr23_window_shapes.log);
[`evidence/2026-08-09_prej_pr24_gate_suite.log`](evidence/2026-08-09_prej_pr24_gate_suite.log);
[`evidence/2026-08-09_prej_cold_build_pass108.log`](evidence/2026-08-09_prej_cold_build_pass108.log))

### F-21
**A mapping-contract version bump is gate-quiet; its entire blast radius
is the emission set.** Measured at the pinned toolchain during the pre-K
rehearsal (mapping v1.0.0 to v1.1.0, country joining, over the live
v1.2.0 star). Unlike the F-20 gold-amendment window, sync reads the STAR
contract only, so gate 3 stays at `updated 0` across all three contracts
for the whole window: no properties re-edit, no singular-test transition,
no git-restore rule anywhere in the sitting; the 34 committed singular
tests never move. The committed star stays internally consistent at the
old emission (old registry rows agree with old columns-dim keys), so
`dbt build` PASS=108 and C1 through C4 hold green on BOTH sides of the
window. The unit lane is the only coupled surface, through two designed
fail-closed mechanisms: the compiled-context staleness guard (the v0001
artifact cites mapping 1.0.0, so `make regen` AND the emission tests
refuse with `run make context` until v0002 mints, the first live fire of the
D-30 guard, exactly as specified) and the golden-fixture equality test.
Consequence, now the recorded packaging rule: the amendment PR carries
exactly three things: the contract bump, the freshly minted
compiled-context artifact, and the refreshed byte oracle (the recorded
D-08 reading, third application); the regeneration PR carries
exactly the emitted set. The signature diff measured: 23 files
+58/−55, ONE new schema key (dims manifest re-keyed; measures, source,
run, timeframe keys unchanged), all five registry rows re-cited at
1.1.0, engine version untouched.
([`evidence/2026-08-10_prek_staleness_guard_live.log`](evidence/2026-08-10_prek_staleness_guard_live.log);
[`evidence/2026-08-10_prek_pr25_window_shapes.log`](evidence/2026-08-10_prek_pr25_window_shapes.log);
[`evidence/2026-08-10_prek_signature_regeneration_diff.log`](evidence/2026-08-10_prek_signature_regeneration_diff.log);
[`evidence/2026-08-10_prek_registry_and_conservation.log`](evidence/2026-08-10_prek_registry_and_conservation.log))

**Addendum (Chore rung, October 2026): the window reaches the local lane
in CI.** Since the `demo-windows` workflow (Arc 7) runs the whole suite
after Path B, a local test that asserted the served registry's mapping
version against the contract file was red for the whole gate-quiet
window: measured at the v1.1.2 bump in the prep sandbox,
`tests/test_query_local.py::test_get_schema_returns_the_registry_declaration`
failed with `assert '1.1.1' == '1.1.2'` on the contract-only tree while
every other lane held, and the Windows legs run that test on any pull
request that touches `tests/`, which the refreshed oracle does. The test
now reads the version from the ownership manifest's
`sources.mapping_contracts`, which is what the committed emission was
generated from and what the built registry declares; the emission tests
in the unit lane hold the emission to the contracts. The packaging rule
above stands at three things. The class: a lane CI gains later can see
a window the lanes it had could not (the F-47 class), so a test that
reads two artifacts reads the two that are built together.

## Serving rung (Phase 5, Session L, August 13, 2026)

### F-22
**A probe in an isolated venv proves the SDK, never the pin.** The mcp
2.0.x pin (D-32) was ratified on probe P1, which ran a toy stdio server in
its own folder and its own virtual environment. It passed: discovery,
type-hint schemas, structured output, and a live Claude Desktop round trip
at 2.0.0. The pin was then unsatisfiable the first time it met this
project's dependency graph. PyAirbyte (D-15) requires `fastmcp>=3.0`;
every published fastmcp 3.x resolves `fastmcp-slim[client]`, which caps
`mcp>=1.24.0,<2.0`. `uv add "mcp>=2.0,<2.1"` therefore fails to resolve
against `airbyte>=0.53`, and no version of either package escapes it.
Root cause, and the rule it earns: a probe run outside the project
environment answers "does this library work," which is a different
question from "does this pin resolve here." Any future dependency probe
resolves inside the project, never beside it.

The recorded fallback holds and costs almost nothing. `mcp>=1.28,<2`
resolves 1.29.0, and every mechanism the serving spec relies on was
re-measured there before Amendment D bound: protocol `2025-11-25`,
identical to 2.0.0; a concrete TypedDict return produces an `outputSchema`
and structured content while a bare `dict` return produces neither,
reproducing the P1 finding exactly; `FastMCP.run`,
`StdioServerParameters`, `stdio_client`, and `ClientSession` all present.
One name changes: the server class is `FastMCP` from
`mcp.server.fastmcp`, where 2.0 exposed `MCPServer` from `mcp.server`.

One uv behavior is recorded with it. `uv add "mcp>=1.28,<2"` alone
resolved 1.28.1, the version already captured in `uv.lock` transitively
through airbyte: uv prefers a locked version that still satisfies a new
constraint rather than upgrading it. A resolution from an empty
environment lands on 1.29.0, so the deliberate pin requires
`uv lock --upgrade-package mcp`. A pin recorded from the first number uv
printed would have been an artifact of the lock, not a decision.
([`evidence/2026-08-13_sessionL_mcp_pin_conflict.log`](evidence/2026-08-13_sessionL_mcp_pin_conflict.log))

### F-23
**At transaction grain the category dimension is 1:1 with the fact by
construction; content addressing there buys identity and change
detection, not compression.** Observed at the Session L live checkpoint
and measured against the committed demo artifact:
`fact_rows 44721 · dim_rows 44721 · distinct dim_hash_id 44721`. The
mechanism is the gold spec's own transaction-grain clause: the mapping
contract declares a degenerate identifier (`line_identity`,
canonical-key v2 of `invoice_id, stock_code, quantity, unit_price`)
carried inside the dimension payload so content keys stay unique.
Rule-13 payload hashing (D-18) then makes `dim_hash_id` inherit that
uniqueness transitively: every fact row mints exactly one dimension row.
The dedup content addressing buys elsewhere in the same star is real and
measured (`dim_timeframe_values` carries 2,004 rows for 44,721 facts,
`dim_source_values` and `dim_run_values` one row each), and the category
group deliberately spends it, because the alternative the spec names is
worse: without the identifier, the composite hash key silently collapses
duplicate rows. Two consequences for consumers, stated in the spec's
*Reading the star* section: `line_identity` is a row fingerprint, not a
business key (a restated measure mints a new identity with nothing
linking old to new, and `lookup_record`'s derived-identity path rides
exactly that key), and the fact-to-dimension hash join buys
addressability rather than compression at this grain.

**Position (documented, not changed).** This is the designed trade at
transaction grain, now stated where a reader will look. The
alternative (relocating `line_identity` out of the dimension manifest
onto the fact as a true degenerate dimension, restoring dedup to the
category group) is a mapping-contract amendment plus a regeneration
that moves the signature-test evidence base. Banked as a post-tag
decision candidate, not rushed to beat a release.
([`evidence/2026-08-14_sessionM_star_key_semantics.log`](evidence/2026-08-14_sessionM_star_key_semantics.log))

### F-24
**`fact_hash_id` is a measure-payload content address, never a row
identifier.** Measured against the committed demo artifact:
`fact_rows 44721 · distinct fact_hash_id 2041 · distinct
fact_col_hash_id 1`. Rule-13 hashing covers the measure payload alone,
so every line with the same quantity and price collides by design:
2,041 distinct measure payloads across 44,721 rows.
`COUNT(DISTINCT fact_hash_id)` is therefore wrong as a row count by
95%, and the column name invites exactly that query, the
highest-probability misread in the model. Row identity at transaction
grain is the full composite key (`fact_hash_id`, `source_hash_id`,
`timeframe_hash_id`, `dim_hash_id`), or `line_identity` inside the
dimension payload; honest row counts are `COUNT(*)` on the fact or
`COUNT(DISTINCT line_identity)` through the typed view. The counting
rules now live in the gold spec's *Reading the star* section, beside the
keys they govern.

**Position (documented, not changed).** The composite-key design stands
(D-18, D-19); the exposure is the name. A rename (`measures_hash_id` or
similar) is an engine-and-contract change with a full regeneration,
banked with the F-23 candidate as one post-tag decision item, alongside
a registry-context enrichment so the `country` meaning string says what
the signature test asserts, which a consumer reaching gold only through
MCP currently cannot learn.
([`evidence/2026-08-14_sessionM_star_key_semantics.log`](evidence/2026-08-14_sessionM_star_key_semantics.log))

### F-25
**A demo artifact named for the schema it carries collides with its own
catalog, and two-part `gold.<x>` SQL fails as ambiguous at DuckDB
1.4.3.** A directly opened database takes its catalog name from the file
stem, so `demo/gold.duckdb` opens as catalog `gold` holding schema
`gold`, and every two-part reference, SELECT and CREATE alike, raises
`Ambiguous reference to catalog or schema "gold"`. Found live at Session
M's export implementation, before anything merged: the exporter could
not build the artifact as specified (the plain `gold.` view re-anchor
fails to bind inside the colliding catalog), and four of the five
serving tools fail through the unmodified query module, which renders
relations two-part by design. Three-part `gold.gold.<x>` works, and the
same file served through an ATTACH alias works, which is exactly why
nothing caught this earlier: the export replay was probed through an
ATTACH alias in a sandbox, and the live serving checkpoint ran against
the working warehouse, whose catalog is `metricmine`. Two individually
probed halves, never probed through each other: the F-22 class at the
artifact boundary. The remedy is Amendment E (Record 006): the committed
artifact is `demo/demo.duckdb`, whose catalog collides with nothing. The
plain `gold.` re-anchor then binds on a direct open and under any attach
alias, and natural two-part SQL works on every serving path, measured
on the Mac and reproduced clean-room by the Architect before the
amendment bound. The probe rule this mints: an artifact is proved by
opening it exactly the way its consumer opens it, never only through a
different access path.
([`evidence/2026-08-14_sessionM_demo_catalog_collision.log`](evidence/2026-08-14_sessionM_demo_catalog_collision.log))

## Agent rung (Phase 6, pre-N prep, August 21, 2026)

### F-26
**The frozen mapping-contract schema is not a structured-outputs
schema.** The engine spec and the schema's own description said the
gold mapping proposer would emit against
`docs/spec/engine/mapping-contract.schema.json` verbatim via
`output_config.format`. Measured at anthropic 1.0.0 against the GA
structured-outputs documentation: the API's JSON Schema subset excludes
`oneOf`, `allOf`, `if/then/else`, `contains` and its counts, `pattern`,
`propertyNames`, and `anyOf` beyond nullable type arrays, and the SDK's
`transform_schema` rejects the frozen schema outright (`ValueError:
Schema must have a 'type', 'anyOf', 'oneOf', or 'allOf' field.`) because
it carries typeless and boolean subschemas. Every composition keyword the
frozen schema is built from (the grain and identifier `oneOf` variants,
the provenance-key `contains` rules, the per-key `if/then`, the
identifier `pattern`s, the aggregation `propertyNames`, the reserved-name
`not`) is unexpressible to the grammar compiler. The remedy is a
projection, not a schema change: each proposer emits against a flat
proposal schema under `docs/spec/agent-layer/` (every property required,
every enum typed, variants flattened into a discriminator plus sibling
arrays the validator holds consistent), and the frozen schema validates
the rendered ODCS document with all of its constraints. Measured the same
day: the mapping proposal schema passes `transform_schema` unchanged at 0
optional and 0 union parameters against limits of 24 and 16; a proposal
mirroring mapping v1.1.0 renders to a document the frozen schema accepts
with first-class elements equal; a planted hallucinated column is caught
by groundedness, not by any schema. The class is F-22 and F-25 again: a
capability verified in isolation (July: "GA structured outputs") against
an artifact never fed to its actual consumer. Probe rule, restated: prove
the artifact through the path its consumer takes.
([`evidence/2026-08-21_preN_probe_transcript.md`](evidence/2026-08-21_preN_probe_transcript.md),
[`evidence/2026-08-21_preN_probe_schemas.py`](evidence/2026-08-21_preN_probe_schemas.py),
[`evidence/2026-08-22_sessionN_probe_p3_live.log`](evidence/2026-08-22_sessionN_probe_p3_live.log))

### F-27
**`datacontract dbt sync` 1.0.12 creates the properties file for a
contracted model that has none, with exact DuckDB data types.** The
repository's evidence had only ever shown sync updating files in place,
and the planning review concluded the human still authors the whole
file. Measured twice in the adoption lab, once from a clean slate: for a
hand-written silver model with a contract and no properties file, sync
created `<model>.yml` carrying the model name, the contract's table
description, `config.meta.datacontract_cli.contract_id`, and every column
with the contract's physicalType as `data_type` (VARCHAR, DATE, BIGINT,
HUGEINT, DECIMAL(38,2)), plus warn-severity `not_null` data_tests per
required column. It wrote neither `config.contract.enforced` nor
`constraints` (grep count 0); those two keys remain the human's (rules 5
and 11, Amendment J). This is the opposite of F-02's `export` scaffold,
which emits generic types: sync writes the contract's exact types, and
gate 2 then enforced the model at HUGEINT and DECIMAL(38,2) data types
(PASS=9), caught a dropped column (`missing in definition`), and caught
a drifted type (`INTEGER | BIGINT | data type mismatch`). Sync reached
its fixed point with the two hand edits preserved (`updated 0 YAML
files`). A naming nit the same run exposed: a rule's `description`
becomes the generated test's file name, so rule descriptions must be
stable prose and evidence sentences stay in the proposal record.
([`evidence/2026-08-21_adoption_lab_transcript.md`](evidence/2026-08-21_adoption_lab_transcript.md),
[`evidence/2026-08-21_adoption_lab_sync_creates_properties.log`](evidence/2026-08-21_adoption_lab_sync_creates_properties.log))

### F-28
**The contract-before-model window admits optional additions and rejects
required ones at gate 3.** D-08 orders a shape change as contract PR
first, implementation PR after. CI had proven gate 3 tolerates a contract
whose model does not exist yet, never an amended contract adding a column
to an existing model. Measured on `silver_invoice_lines` amended to
v1.2.0 with the model and its committed properties file unchanged: adding
an OPTIONAL column is green across all three gates in CI's order (build
on the committed properties file passes; sync adds the column to the
workspace copy; 11 tests pass), and a build against that synced file then
fails with `invoice_day | DATE | missing in definition`, which is exactly
the model PR's job. Adding a REQUIRED column is red at gate 3: the
generated `not_null` test references a column the model does not produce
(`Runtime Error: "invoice_day" not found`). The executable form of
D-08's order is therefore a two-step amendment for required additions:
add as optional, land the model, then tighten to required in a second
contract version. The amend stance (D-35) proposes additions as optional
with a declared follow-up change.
([`evidence/2026-08-21_adoption_lab_transcript.md`](evidence/2026-08-21_adoption_lab_transcript.md))

### F-29
**A governing-contract version bump carries its compiled-context refresh
in the same PR; the F-28 window closes at the D-30 freshness gate.** The
first landed amendment (silver_invoice_lines v1.1.1, PR #99) proved the
ordering: the engine reader fails closed when the committed
compiled-context artifact cites an older source version than the tree
(`run make context`, D-30 by design), and four CI emission tests enforce
it, so a contract-only PR cannot go green, while the refresh cannot be
generated before the contract lands. No separate-PR ordering keeps every
merge green. Measured on the neutral v1.1.1 amendment: the whole cascade
is three metadata lines. `make context` minted v0004 differing from v0003
in exactly one line (the silver source version); `make regen` landed only
the ownership manifest's compiled_context pointer, with all 24 model
files unchanged; the golden manifest fixture followed by the same line;
the demo digest was untouched. Rule 6 stands: `context/compiled/`
artifacts and the ownership manifest are governance metadata under D-30
and D-09, not transform changes, so the amendment PR carrying them stays
a contract change with its derived downstream record. The model-plane
half (the properties re-pin and the version-named generated tests) still
lands after, as its own PR (D-08's order; measured at PR #101).
([`evidence/2026-08-26_sessionQ_amend_live.md`](evidence/2026-08-26_sessionQ_amend_live.md),
[`evidence/2026-08-26_sessionQ_amend_live_record.json`](evidence/2026-08-26_sessionQ_amend_live_record.json))

## Toolchain rung (Arc 1 prep, August 28, 2026)

### F-30
**dbt 1.12 lands clean on the emitted project, and the line brings a
lock-pinned binary the register must name.** Measured at the Arc 1 prep
against main 0708240: dbt-core 1.12.3 with dbt-duckdb 1.11.0 co-resolves
against the committed lock on the first try (`uv add --no-sync`, the P1
pattern) with airbyte, anthropic, mcp, and duckdb untouched, and the
full gate re-proof at that state lands every lane (411 passed, 52
deselected, 13 warnings; 240; 8 passed, 232 deselected; the scan module
11), the build (PASS=109; the Done line gains a REUSED=0 field at 1.12
and nothing in the repository couples to the line), the adoption scan
(13 models, 12 skip_engine_owned, 1 in_sync, queue Empty, the plan body
byte-identical to head's), gates 1 through 3 (sync writes zero YAML;
85 plus 11 tests), zero deprecations under --show-all-deprecations, and
the D-33 digest unchanged. datacontract-cli 1.0.12 needs nothing: its
tool environment carries no dbt, and `datacontract dbt test` shells out
to the project's dbt and reads run_results.json (F-04, F-09). The
require-dbt-version mirror in transform/dbt_project.yml refuses the new
line until edited, as designed. The line adds two dependencies:
metricflow, and dbt-core-experimental-parser at a pre-release
(>=2.0.0b1), published as a download-at-install source distribution
whose build step fetches a platform wheel from GitHub releases and
verifies it against the sha256 the sdist carries; uv.lock pins the
sdist by hash, so the chain is deterministic, and the install adds a
150 MB binary to the environment (49.9 MB compressed on the wire). The
rule that earns: a pin's surface is whatever the lock resolves, and a
pin amendment names every new install-time source, not only the
package that asked for it.
([`evidence/2026-08-28_arc1_prep_probe_transcript.md`](evidence/2026-08-28_arc1_prep_probe_transcript.md), sections 2 through 5; [`evidence/2026-08-28_arc1_gate_reproof.md`](evidence/2026-08-28_arc1_gate_reproof.md), the Mac re-proof)

### F-31
**The v2 parser gate is parse-only for a contract-enforced project; the
beta engine itself builds it.** At dbt-core 1.12.3 with
dbt-core-experimental-parser 2.0.0b2, `dbt parse --use-v2-parser` passes
clean on the emitted project (109 nodes, no warnings, 834 ms in the
prep sandbox), and `dbt build --use-v2-parser` fails on every
contract-enforced model: the delegated manifest serializes column
constraints with warn_unenforced and warn_unsupported as null, and
dbt-adapters' constraint parser rejects them (`Could not parse
constraint`; PASS=2 ERROR=8 SKIP=99). Every contracted model here carries
not_null constraints (rule 5), so at this pairing the flag can gate
parsing and nothing else, which is the low-risk probe dbt Labs documents
it as (the 1.12 guide: a beta parser whose manifest may differ in edge
cases; dbt-core #16010 records the same manifest-copy family).
Separately, dbt Core 2.0.0-beta.2 in an isolated environment parses and
builds the emitted project unchanged, 109 of 109, and its warehouse
reproduces the D-33 digest with the 1.12 gate-3 tests green over its
relations; the beta's PyPI source distribution omits the
mashumaro[msgpack] dependency its wheel declares, and its DuckDB driver
arrives through the ADBC driver manager from public.cdn.getdbt.com on
first use (measured with the pinned duckdb 1.4.3 wheel as the driver
where that host was unreachable). The deferral stands on evidence rather
than caution: the engine, the contracts, and the emitted models need no
change for v2; the toolchain around it is not yet stable.
([`evidence/2026-08-28_arc1_prep_probe_transcript.md`](evidence/2026-08-28_arc1_prep_probe_transcript.md), sections 6 and 7; [`evidence/2026-08-28_arc1_gate_reproof.md`](evidence/2026-08-28_arc1_gate_reproof.md), the Mac probes)

## SDLC rung (Phase 8 prep, August 28, 2026)

### F-32
**A prose working-tree rule has no deterministic backstop in the default
permission flow; a PreToolUse hook is the check that sees every call.**
Observed at the Arc 1 sitting (August 28, 2026): during a driver hunt,
Claude Code ran `find` over the home directory and `~/Library` against
the CLAUDE.md Conventions rule, with no permission prompt, because
`find`, `ls`, `cat`, `grep`, and a fixed set of other commands are
built-in read-only commands that run unprompted in every permission
mode, and the set is not configurable. Read and Edit deny rules match
paths by pattern and cannot say "outside the project root"; the sandbox
is opt-in and OS-level. A PreToolUse hook runs before the permission
prompt for every tool call, sees the tool input, and can deny it with a
JSON decision, so it is the one local check that sees those calls.
Measured at the Phase 8 prep: the working-tree guard
(`.claude/hooks/working_tree_guard.py`, wired by `.claude/settings.json`)
denies a Bash command naming the home directory, a parent climb out of
the tree, a `/tmp` write, and a Read, Edit, or Write outside the root,
and passes in-tree work and system toolchain paths, in 40 subprocess
tests of the script (the CI lane rises from 411 to 451 tests) and in one
end-to-end run of Claude Code 2.1.251 in which the deny reached the
model (`Hook PreToolUse (working-tree guard) returned
permissionDecision: deny`). A project hook committed in
`.claude/settings.json` applies to a clone once its owner trusts the
folder, which the trust dialog lists, and to headless runs; a session
opts out with `--settings '{"disableAllHooks": true}'` or `--bare`. The
guard reads command text, never a subprocess, so the prose rule keeps
its line.
([`evidence/2026-08-28_phase8_prep_probe_transcript.md`](evidence/2026-08-28_phase8_prep_probe_transcript.md))

### F-33
**A working-tree guard must allow the tool's own state and a runner's
action directory; the prep's stdin cases could not see either.** Observed
at the Phase 8 sitting (August 29, 2026), after the guard shipped and
before the first action-prepared pull request merged. Four false positives,
each measured live and each fixed by an allowance a subprocess test now
pins: (1) plan mode writes its plan file through the Write tool under the
user's Claude directory, so the guard denied entering plan mode; the fix
keeps plan files in the tree (`plansDirectory: .claude/plans`, gitignored).
(2) Claude Code reads and writes its auto-memory directory through the
file tools; the guard allows that documented directory for the file tools
only, never for Bash. (3) A commit body or a sed expression whose token
opens with a slash (`/contract-review`, `/^$/d`) tokenized as an absolute
path; a slash-opening token is now a path only when its first segment
names something on disk. (4) On a GitHub Actions runner the Claude Code
GitHub Action's push helper lives beside the checkout under the runner's
`_actions` directory, pre-approved by the action as `Bash(git-push.sh:*)`,
so the first action run (33253883455) applied issue #74's edits, committed,
and could not push; the guard now allows `GITHUB_ACTION_PATH`,
`RUNNER_TEMP`, and the work directory's `_actions` and `_temp` on a runner
and nothing more, and off a runner nothing changes. The subprocess suite
grew from 40 to 55 cases (the CI lane from 451 to 466), and the class the
guard exists for still denies: a `find` over the home directory. The rule
this mints for every further hook (D-37): measure the tool's own
behaviors, its plan files, its memory, and a runner's plumbing, before
shipping a guard around them, because stdin cases only model the calls
their author imagined.
([`evidence/2026-08-29_phase8_exit.md`](evidence/2026-08-29_phase8_exit.md);
[`tests/hooks/test_working_tree_guard.py`](../../tests/hooks/test_working_tree_guard.py))

## Incremental rung (Arc 5b prep, August 31, 2026)

### F-34
**Contracted incremental models require `on_schema_change` at dbt 1.12.**
Observed at the Arc 5b prep (August 31, 2026), on the first incremental
build of the emitted star: dbt-core 1.12.3 refuses to run a contracted
model materialized as incremental with the default `on_schema_change:
ignore` ("Models materialized as incremental with contracts enabled must
set on_schema_change to 'append_new_columns' or 'fail'"). The engine
therefore emits `on_schema_change='fail'` on every incremental config
line, and `fail` is the right value here by design, not just by
requirement: a shape change must arrive through a contract amendment and
a regeneration (D-08, D-09), never silently at build time. The
uncontracted mart carries the same setting for the same reason.
([`tests/test_engine_emission.py`](../../tests/test_engine_emission.py),
the D-38 mode tests; the emitted config lines under
[`transform/models/gold/`](../../transform/models/gold/))

### F-35
**Sync carries jinja var guards in quality-rule SQL verbatim into the
generated singular tests.** Probed at the Arc 5b prep (August 31, 2026)
before D-39 bound: a quality rule whose query carries
`{% if var('mm_batch_floor', none) is not none %} ... {% endif %}`
survives `datacontract dbt sync` at 1.0.12 byte-verbatim inside the
generated singular test, and dbt compiles both branches: with the var
unset the guarded predicate is absent from the compiled SQL and the test
runs in its full-table form; with `--vars` passing a floor, the compiled
SQL carries the bound `captured_at >= TIMESTAMP` predicate. The F-19
lesson (sync passes `{{ ref() }}` through) extends to arbitrary jinja,
which is the mechanism the D-39 batch scope stands on: one contract, one
test set, the scope switched by a declared var, and `make audit-gold`
the unscoped run.
(The guarded rules in
[`contracts/gold_unified_event_star.odcs.yaml`](../../contracts/gold_unified_event_star.odcs.yaml);
the compiled forms under dbt's target directory on any `--vars` run)

## SDLC rung, continued (Arc 4 execution, September 2, 2026)

### F-36
**Under `uv run`, `shutil.which("uv")` finds the venv's locked uv
package, not the operator's uv.** Observed at the Arc 4 execution
(September 2, 2026): PyAirbyte's dependency set pins a `uv` PyPI package
(0.8.24 at airbyte 0.53.2), the project venv's `bin` leads PATH under
`uv run`, and doctor's uv line reported 0.8.24 on every machine (the Mac
runs uv 0.11.28; the sandbox 0.8.17). No gate depended on it; the bug
form's environment block would have carried the wrong uv. uv exports its
own path to the child process as `UV`, so doctor reads
`os.environ.get("UV") or shutil.which("uv")` since #151. The class:
anything that asks the venv's PATH about the toolchain that manages the
venv gets the venv's answer.
([`scripts/doctor.py`](../../scripts/doctor.py);
[`evidence/2026-09-02_arc4_exit.md`](evidence/2026-09-02_arc4_exit.md))

### F-37
**The devcontainer installs uv unpinned at create.** The post-create
command runs `python3 -m pip install --user --no-cache-dir uv`, so a
Codespace resolves the newest uv on the day it is created; the locked
toolchain is pinned by `uv sync --frozen` regardless, so the variance is
in the manager, never in what it installs. Recorded at the Arc 4 execution as the stranger's posture, not
a gate; a future pin is a one-line change if a uv release ever refuses
the lock.
([`.devcontainer/devcontainer.json`](../../.devcontainer/devcontainer.json))

### F-38
**GitHub's GraphQL `Repository.issueTemplates` field lists no YAML issue
forms.** With three valid forms on main after #145, the field returned an
empty list while `contactLinks` and `isBlankIssuesEnabled` read back from
`config.yml` correctly. The chooser page is the receipt for forms; a
scripted check of forms cannot use that field.
([`.github/ISSUE_TEMPLATE/`](../../.github/ISSUE_TEMPLATE/))

### F-39
**`context_registry.loaded_at` and the `captured_at` columns are build
stamps, so committed-versus-fresh demo equality holds at the content
layer only.** The first design of the demo-artifact gate (a cell-level
symmetric EXCEPT against the committed artifact) red-lined on the five
registry rows: `loaded_at` differed on all five, every content column
equal. The shipped gate compares object sets, per-table row counts, and
the D-33 ordered view digests, and says so in its docstring; the typed
views carry no audit column, which is why their digests are stable
across builds and machines.
([`scripts/check_demo_digest.py`](../../scripts/check_demo_digest.py))

### F-40
**uv.lock bytes vary with the uv version that wrote them.** The mcp
1.29.1 refresh at Arc 4 diffed 5+/3- from uv 0.8.17 (two greenlet wheel
rows re-listed beside the mcp move) and 3+/3- from uv 0.11.28. A lock
rung's gate is therefore semantic, only the named package's version
moves, never byte-equal across machines. The F-40 class extends the F-19
lesson (literals break on legitimate bumps) to lock files.
([`uv.lock`](../../uv.lock))

### F-41
**A `pull_request` workflow added by a pull request runs on that same
pull request.** The DCO check gated its own PR (#146 showed three checks
from its first run). Platform semantics, observed live; a check can be
made blocking from the PR that introduces it.
([`.github/workflows/dco.yml`](../../.github/workflows/dco.yml))

## Multi-source rung (Arc 6 prep, September 2, 2026)

### F-42
**The unified event star is category-parameterized: a new category adds
five gold objects and a star contract amendment.** Each mapping contract
emits its own values and columns dimensions, its fact, its mart, and its
view, and the star contract declares those objects by name with their
conservation rules. "New sources add rows, not schema" holds within a
category (a second file of the same shape adds rows) and for the three
shared groups; across categories it is the shape that is invariant, not
the object count. Measured at the Arc 6 prep rehearsal of the family: one category was 13 dbt
models (one silver, twelve gold) and 95 tests at v1.0.0; three
categories are 31 models (nine silver, 22 gold) and 303 tests (67 star
singular tests, 50 silver singular tests, 186 property tests), the star
contract 1,621 lines from 863.
([`docs/spec/gold-unified-event-star.md`](../spec/gold-unified-event-star.md);
the renderer `scripts/render_star_objects.py`)

### F-43
**The timeframe group did not conform across categories as built; the
conformed calendar does.** Before Arc 6 the timeframe payload's key was
the category's own time column name (`{"invoiced_at": ...}`), so two
categories at day grain minted different `timeframe_hash_id` rows for the
same day and the columns dimension carried one manifest per category. The
conformed calendar (D-17 Amendment R) makes the payload `{grain,
period_start}` under one manifest for the whole star. Measured at the
Arc 6 prep rehearsal on the committed family: 166,158 flights and 13,014 weather
rows, both at hour grain, resolve to 4,341 distinct hour keys, and every
one of the 3,439 departure hours is a key the weather category minted
too; with the retail category's 2,004 minute-grain keys the calendar is
6,345 rows under one timeframe columns row and one registry row.
([`src/metricmine/engine/emitters.py`](../../src/metricmine/engine/emitters.py);
the declared-join gate `tests/test_declared_joins.py`, landing with the star at 1.6.0)

### F-44
**Hex hash text and wide JSON payloads dominate the star's storage;
DuckDB block size is not a compacting lever.** At the Arc 6 prep, on
150,000 synthetic flight-like rows, block sizes of 262144, 65536, and
16384 bytes moved the artifact by under 5 percent, and the hashes (two
64-character keys on the fact, one on each dimension and mart row) were
most of the bytes. At the rehearsal of the family, the demo
artifact is 106 MB at three categories from 12 MB at one, and the
flights category is 88 MB of it: its values dimension 59 MB (the
29-attribute JSON payload chosen so the whole unified row reaches the
typed surface), its fact 16 MB, its mart 13 MB; the weather and retail
categories together are under 20 MB. The representation (32-byte BLOB
keys against 64-character hex text; a leaner dimension payload) is a
keying-representation candidate for a later revision, not a compaction
lever the exporter has; the window is code, and a quarter would roughly
halve the artifact.
([`docs/scale.md`](../scale.md); the Arc 6 prep transcripts in project records)

### F-45
**Profile artifacts embed capture-time values, so a full `make profile`
after any re-landing re-mints every table's artifact.** By the
profiler's own determinism rule 5 (observed audit-stamp values are
source data), `_airbyte_raw_id` samples, `_airbyte_extracted_at` bounds,
and silver `captured_at` bounds change with every landing. Measured at
the prep: a re-landing of the unchanged retail sample minted
`bronze.online_retail_ii` v0002 with the data columns identical. The
`--only SCHEMA.TABLE` selector (`make profile ONLY=...`) mints one
target; an artifact mints once, at the sitting where its source lands.
([`src/metricmine/profiling/run.py`](../../src/metricmine/profiling/run.py))

### F-46
**The committed silver profile predates `captured_at`, and the adoption
scan reads it as an amend item.** `profiles/silver.silver_invoice_lines/v0001`
was minted before silver 1.2.0 added `captured_at`, so `make scan` at
v1.0.0 derives `amend` for `silver_invoice_lines` ("captured_at: in
contract, absent from profile"). A fresh profile then disagrees on
`captured_at.required` (contract false, measured true), which is exactly
the F-28 tightening the register deferred. Measured at the prep: the
re-profile plus silver 1.3.0 (`captured_at` required) leaves the queue
empty.
([`src/metricmine/adoption/scan.py`](../../src/metricmine/adoption/scan.py))

### F-47
**The local-marked pytest lane was red at v1.0.0 and nothing in CI could
see it.** Four of 52 failed at the tag: the scan test (F-46), two query
tests (the mart's typed columns end in `captured_at` since D-38; the
mapping version literal 1.1.0 against 1.1.1 since Arc 3), and the server
round trip (`typed_columns[-1]`). CI deselects `local`, so the drift
accumulated across two arcs. The lane is generalized to any category
count at the fan-in and re-run at every sitting close from here on.
([`tests/test_query_local.py`](../../tests/test_query_local.py))

### F-48
**Sync names generated singular tests by contract version, so a bump
leaves the previous version's files in place.** A star contract bump
from 1.4.0 to 1.5.0 wrote 67 files named `gold_unified_event_star__1_5_0__...`
beside the 35 `__1_4_0__` files, which stay until `git rm`; the
regeneration discipline (review the generated set, commit the reviewed
state) covers it and the runbook names the `git rm` step.
([`transform/tests/datacontract_cli/`](../../transform/tests/datacontract_cli/))

### F-49
**The scan reads a measured zero-null column declared optional as a
disagreement, so a new contract declares `captured_at` required from its
first version.** F-28's optional-first rule governs additions to an
existing contract (the model cannot yet populate what the contract
newly requires); a new silver table whose model populates the column
from its first build declares it required, and the scan agrees.
([`src/metricmine/adoption/scan.py`](../../src/metricmine/adoption/scan.py))

### F-50
**The source-file connector's pandas defaults read "NA" as missing.**
OurAirports codes North America as continent `NA` and Namibia as
iso_country `NA`; landed with the connector's default reader options,
32.6 percent of continents (2,951 airports) and 31 countries arrived as
NULL, and a required column failed at the first build. The reader
options `{"keep_default_na": false, "na_values": [""]}` make the empty
string the only missing marker; every code then lands as text. The
class: pandas' default NA list (`NA`, `N/A`, `NULL`, `None`, `NaN`, and
more) eats legitimate codes in any source, so the landing pins it
wherever a code column can collide.
([`config/default.yaml`](../../config/default.yaml);
[`docs/spec/ingestion.md`](../spec/ingestion.md))

### F-51
**Sync-generated singular tests carry no dependency edge, so a silver
model built from other silver models must name itself through
`ref()` in its quality rules.** `datacontract dbt sync` writes each
quality rule's SQL into a singular test verbatim. With the schema-
qualified form (`silver.silver_flights`) dbt sees no edge, schedules
the test at DAG level zero, and on an empty warehouse runs it before
the unified table exists: twelve `Catalog Error` failures in the first
cold build of the family, invisible on a warehouse that already carried
the tables from an earlier build. The cleanup tables build at level
zero, so their schema-qualified rules (the F-08 louder-red design) keep
passing by ordering; the unified tables build at level one, so their
rules reference `{{ ref('<table>') }}`, the F-19 pattern the star
contract uses, and the generated tests inherit the edge. Every
regeneration cold-builds from an empty warehouse from here on: a
warehouse that already carries the tables cannot show this class.
(`contracts/silver_flights.odcs.yaml` and its generated tests under
`transform/tests/datacontract_cli/silver_flights/`, landing with the unified tables)

### F-52
**YAML 1.1 boolean words as mapping keys parse as booleans.** A
structured custom property whose entry used `on:` as a key (a join
condition) loaded as `True: ...` under PyYAML, and the compiler's
canonical serialization failed sorting a mapping with a boolean key
beside string keys. `on`, `off`, `yes`, and `no` are booleans in YAML
1.1; structured contract values use words outside that set
(`join_condition`), and a loader-side check is not needed once the
key is named safely.
([`src/metricmine/context/compile.py`](../../src/metricmine/context/compile.py))

### F-53
**dbt's partial-parse cache keeps a disabled test disabled across the
F-13 window, so the regeneration build clears `transform/target`
first.** At the star's 1.6.0 rung the contract's C3 rule names two
columns dimensions the regeneration has not emitted yet; dbt disables
the sync-generated test with a WARNING and the cold build ends one test
short (PASS=253). When the regeneration lands the dimensions, a build
that reads `transform/target/partial_parse.msgpack` keeps the test
disabled: PASS=333 with C3 silently absent and `make audit-gold` at 66,
and no warning this time because the cache never re-evaluated the
test. Removing `transform/target` before the build forces a full parse:
PASS=334, audit 67, C3 among them. The rule from here: every cold
build removes the warehouse and `transform/target` together, and a
count one short of the expected total after a contract bump is a
parse-cache symptom before it is anything else.
(`transform/tests/datacontract_cli/gold_unified_event_star/gold_unified_event_star__1_6_0__context_registry__c3_registry_coverage__every_schema_key_p.sql`,
landing with the regeneration)

## Windows rung (Arc 7 prep, September 6, 2026)

### F-54
**The local lint lane fails on a machine without the isolated
`datacontract` tool, so the module skips by name.** The demo guide says
the demo runs without `datacontract-cli`, and Path B ends with
`uv run pytest -q`. On a fresh clone of `cb2cd07` with the tool absent,
that command failed the fifteen tests of `tests/agents/test_lint_local.py`
on a missing executable (`15 failed, 69 passed` in the local lane) while
every other local test passed; with the tool installed the same command
passed all 84. The module now carries
`pytest.mark.skipif(shutil.which("datacontract") is None, ...)` beside
its `local` mark: `69 passed, 15 skipped` without the tool, unchanged
with it. The gates stay CI's, where the tool is installed; a stranger's
closing test run says what it skipped and why instead of failing on a
tool the guide never asked for. The class: a local-lane test that shells
out to a tool the demo path does not require must skip on its absence,
or the demo path's own closing command reports a failure the demo does
not have.
(`tests/agents/test_lint_local.py`, landing with the Windows plumbing)

**Addendum (Chore rung, October 2026): the same class on the warehouse.**
A stranger who runs `uv run pytest -q` after Path A alone, with the
artifact fetched and no warehouse built, gets one failure: measured
`1 failed, 677 passed, 82 skipped` at `a009766` on September 12 and
`1 failed, 692 passed, 67 skipped` at `485f3a5` on October 2 (the
fifteen-test difference is the lint lane above, skipped where the tool
was absent and run where it was present). The failure is
`tests/test_adoption_scan.py::test_the_committed_repository_scans_clean`,
marked `local`, which asserts `in_sync` and reads `needs_build` where its
local siblings skip on the missing warehouse. The demo guide runs the
suite after `make demo` and the contributing guide runs the `not local`
lane, so no documented path shows it; the fix, a skip like its siblings,
is a chore-arc item and lands with its own line here.

### F-55
**A hosted Windows runner proves the command a desktop config launches
over stdio, never the desktop client's click-through.** The Windows
entry the demo guide gives for Claude Desktop
(`%APPDATA%\Claude\claude_desktop_config.json`; the clone's
`.venv\Scripts\python.exe` with `-m metricmine.server`) was written from
the MCP client guide by an author with no Windows machine. What a runner
can measure is the command: `scripts/serve_smoke.py` spawns it the way a
client does (from outside the repository, with the mcp SDK's default
minimal environment, `MM_SERVE_DB` unset) and asserts the server name,
five tools, and three categories, and the `demo-windows` job runs it
after `demo-fetch` on every change to the demo path. What no runner can
measure is the desktop app reading that file and listing the server, so
the Windows desktop step ships documented, not measured, and the guide
says so. This finding closes when a person confirms the step on a
Windows desktop; the confirmation lands here as an addendum with the
date and the Claude Desktop version, and the guide's sentence changes
with it.
(`scripts/serve_smoke.py`, landing with the Windows plumbing; the Claude
Desktop step of [`docs/demo.md`](../demo.md))

**Addendum (October 2, 2026): one report, the step still unmeasured.**
A Windows 10 user ran Path A and Path B (a run dated September 23, 2026)
from a Claude Desktop installed from the Microsoft Store, with the entry
merged into the config file,
and every published number reproduced (247,555 bronze rows, `PASS=334`,
the export digests, `19 tables and 3 views`); the click-through itself,
whether that app lists the server, was not run. This finding stays open
and closes as the entry says, with the date and the app version.

## Windows rung, cycle one (Arc 7 execution, September 6, 2026)

### F-56
**The SDK's asyncio stdio client on a Windows runner never returned from
the first answer larger than the pipe buffer; the smoke now reads the
pipes itself with every wait bounded.** Cycle one of the `demo-windows`
check (run 34032638337, both shells) hung at `scripts/serve_smoke.py` for
the job's whole hour. The server it launched logged `ListToolsRequest`
and `CallToolRequest` within three seconds of the step's start (the pwsh
leg: 12:18:00.7146 and 12:18:00.7184 UTC), nothing followed for 59
minutes, and the job's timeout cancelled the step. The traceback at the
cancellation came from the SDK's `stdio_client`: its stdout reader had
parsed a message and raised `BrokenResourceError` sending it into a
session that had already closed. The smoke as first cut printed nothing
until the SDK's teardown returned, so the log could not name the step.
Measured on Linux against the same server and asset, the three answers
are 2,853 bytes (`initialize`), 6,592 bytes (`tools/list`), and 11,316
bytes (`tools/call list_fact_categories`); asyncio's subprocess pipes on
Windows are named pipes with an 8,192-byte buffer
(`asyncio.windows_utils.BUFSIZE`); the first two answers arrived on the
runner and the third did not. That is a correlation the log supports,
not a mechanism the log shows; the mechanism inside the SDK's client is
unmeasured. The remedy: the smoke speaks the wire protocol itself over
`subprocess.Popen` pipes, one thread blocking on the server's stdout,
a 60-second deadline on every answer, each answer printed with its size
and latency as it arrives, and a bounded shutdown that reports the
server's exit; the mcp package supplies the minimal environment and the
protocol version and nothing else. Measured on Linux: the three answers
in about three seconds and exit 0 in 0.2 seconds after stdin closed;
seven injected faults (a hung tool call, an early exit, an `isError`
answer, a 200 KB answer, CRLF line endings, a notification on stdout, a
server that ignores end-of-file) each named within the deadline. What
the smoke proves is unchanged: the command the desktop config launches
answers with the server name, five tools, and three categories. Claude
Desktop is not the Python SDK's client, so the finding says nothing
about the desktop's own reader; F-55 stays open as before. The class: a
proof script prints each step as it completes and bounds every wait, or
a platform hang hides which step hung and costs the job's whole timeout.
The fixed tree's Windows run is quoted in the Arc 7 exit record; if the
plain reader also stops at the tool answer, this finding reopens on the
server side.
(`scripts/serve_smoke.py`, landing with the smoke's re-cut; the
`demo-windows` run 34032638337)

**Addendum (Windows rung, cycles two and three): the mechanism, measured, and the fix.** The first reading above named the wrong cause. The SDK's asyncio client and the 8,192-byte pipe buffer were a coincidence: the first `list_fact_categories` was simply the first parameterized query in the process. Six probes on `exp/windows-stdio-probe` ruled out the stdout write path (a worker thread, a dedicated writer thread, an inline write), both event loops (proactor and selector), the stdin read mechanism, interpreter buffering, a loop timer, buffered memory streams, and a heartbeat. The `faulthandler` dumps then named the frame: the tool thread stalls inside `list_fact_categories`, at the first parameterized DuckDB query, inside an `import pandas` that DuckDB performs there, at the load of numpy's C extension. Measured off Windows: DuckDB 1.4.3 evaluates `import_cache.pandas.NaT()` for every bound parameter (`python_conversion.cpp`, no guard and no switch), so the first parameterized `execute` in a process imports pandas, and pandas pulls in numpy and pyarrow; literal SQL imports nothing; once the modules are loaded the parameterized query is immediate. On Windows numpy's pinned wheel names its bundled OpenBLAS DLL in the extension's import table, that DLL's constructor runs libgfortran's static initializer, and the initializer preconnects a Fortran unit by calling `fstat(0)`. UCRT turns `fstat` on a pipe into `PeekNamedPipe`, and Windows serializes every request on a synchronous pipe handle behind the request already in flight, which is the SDK reader thread's pending `ReadFile` on stdin. So the import cannot finish until the client sends another line or closes stdin, and every earlier candidate failed because each kept that read pending while the import ran. This is numpy issue 24290, open since 2023, reported from another stdin JSON-RPC server with the same stack. The fix: `src/metricmine/server/__main__.py` imports pandas, numpy, and pyarrow at startup, before `server.run` starts the transport and parks its first read, so the DLL load runs with no read pending. Probe 6 (run 34052236321, windows-latest): the shipped server stalled the tool answer to the poke at 31 s; the same server with the startup import answered the tool call in 47 ms, with no `faulthandler` dump in an import frame. The demo path and the smoke need no change. The class: a native import a request triggers on demand can deadlock behind the transport's own pending read on Windows, so a server loads its on-demand native code at startup, before it parks a read. Two follow-ups stand: removing parameter binding from the three query-module sites would stop DuckDB importing pandas at all (Arc 3), and the serialization is worth reporting upstream to the mcp SDK's blocking stdin reader.
(`src/metricmine/server/__main__.py`, the startup import; the `demo-windows` run and probes 2 through 6 on `exp/windows-stdio-probe`)

### F-57
**A heavily non-ASCII sample fails the source-file connector's check on Windows, which reads the file in the platform's default encoding (cp1252) unless the reader options name one; the ourairports samples declare `encoding: utf-8`.** Two Windows runs of `demo-windows` on PR #184 settled it. With the sample passed as a plain absolute path, five of the six samples checked and landed on Windows and only `ourairports_airports` failed, with the connector's generic "Please check File Format and Reader Options are set correctly" (`source_file/source.py`), not a URL error. A first reading (this finding's prior revision, reverted with #188) blamed the file URL and passed the path as `csv_path.as_uri()`. That was wrong twice over: the plain path already worked for the ASCII-safe samples, and `as_uri()` broke every sample, because the connector opens `file://` plus the scheme-stripped url with `smart_open`, and for `file:///D:/a/...` smart_open opens the literal `/D:/a/...`, a leading slash before the drive letter that Windows refuses (`OSError 22`). The real cause, read from the connector source (`source_file/client.py`, airbyte-source-file 0.3.15): `Client.encoding = reader_options.get("encoding")`, passed to `smart_open.open(..., encoding=...)`; unset, smart_open opens text in the platform's preferred encoding, UTF-8 on macOS and Linux and cp1252 on Windows. `ourairports_airports` carries 1,310 non-ASCII lines (airport names) whose UTF-8 bytes are not valid cp1252, so the decode fails on Windows and nowhere else; the ASCII-safe samples decode under either. The fix: the ourairports reader options declare `"encoding": "utf-8"`, so the connector opens the file as UTF-8 on every platform, a no-op off Windows where UTF-8 was already the default. The class: a text file read without a declared encoding is read in the platform's, and a non-ASCII file then loads on one platform and fails on another. The fixed tree's Windows run is quoted in the Arc 7 exit record.
(`config/default.yaml`, the ourairports reader options; the `demo-windows` runs on PR #184)

## Toolchain rung, continued (v1.1.2 fast-follow, September 9, 2026)

### F-58
**Three keyless download paths built no SSL context, so a python.org macOS
build with an empty OpenSSL trust store failed every fetch before anything
built.** `urllib.request.urlopen` with no `context=` builds one from
`ssl.create_default_context()`, which loads OpenSSL's default verify paths
and nothing else. On the framework CPython 3.12 measured here those paths
are empty: `ssl.get_default_verify_paths()` returns `cafile=None` and
`capath=None`, the `openssl_cafile` it names (`cert.pem` under the
framework's `etc/openssl`) does not exist because the framework's
`Install Certificates.command` was never run, and
`ssl.create_default_context().get_ca_certs()` loads zero anchors. Every
fetch then dies with `CERTIFICATE_VERIFY_FAILED` before anything builds.
Reproduced before the fix branch was cut: with `SSL_CERT_FILE` and
`SSL_CERT_DIR` pointed at nonexistent paths, `make demo-fetch` prints its
downloading line and then fails on the certificate. The three call sites
were `scripts/fetch_demo.py:69` (the release asset, a stranger's first
network call), `scripts/fetch_common.py:55` (the shared `download`, which
fans out to the six source fetch scripts, so a contributor following
`docs/adding-a-source.md` hit the same wall), and
`scripts/fetch_sample.py:52`. Pre-existing since before v1.1.0, and off the
Windows path: `ssl.SSLContext.load_default_certs` reads the system
certificate store on `win32` before it consults either path, so a Windows
machine reports no cafile and no capath and verifies anyway. The remedy: one
shared `metricmine.tls.ssl_context()`, passed at all three call sites, with
certifi declared at a floor in `pyproject.toml` rather than carried
transitively. It **adds** certifi's anchors to the machine's own trust
rather than substituting for them, and the difference is not cosmetic.
`ssl.create_default_context(cafile=...)` takes an `if cafile or capath or
cadata: load_verify_locations(...)` branch whose `elif` holds the
`load_default_certs(purpose)` call, so naming a bundle there skips the
Windows certificate store, the system bundle on Linux, and any
`SSL_CERT_FILE` the operator exported. Measured on a machine whose default
store held 113 anchors: the substituting form kept 109 and lost 54 of the
machine's own, while `create_default_context()` followed by
`load_verify_locations(cafile=certifi.where())` lost none and ended with
163. A corporate TLS-inspecting proxy's root lives in exactly the store the
substituting form discards, so that form would have broken machines this
finding never touched while appearing to fix the one it did; the review
caught it before it shipped, and `tests/test_tls.py` now asserts that
nothing the machine trusts goes missing. Verification is never disabled,
and certifi absent or unreadable degrades to the context urlopen would have
built for itself. `make doctor` gained a `trust store` check that reads
`ssl.get_default_verify_paths()` and the default context's anchor count and
warns when nothing is loaded and no capath could load one lazily. That
second clause is the whole condition: OpenSSL looks a hash up in a capath
on demand, so a capath legitimately reports zero anchors and verifies
fine, while a cafile that reports zero does not. Stating it that way also
catches an `SSL_CERT_FILE` aimed at a file that exists and parses to
nothing, which is the misconfiguration the check's own remedy invites; it
was measured against this repository's README, which the first cut passed.
It reports rather than gates, and the remedy above is what earned that: once the
downloads carry their own bundle a bare store no longer breaks the demo
path, so a failure there would red a machine whose demo runs. The first cut
recorded FAIL, chosen against the pre-fix world and not revisited when the
fix landed in the same branch; measured on the bare Framework Python this
finding was found on, minutes apart in one shell, doctor recorded the
failure and `make demo-fetch` then downloaded 108,277,760 bytes and verified
19 tables and 3 views. The tier is a real gate rather than a label, because
doctor's exit code reaches four consumers and the least documented is the
hardest: `.devcontainer/devcontainer.json`'s `postCreateCommand` runs
`scripts/doctor.py` as the last link of an `&&` chain, so a non-zero return
marks container creation failed. The other three are the `demo-windows`
preflight step, the `Makefile` target, and the task entry point's subprocess
propagation. Its honest limit: a capath that exists but is empty still
passes, because proving the store usable needs a network call doctor is
forbidden to make. The anchor
count is never the sole test either, in both directions, and both were
measured: a capath-only machine loads zero anchors by default and verifies
fine, and a Windows machine loads its anchors from a store neither path
names, so gating on the two paths alone would have failed the
`demo-windows` preflight. The class: a download that does not name its
trust store inherits the interpreter's, and an interpreter that ships
without one turns a first-run fetch into a traceback the reader blames on
the project.
(`src/metricmine/tls.py`, landing with the three call sites; the deferred
item carried forward in the
[Arc 6 exit record](evidence/2026-09-05_arc6_exit.md))

## dbt Core v2 rung (Prep V, October 2026)

### F-66
**dbt Core v2 (`dbt-oss` 2.0.5) parses and builds the project after one
properties-key move, resolves the package hub on every parse and build
unless the package is local, schedules the 24 edge-less generated tests
before their models on a cold build, and ships no DuckDB driver; the
engine arrives as a 63 to 76 MB wheel download at install and the driver
as a CDN download at first run unless the project registers its own.**
Measured October 2 and 3, 2026, in a Linux sandbox on fresh clones at
`485f3a5` and `5827ac1` with the pinned Python `duckdb` 1.4.3 and
`datacontract-cli` 1.0.12, and on October 3 on a macOS 26 arm64 machine
(uv 0.11.28) by a read-only probe script against a scratch clone; the
Mac facts are marked below. The distribution: `dbt-oss` 2.0.5 on PyPI
is a 5,062-byte source distribution (sha256 `1000d181...`) with one
dependency, `mashumaro[msgpack]`; its PEP 517 backend picks the wheel
for the machine's platform from a manifest the sdist embeds, downloads
it from `github.com/dbt-labs/dbt/releases` with `urllib` under the
interpreter's default TLS context, and verifies its sha256. The
installed engine is `dbt/_core.abi3.so` (`_core.pyd` on Windows) and the
`dbt` command is a Python console script that loads it, so a `dbt` run
is a Python process. Five wheels exist, measured from the release
assets (the wheel, then the engine it carries): macOS 10.12 x86_64
(66,535,563 bytes; 195,084,620), macOS 11.0 arm64 (62,804,126;
172,054,112), manylinux 2.28 aarch64 (64,942,384; 186,268,120),
manylinux 2.28 x86_64 (69,112,585; 217,513,944), and win_amd64
(75,887,849; 321,483,776). On the Mac the build step downloaded and
verified the arm64 wheel through a python.org framework CPython 3.12.2
whose certificate bundle was present (`etc/openssl/cert.pem` under the
framework), so the F-58 remedy was not needed there. The lock drops 26
packages (dbt-core, dbt-duckdb, dbt-adapters, dbt-common, metricflow,
dbt-core-experimental-parser, agate, and their dependencies) and adds
one, 210 to 185. The parse: with the hub refused, `dbt parse` fails
before parsing anything (`Failed to get index from
https://hub.getdbt.com/api/v1/index.json`), because v2 resolves
`packages.yml` on every parse and build; with `packages.yml` naming a
local package it prints `Loading packages.yml` and no resolution line,
`dbt deps` symlinks the package into `dbt_packages/` (the engine carries
a copy-fallback event for a platform without symlinks) and writes
`package-lock.yml` in its own form (`- local: vendor/dbt_utils`,
`name: dbt_utils`, a new `sha1_hash`), stable across runs. The one
refusal: `[error] [UnusedConfigKey (dbt1060)]: While parsing config:
Ignored unexpected key "meta". YAML path: columns[9].meta` at
`transform/models/silver/silver_invoice_lines.yml:149`, the
column-level `meta: datacontract_cli: generated: true` that sync 1.0.12
wrote ([F-27](#f-27)); moved under `config`, the project parses in
about a second and the pinned sync leaves the moved key in place
(`updated 0 YAML files` on all 13). Not a refusal: `require-dbt-version:
[">=1.12.0", "<1.13.0"]` parses at 2.0.5 without a warning, so the
range is a declaration under v2 and a refusal under 1.x; the October 2
smoke recorded it as a second refusal and this re-measure corrects it.
The driver: `dbt debug` with nothing registered prints `Failed to load
duckdb driver from name, then failed to load it from the CDN` with the
CDN (`public.cdn.getdbt.com`) refused, so the pip distribution ships no
driver. Registered through `ADBC_DRIVER_PATH` with a manifest naming
the `_duckdb` extension module of the pinned wheel (it exports
`duckdb_adbc_init` and links no libpython; the wheel's own
`adbc_driver_duckdb` module names the same path and entrypoint), `dbt
show --inline 'select version()'` prints `v1.4.3` and the warehouse dbt
writes carries storage version 64 and library `v1.4.3`, the numbers the
published asset carries. The user configuration folder
(`~/.config/adbc/drivers` on Linux) is honored too and
`$VIRTUAL_ENV/etc/adbc/drivers` is not; the project uses the
repository-local route only, so nothing is written outside the clone.
On the Mac, with nothing registered, the driver dbt fetched from the
CDN was DuckDB v1.5.4 (`Debugging connection test: OK`, `version()`
`v1.5.4`) and the file it wrote carried storage version 64 with library
`v1.5.4`; the pinned wheel's `_duckdb.cpython-312-darwin.so` (its `nm`
lists `duckdb_adbc_init`) registered through `ADBC_DRIVER_PATH`
answered `v1.4.3` and wrote storage version 64 with library `v1.4.3`,
taking precedence over the cached CDN driver. The Windows `.pyd` of the
same wheel exports the entrypoint and imports `python312.dll`, which a
`dbt` run has loaded (read from the wheel with a PE reader); whether it
loads as dbt's driver on Windows is measured on the toolchain pull
request's `demo-windows` legs and recorded here by addendum. dbt-autofix
0.22.6's dry run over the project at `5827ac1` (on the Mac) reported
three items: the same `meta` move, the
`require_generic_test_arguments_property` behavior flag, and the
deprecated `target-path` key in `dbt_project.yml`; the move is made by
hand in the toolchain pull request and the other two are backlog,
neither refused by 2.0.5. The build: on a cold warehouse `dbt build`
fails 20 to 24 of the 24 singular tests that name `silver.<table>` by
schema ([F-51](#f-51)'s class, the seven level-zero
silver contracts: nyc_flights 7, nyc_weather 5, ourairports_airports 4,
invoice_lines 2, nyc_airlines 2, nyc_planes 2, ourairports_runways 2),
scheduled from `[1 of 334]` before the models exist; the count is a
race with the models (24 on October 2; 20 and 22 on October 3). `dbt
run` then `dbt test` on the same cold warehouse: 31 models, 303 tests,
twice (D-20 as amended); a warm `dbt build` passes all 334. With the 24
rules rewritten to `{{ ref() }}`, the route D-20's amendment records and
does not take, a cold `dbt build` passes twice. Under v2 the full gate
set lands at its head values: ruff, the unit lane, 13 contracts valid at
1.0.12, the asset fetched and verified, `server: metricmine-gold, 5
tools`, 247,555 bronze rows, the scan's queue empty, the D-33 digest
`PASS` (registry `d431a853...`), the local lane, `make audit-gold` 67
tests, and `datacontract dbt sync` and `dbt test` clean; v2 also writes
its information schema under `transform/target/private/index/` as
Parquet beside the `manifest.json` the contract tooling reads. One more
seam, measured and left as it was: the engine posts anonymous usage
statistics to `p.vx.dbt.com` on every command unless
`DBT_SEND_ANONYMOUS_USAGE_STATS=false`, `DO_NOT_TRACK=1`, or the
profile's `send_anonymous_usage_stats: false` says otherwise (the
engine's strings carry all three switches; the sandbox refused that host
fifteen times during one `make demo` and every command succeeded). The
1.12 line posted to its own collector (`fishtownanalytics.sinter-collect.com`
in `dbt/tracking.py`) under the same default, and the project has never
set the switch on either line; whether to is backlog, not this finding.
The class: an engine that changes who schedules, who downloads, and who
resolves is pinned at every one of those seams, or it is not pinned.
(`pyproject.toml`, `transform/dbt_project.yml`,
`transform/packages.yml`, `transform/vendor/dbt_utils/`,
`src/metricmine/driver.py`, `scripts/doctor.py`; the toolchain pull
request)

## Chore rung (the Arc 8 audit and the September 17 probes, minted October 2026)

### F-59
**The Git for Windows installer asks for elevation, and winget's user
scope does not avoid it, so "no step needs administrator rights" held
only after the two installs.** The demo guide and the site's Get started
page said that no step needs administrator rights. Read from the vendors'
trackers on September 11, 2026, and not
run here (no Windows machine took part in the audit): the Git for Windows
installer requests elevation at launch, and the winget manifest's
`--scope user` does not avoid it (microsoft/winget-pkgs issue 369735,
open, filed May 6, 2026); on macOS the Command Line Tools install that a
bare `git` triggers is an install too. The true form landed with #200: uv
installs per user, and nothing after the two installs needs administrator
rights; the Windows troubleshooting group names the portable build of git
(a self-extracting archive with `cmd\git.exe` on the PATH, stated from the
Git for Windows download page) for a machine where that approval is not
the reader's to give. The one Windows recipient of the September wave did
not report on the prompt, so the claim stands as read from the vendor
until a person confirms it on a managed machine; the confirmation lands
here as an addendum. The class: a claim about what a machine will ask of a
stranger is scoped to the steps the project controls, and a step the
project does not control is named with where its behavior was read.
(`docs/demo.md`, the git bullet under What you need and the Windows
troubleshooting group, landed with #200)

### F-60
**`make demo` reaches the Airbyte connector registry unless
`AIRBYTE_OFFLINE_MODE=1` is set, and nothing a stranger runs sets it;
behind a filter the first landing stops at the registry with PyAirbyte's
own error.** D-27 records that CI lands bronze offline ("no Airbyte
registry dependency, no telemetry"), and the devcontainer, both
workflows, and every prep probe export `AIRBYTE_OFFLINE_MODE=1`; the
Makefile, `src/metricmine/tasks.py`, the demo guide, and the README did
not, so the measured path and the documented path differed. Measured on
September 12, 2026, on a fresh clone in a sandbox whose egress refused
`connectors.airbyte.com`: online, `make demo` stopped at
`AirbyteConnectorRegistryError: Failed to connect to the connector
registry` before landing a row, and the message names
`AIRBYTE_OFFLINE_MODE` itself; with the variable set, the same clone
landed 247,555 rows into bronze and built `PASS=334`. Re-measured on
October 2 in a sandbox with the same refusal: the offline landing again
247,555 rows. On an open network the registry answers and the online run
proceeds, as the Mac walks of Arcs 6 to 8 showed; the Windows runner sets
the variable and never exercises the online path. The documented remedy
is the troubleshooting entry #202 added. The better fix, `tasks.py`
setting the variable for the landing step unless the environment already
sets it, so the laptop path is the measured path, amends D-27 and lands
by its own documentation pull request first. The class: a build step
whose network reach CI suppresses by configuration reaches the network on
a stranger's machine unless the project's own entry point suppresses it
the same way.
(`src/metricmine/tasks.py` and the Makefile's `ingest` target, unchanged;
the troubleshooting entry in `docs/demo.md`, landed with #202)

**Addendum (October 2, 2026): the dbt package hub is the second registry
a filtered network refuses.** `make demo`'s package step, `dbt deps`,
reaches `hub.getdbt.com` for `dbt-labs/dbt_utils` 1.3.3, and behind a
proxy that allows github.com and refuses the hub it stops with
`HTTPSConnectionPool(host='hub.getdbt.com', port=443): Max retries
exceeded ... 403 Forbidden`, emptying `transform/dbt_packages/` on the
way. Measured in
this project's own sandbox on September 12 and 17 and October 2, 2026,
and reported from a Windows user's cloud sandbox run of September 23.
Either
route installs the same tag (`ef562bac`) from GitHub with no hub
contact, measured on October 2: the package placed by hand from its
tag, after which `dbt parse` and `dbt build` find it and `dbt deps` is
left out of the run, or `transform/packages.yml` pointed at the git
form for the session, after which `dbt deps` installs it and rewrites
`package-lock.yml` until both files are restored. The demo guide
carries both. Vendoring the package, which would also remove the hub
fetch dbt v2 makes on every parse, is a decision for the register and
is not taken here.

### F-61
**`make export-demo` and `make demo` rewrite the committed digest manifest
to the local build, and `make demo-fetch` then refuses until the manifest
is restored from git.** Measured on September 12, 2026, on Linux and
re-measured on October 2 at `485f3a5`: after Path B, `git status
--porcelain` prints ` M demo/demo.digest.json` (the export rewrote the
artifact block to `release: null` and the local file's sha256 and size),
and `make demo-fetch` prints `this tree has no published demo artifact
yet (the manifest names no release); build it locally: make demo` and
exits 2, until `git checkout demo/demo.digest.json`. The export re-measures
both blocks from the build; at head the content block comes out
unchanged, so the D-33 gate still holds the build to the published
content, and the `demo-windows` workflow already restores the manifest
between Path B and its manifest gate for this reason. The guide
said the export "writes the manifest beside it" and the contributing guide
said "there is nothing to restore afterwards"; #202 corrected both and
keyed a troubleshooting entry to the refusal. The design question,
whether the fetch should read the committed manifest (`git show
HEAD:demo/demo.digest.json`) when the working copy names no release, is
a D-33 matter and is not decided here. The class: a documented build step
that rewrites a committed file leaves the next documented step reading
the rewritten one, and the guide has to name the restore between them.
(`src/metricmine/export_demo.py` and `scripts/fetch_demo.py`, unchanged;
the Path B notes and the troubleshooting entry in `docs/demo.md` and the
sentence in `CONTRIBUTING.md`, landed with #202)

### F-62
**A governed amendment corrected a silver column's description and left
its restatement in the mapping contract stale; the served context carried
both sentences, and no gate or review item read the pair.**
`silver_invoice_lines` v1.1.1 (#99, August 26, 2026) corrected `quantity`
from "negative only on cancellation lines" to the measured truth:
negative values occur on cancellation-invoice lines and on zero-unit-price
stock-adjustment lines, so consumers must not infer cancellation from a
negative quantity alone. `gold_invoice_lines_mapping` v1.1.1 (line 98)
restated the column in its own words, "Units on the line; negative only
on cancellations.", and the amendment did not touch it. Measured on
September 17 and re-measured on October 2, 2026, on both the published
v1.1.1 asset and a Path B build at `485f3a5`: of 44,721 rows in
`gold.mart_invoice_lines_typed`, 1,103 carry a negative quantity, 90 of
them on lines that are not cancellations, every one of the 90 at
`unit_price = 0`. The compiled context serves the mapping sentence as
`meaning` and, because the silver text differs, the silver sentence as
`source_meaning`, so a consumer's agent reads two sentences that cannot
both be true and nothing tells it which is the claim to check. The class,
measured at head: 9 served field pairs where a mapping contract restates
a silver column in other words (all nine in the retail mapping; every
other served field is a verbatim copy of silver), and 29 pairs where a
silver contract restates a same-named upstream silver column in other
words (`silver_flights` 19, `silver_airport_weather` 10, matched by
column name on both sides; renamed columns are not counted), where no
second sentence is served at all. Replayed on September 17 by a read-only
probe
over `git show` across every first-parent commit on main that touches
`contracts/`: three changed a silver column's description, one of them
with a restatement in place, and that one (#99) is the stale case; the
history holds no commit that could show a false flag, so the replay shows
that a deterministic check would fire, not how often it would be wrong.
The correction is a contract change in its own pull request with its
compiled-context refresh (D-08, F-29) and a regeneration pull request
behind it (D-09); a stranger meets the corrected sentence only at the
first release that carries a refreshed asset, and every earlier asset
serves the stale one. The cure for the class is item 10 of the contract
review checklist, landing with this finding; a deterministic report line
on the pull request would amend the scan's text under D-35 and is not
built. The class: a description that another contract restates in other
words is two sentences under one approval, and an amendment that corrects
one must read the other.
(`contracts/gold_invoice_lines_mapping.odcs.yaml` line 98 at `485f3a5`;
`.claude/skills/contract-review/SKILL.md` item 10, landing with this
finding)

### F-63
**A committed `.mcp.json` is loaded without asking by every non-interactive
Claude Code session, so its launch line installs nothing and fails fast on
a clone that was never synced: exit 1 in well under a second, a bare
virtual environment and no package.** Claude Code's documentation (read
October 2, 2026) says it asks before using a project-scoped server in an
interactive session and that `claude -p` runs, Agent SDK sessions, and
cloud sessions load project-scoped servers without asking; the
claude-code-action's documentation says a repository `.mcp.json` is
detected and used automatically, with its tools still subject to
`--allowedTools`, and that the action sets `enableAllProjectMcpServers`
to `true`. So a committed file is a launch line that runs wherever an
agent opens the repository, this repository's own `claude.yml` included.
The committed entry, written by `claude mcp add --scope project
metricmine-gold -- uv run --no-sync --project '${CLAUDE_PROJECT_DIR:-.}'
python -m metricmine.server`, was measured on Linux with Claude Code
2.1.288 and uv 0.11.32. On a fresh clone with no `.venv`, the line exits 1
at once with `Error while finding module specification for
'metricmine.server' (ModuleNotFoundError: No module named 'metricmine')`
after creating a bare virtual environment (uv's `_virtualenv.pth`,
`_virtualenv.py`, and their `__pycache__`, no package); Claude Code's
own health check
reports the server as failed to connect (`CONNECTION_CLOSED: Connection
closed`). On a synced clone with no demo artifact present it reports
`√ Connected`, a vendor-neutral client from outside the repository gets
`initialize` (2,879 bytes) and five tools, and a tool call then returns
`isError` with the fail-closed message naming `make demo-fetch`, `make
demo`, and `MM_SERVE_DB`. Claude Code spawns the project server with the
project root as its working directory and sets `CLAUDE_PROJECT_DIR` to
that root in the server's environment, while the
`${CLAUDE_PROJECT_DIR:-.}` form in the file expands to `.` because the
variable is unset in Claude Code's own environment; `.` is the project
root by working directory, so both halves resolve. Spawned from outside
any project, the same line exits 1 in well under a second with uv's `--no-sync has no
effect when used outside of a project` and the same missing module, and
installs nothing. The unsynced failure names no remedy and nothing in the
launch line can add one, so the contributing guide and the demo guide
name `uv sync` beside the file. What the repository's own Action does
with the file is measured on the pull request that commits it and is
recorded here by addendum. The class: a configuration file an agent host
executes on sight is a launch line that must be safe to run on a clone
nobody prepared, which means it installs nothing and fails fast when the
clone is not ready.
(`.mcp.json`, landing with this finding; `scripts/serve_smoke.py` for the
handshake the desktop config launches)

Addendum, October 3, 2026 (HR-5, from the log of run 37111755595 on
#203): the repository's own Action never read the pull request's
`.mcp.json`. The claude-code-action restores `.mcp.json`, `.claude/`,
`CLAUDE.md`, and a few other configuration paths from `origin/main`
before it runs, because a pull request head is untrusted for them
(`Restoring .claude, .mcp.json, .claude.json, .gitmodules, .ripgreprc,
CLAUDE.md, CLAUDE.local.md, .husky from origin/main (PR head is
untrusted)`), and `origin/main` at `485f3a5` did not carry the file;
the action's SHA step had already failed to open it (`fatal: could not
open '.mcp.json' for reading: No such file or directory`). The same
run set `enableAllProjectMcpServers: true` in the session's settings,
and its `--allowedTools` list named only the action's own GitHub tools
and the workflow's three commands, so on a base that carries the file
the action loads the project server and the model sees its tools as
unlisted ones. Claude's reply on #203 that no `metricmine-gold` tools
were available was therefore the reply of a session with no project
file, not of a server that failed to start. What the action does on a
base that carries the file is measured once, as a reported line on the
first pull request after this addendum, and recorded by a second
addendum.

### F-64
**A terminal the Microsoft Store build of Claude Desktop opens inherits
the app's redirected `AppData`, so a `uv sync` started from one fails
on the link uv makes for the project's Python, and two uv variables
that move the install out of `AppData` are the fix.** Reported
by a Windows 10 user whose Claude Desktop came from the Microsoft Store
and whose commands ran from that app (a run dated September 23, 2026,
read on October 2; uv 0.12.18, Python 3.12.14, a per-user install with
no administrator rights); the report was checked against the
repository, not re-run. `uv
sync` failed with a missing target directory for the Python
minor-version link under `%APPDATA%\uv`, and the link's target was seen
redirected into the app's package folder
(`%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache`), the same
redirection the demo guide already named for the config file. Setting
`UV_PYTHON_INSTALL_DIR` and `UV_CACHE_DIR` to plain paths under the user
profile fixed the sync on the first retry, and Path A and Path B then
reproduced every published number. A later `mm ingest` on the same
machine failed once removing a temporary file (`WinError 5`), which the
same redirection of the temp folder would explain; on the retry the
same warnings continued without stopping the ingest. That half is
unconfirmed, and the guide's entry sets `TEMP` and `TMP` beside the two
uv variables. uv honors both variables
on every platform (measured on Linux with uv 0.11.32: `uv python dir`
and `uv cache dir` follow them). The class: an agent host that is also
the install's process tree lends the install its own sandboxing, so a
guide written for a person at a terminal has to say what the host's
shell inherits; the mechanism, an app package's file-system
virtualization, is the report's reading and the guide's existing
config-file note, not something measured here. A `doctor` check for
the redirection is a candidate, not built.
(the Windows troubleshooting entry and the agent-run section of
[`docs/demo.md`](../demo.md), landing with this finding)

### F-65
**Three compiler tests made a symlink to the contracts directory, which
Windows grants to administrators and to Developer Mode and refuses a
per-user account, so the hosted runners passed and the first per-user
Windows machine failed exactly those three.** The fixture `_mini_repo`
in `tests/test_context_compiler.py` symlinked `<tmp>/contracts` to the
repository's `contracts/` so the reader resolves silver contracts by
its convention. On a per-user Windows 10 account the call raised
`OSError: [WinError 1314] A required privilege is not held by the
client`, and `uv run pytest -q` ended `687 passed, 70 skipped, 3
failed` (a run dated September 23, 2026, reported on October 2; the
line is the reporter's and was not re-run here); the `demo-windows`
runners, which hold the privilege, pass the same three, so the path CI
measures was not the path a stranger runs (the F-47 and F-55 class).
The fixture now tries the symlink and falls back to a directory copy on
`OSError`, and a unit test makes the symlink call raise so the fallback
runs on every platform. The demo path never runs these tests; a
stranger meets them only in the closing `pytest -q` the guide asks for.
(`tests/test_context_compiler.py`, the `_contracts_into` helper and
`test_contracts_fall_back_to_a_copy_without_the_symlink_privilege`,
landing with this finding)
