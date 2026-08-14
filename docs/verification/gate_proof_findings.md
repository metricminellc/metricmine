# Gate Proof Findings — Verified Toolchain Behavior

Scratch gate proof run July 11, 2026, prior to Phase 1 exit (Decision
[D-12](../decisions/decision-register.md#d-12)).
Toolchain: dbt-core 1.11.12 · dbt-duckdb 1.10.1 · DuckDB engine 1.4.3 ·
datacontract-cli 1.0.12 (isolated uv tool). All findings below were observed
directly, not inferred from documentation. They supersede any conflicting
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
| [F-25](#f-25) | A demo artifact named for its schema collides with its own catalog | Serving rung |

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
failed exactly this way in rehearsal — resolving to `transform/warehouse/`,
the same failure class as the #41 `DBT_PROFILES_DIR` fix one level deeper —
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
over structs emits COMPACT JSON and preserves INSERTION order — it does
not sort, so sorted payload fields are an EMISSION-time property, never
assumed from the engine. `lower()` is unicode-safe over serialized JSON
text (ä, ß verified) and parity with Python `str.lower()` is
vector-checked. `json_valid()` and `json_extract()`/`json_extract_string()`
behave as C4 and the typed projections need. `to_json(list)` yields
compact JSON arrays (the manifest mechanism). VARCHAR casts are
scale-preserving for DECIMAL ("2.50", never "2.5") and render TIMESTAMP
as "YYYY-MM-DD HH:MM:SS" — so the Python keying reference must render
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
effect on sibling contracts in the same glob — even when the unmatched
object carries query-bearing error-severity quality rules (they are never
half-applied; equally, they are never applied, so rules on a permanently
model-less contract are dead letters and are banned by the engine spec's
JSON Schema). When a schema object name COLLIDES with a model another
contract claims, sync and test both exit 1 (`Cannot sync — overlapping
dbt models`) and write nothing. Flat placement of mapping contracts is
therefore permanent-safe at the pin, under the engine spec's naming rule.
ODCS lint at 1.0.12 tolerates the mapping contract's additive first-class
keys (object-level entityGroup/sourceTable/timeColumn/timeGrain/grain,
property-level mappingRole) — verified, and frozen by the pin.

### F-13
**A partially-modeled multi-object contract holds the gate green.** With
one schema object modeled and built and a second object unmodeled — the
second carrying a C3-shaped query rule against its nonexistent table —
sync syncs the matched object (properties updated, singular test written)
and skips the unmatched one; test runs the matched object's tests and
reports the contract PASSED; exit 0 end to end. Consequence for the
ladder: the registry amendment window (contract-first, model one PR
later) is safe in the preferred order. Stated honestly: a skipped
object's rules are declared but NOT enforced until its model lands —
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
text.** At duckdb 1.4.3, a VARCHAR column holding canonical JSON text —
object, object with a null member, unicode content, and compact-array
manifest forms — returns json_valid true, while garbage and truncated
JSON return false; `COUNT(*) ... WHERE NOT json_valid(payload)` counts
exactly the invalid rows, which is the C4 rule shape the gold star
contract declares at error severity. json_extract and
json_extract_string project payload fields from the same VARCHAR text,
and a projected numeric string casts cleanly to DECIMAL(10,2) — the
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
recomputed through DuckDB SQL at the pinned engine —
`lower(to_json(struct_pack(...)))` over VARCHAR-cast members in
lowercase-sorted field order, then `sha256()`; manifests via
`lower(to_json([...]))` — and compared against the Python reference
(`src/metricmine/keys.py`): 18 payload and 6 manifest serializations
checked, zero disagreements. Coverage exercised through SQL: unicode
lowercasing (ü/ä/ß), DECIMAL scale-preserving rendering ("2.50",
"5.00"), TIMESTAMP "YYYY-MM-DD HH:MM:SS" with its interior space
preserved, include-as-null, boolean rendering, embedded-quote escaping,
hyphen preservation, the empty string (digest equal to hashlib's), and
the form-(b) derived line_identity composition over the real silver
grain tuple types. The scalar path pins Python only: schema keys embed
as emission-time literals by design. The dbt-path half — the same
semantics THROUGH dbt-built models — deliberately remains with the
pre-regeneration rehearsal ([`docs/spec/engine.md`](../spec/engine.md)
§3).
([`evidence/2026-08-08_probe_sql_python_parity.log`](evidence/2026-08-08_probe_sql_python_parity.log);
the vector generator and parity probe are staged beside it as
`2026-08-08_gen_vectors.py` and `2026-08-08_probe_sql_parity.py`)

### F-17
**Sync generates a per-column `unique:` data_test twin for single-column
primaryKey flags.** At datacontract-cli 1.0.12, `datacontract dbt sync`
writes — beyond the §6-listed `not_null` block — a sync-shaped `unique:`
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
through verbatim — a property this finding both exposed and now exploits.
Raw schema-qualified references (`gold.<table>`) give dbt no dependency
edge, so the generated singular tests schedule in the ROOT layer, before
the models they query exist on a first-ever build. A warmed warehouse
masks the hazard completely (early tests find the previous build's
tables), which is why local runs and the pre-I rehearsal were green while
CI's fresh build errored 12 of the 20 no-ref tests with catalog errors
(PR #64, closed unmerged as this finding's primary evidence; the eight
that passed cold did so only by root-layer ordering luck — all twenty
were unordered). The fix, verified at the pinned toolchain over a fresh
warehouse: gold references in quality SQL use `{{ ref('<model>') }}` —
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
under `<contract>__1_2_0__...` filenames — byte-identical to the 1_1_0
set modulo version strings — and never deletes the stale files; both sets
coexist and `datacontract dbt test` still passes, but a plain `dbt build`
would run both. The transition is therefore sync-owned work committed
post-review in the amendment PR: regenerate, review against the rehearsal
reference, delete the stale set. (b) The same sync run updates every
committed engine-emitted properties file in place (contract_versions
1.1.0 to 1.2.0 — the only delta), which on a working tree MUST be
reverted (`git restore transform/models/gold/`), never committed: the
files are engine-owned at the old fixed point, and committing sync's edit
would diverge their ownership-manifest checksums and trip the engine's
rule-8 drift refusal at the next regeneration. In every CI workspace
between the amendment merge and the regeneration merge, gate 3 therefore
reports `updated 9 YAML files` ephemerally and still passes end to end
(the F-13 skip covers the not-yet-modeled registry object); the fixed
point returns when the regeneration lands. Re-verified in the same
rehearsal: the fixed point holds over the EXTENDED emission — the
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
refuse with `run make context` until v0002 mints — first live fire of the
D-30 guard, exactly as specified) and the golden-fixture equality test.
Consequence, now the recorded packaging rule: the amendment PR carries
exactly three things — the contract bump, the freshly minted
compiled-context artifact, and the refreshed byte oracle (the recorded
D-08 reading, third application) — and the regeneration PR carries
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

### F-25
**A demo artifact named for the schema it carries collides with its own
catalog, and two-part `gold.<x>` SQL fails as ambiguous at DuckDB
1.4.3.** A directly opened database takes its catalog name from the file
stem, so `demo/gold.duckdb` opens as catalog `gold` holding schema
`gold`, and every two-part reference — SELECT and CREATE alike — raises
`Ambiguous reference to catalog or schema "gold"`. Found live at Session
M's export implementation, before anything merged: the exporter could
not build the artifact as specified (the plain `gold.` view re-anchor
fails to bind inside the colliding catalog), and four of the five
serving tools fail through the unmodified query module, which renders
relations two-part by design. Three-part `gold.gold.<x>` works, and the
same file served through an ATTACH alias works — which is exactly why
nothing caught this earlier: the export replay was probed through an
ATTACH alias in a sandbox, and the live serving checkpoint ran against
the working warehouse, whose catalog is `metricmine`. Two individually
probed halves, never probed through each other — the F-22 class at the
artifact boundary. The remedy is Amendment E (Record 006): the committed
artifact is `demo/demo.duckdb`, whose catalog collides with nothing. The
plain `gold.` re-anchor then binds on a direct open and under any attach
alias, and natural two-part SQL works on every serving path — measured
on the Mac and reproduced clean-room by the Architect before the
amendment bound. The probe rule this mints: an artifact is proved by
opening it exactly the way its consumer opens it, never only through a
different access path.
([`evidence/2026-08-14_sessionM_demo_catalog_collision.log`](evidence/2026-08-14_sessionM_demo_catalog_collision.log))
