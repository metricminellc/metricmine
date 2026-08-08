# Gate Proof Findings — Verified Toolchain Behavior

Scratch gate proof run July 11, 2026, prior to Phase 1 exit (Decision
[D-12](../decisions/decision-register.md#d-12)).
Toolchain: dbt-core 1.11.12 · dbt-duckdb 1.10.1 · DuckDB engine 1.4.3 ·
datacontract-cli 1.0.12 (isolated uv tool). All findings below were observed
directly, not inferred from documentation. They supersede any conflicting
guidance in older references. Governing rules: CLAUDE.md rules 10–11.

Findings carry canonical IDs **F-01 to F-07**, cited from the
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
