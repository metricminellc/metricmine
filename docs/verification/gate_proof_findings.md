# Gate Proof Findings: Verified Toolchain Behavior

Scratch gate proof run July 11, 2026, prior to Phase 1 exit (Decision
[D-12](../decisions/decision-register.md#d-12)).
Toolchain: dbt-core 1.11.12 · dbt-duckdb 1.10.1 · DuckDB engine 1.4.3 ·
datacontract-cli 1.0.12 (isolated uv tool). All findings below were observed
directly, not inferred from documentation. The gate path was re-proven at
dbt-core 1.12.3 with dbt-duckdb 1.11.0 at Arc 1 ([F-30](#f-30)); every
finding stands. They supersede any conflicting
guidance in older references. Governing rules: CLAUDE.md rules 10–11.

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
(contract v1.1.0, PRs #42–#44) and in the live break demo (PR #45, closed
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

