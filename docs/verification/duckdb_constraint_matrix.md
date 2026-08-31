# DuckDB Constraint Enforcement Matrix

> Repo path: `docs/verification/duckdb_constraint_matrix.md`
> The full Session A evidence behind finding
> [F-06](gate_proof_findings.md#f-06). Probed July 11, 2026, in the scratch
> gate-proof project, prior to Phase 1 exit
> (Decision [D-12](../decisions/decision-register.md#d-12)).
> Toolchain: dbt-core 1.11.12 · dbt-duckdb 1.10.1 · DuckDB engine 1.4.3.

## Method

Model `silver_orders` (`materialized: table`, `contract: enforced: true`)
over a 12-row seed. For each constraint type: declare the constraint in the
model's properties yml, inject one violating row via `UNION ALL` in the
model SQL, rebuild, and observe where the failure lands: the MODEL CREATION
step erroring means DuckDB enforced the constraint in DDL; a test step
failing would mean enforcement lives only in tests.

The probe command, identical for every row of the matrix (run from the
scratch project root; the same invocation captured in
[`evidence/2026-07-11_gate2_shape_failure.log`](evidence/2026-07-11_gate2_shape_failure.log)
and [`evidence/2026-07-11_gate3_content_failure.log`](evidence/2026-07-11_gate3_content_failure.log)
for the two break directions F-07 records):

```sh
uv run dbt build --select silver_orders --profiles-dir .
```

Sequence per probe: a green baseline build (`PASS=7 WARN=0 ERROR=0`), the
violating build, then a restored build returning to green (`PASS=7`),
proving the failure was the injected violation and nothing else.

## The matrix

| Constraint  | Accepted by dbt | Rendered in DuckDB DDL | Enforced by DuckDB at build | Error signature |
|-------------|-----------------|------------------------|-----------------------------|-----------------|
| not_null    | yes             | yes                    | yes                         | NOT NULL constraint failed: silver_orders__dbt_tmp.amount |
| unique      | yes             | yes                    | yes                         | PRIMARY KEY or UNIQUE constraint violation: duplicate key "1001" |
| primary_key | yes             | yes                    | yes                         | PRIMARY KEY or UNIQUE constraint violation: duplicate key "1001" |
| check       | yes             | yes                    | yes                         | CHECK constraint failed ... with expression CHECK((order_id > 0)) |
| foreign_key | yes             | yes                    | yes (conditional)           | Binder Error: no primary key or unique constraint for referenced table "raw_orders" |

The foreign_key probe's model-creation failure, verbatim from the run log:

```text
1 of 7 ERROR creating sql table model main.silver_orders ................ [ERROR in 0.05s]
...
Runtime Error in model silver_orders (models/silver_orders.sql)
  Binder Error: Failed to create foreign key: there is no primary key or
  unique constraint for referenced table "raw_orders"
Done. PASS=0 WARN=0 ERROR=1 SKIP=6 NO-OP=0 TOTAL=7
```

## Key findings

- dbt-duckdb enforces ALL FIVE constraint types at build time. This is
  stronger than the general dbt guidance (most adapters enforce only
  not_null); DuckDB is the exception.
- unique and primary_key share one enforcement mechanism (identical DuckDB
  error message).
- check expressions are evaluated by DuckDB at materialization; the
  `expression:` key works.
- foreign_key is enforced but CONDITIONAL: the referenced table must itself
  carry a PK/unique key on the referenced column. The bronze-layer seed
  `raw_orders` has none, so the FK failed to CREATE. This is DuckDB
  enforcing referential integrity strictly, not ignoring the constraint.

## Reconciliation with rule 5 (no contradiction)

- CLAUDE.md rule 5 is a PORTABILITY stance, not a DuckDB claim: only
  not_null is enforced across ALL target adapters (Snowflake, BigQuery,
  etc.). Uniqueness and referential integrity stay in dbt tests regardless
  of DuckDB's local behavior, so the pipeline ports by profile swap
  ([D-11](../decisions/decision-register.md#d-11)).
- The foreign_key probe demonstrates a second reason to delegate FKs to
  tests: even where enforced, DDL foreign keys impose structural
  requirements on referenced tables that a medallion bronze layer will not
  always satisfy.
- Empirical statement for the repo: DuckDB enforces all five locally; the
  non-portable ones are still tested because the demonstration target
  (Snowflake) will not enforce them.
