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
as the properties file.

## Constraint enforcement matrix (empirical)

### F-06
**All five constraint types are enforced by DuckDB at build time; rule 5
stands as a portability stance.**

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
