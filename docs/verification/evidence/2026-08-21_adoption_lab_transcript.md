# Adoption Lab Transcript (August 21 to 22, 2026)

Environment: Cowork sandbox, lab copy of github.com/metricminellc/metricmine
at head 2bbf4b3 (v0.1.0) at /tmp/mm-lab. Pinned toolchain brought up exactly
as CI does, with one sandbox deviation: hub.getdbt.com is unreachable from
the sandbox (403 at the proxy), so dbt_utils 1.3.3 was vendored from the
GitHub tag into transform/dbt_packages/ (the same deviation the August 8
prep transcript records). `uv sync` resolved the committed lock; dbt-core
1.11.12 on CPython 3.12; datacontract-cli 1.0.12 as an isolated uv tool;
AIRBYTE_OFFLINE_MODE=1; DBT_PROFILES_DIR and MM_WAREHOUSE_PATH absolute. No
API key present: the proposer's judgment half is simulated by a
deterministic evidence-only proposal; every gate below is the real gate.

Purpose: prove, with the real gates, that an EXISTING hand-written model
with no contract can be adopted into the pipeline bottom-up, that the gates
then enforce it, and measure the two things the repository had never
measured (whether `datacontract dbt sync` creates a properties file for a
model that has none, and what gate 3 does in the contract-before-model
window for an amended existing model).

## Baseline at head 2bbf4b3 (lab)

```
make ingest (offline)  -> landed {'online_retail_ii': 45228} into bronze
dbt build              -> Done. PASS=108 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=108
gate 1 (lint x3)       -> data contract is valid (three contracts)
gate 3 sync            -> silver_invoice_lines.odcs.yaml: Synced 1 model: updated 0 YAML files.
gate 3 test            -> gold_unified_event_star@1.2.0 passed; silver_invoice_lines@1.1.0 passed; Tested 3 contract(s): 1 no tests, 2 passed.
```

## Probe B: adopt an existing hand-written model, end to end

**B1. The fixture.** A hand-written silver model with no contract and no
properties file, the shape a user brings: `silver_country_daily_sales.sql`
(daily sales by country from the contracted line table; cancellations
excluded at this model; grain country + sales_date). Materialized as table
by the folder default in dbt_project.yml.

```
dbt build --select silver_country_daily_sales -> PASS=1
relation columns: [('country','VARCHAR'), ('sales_date','DATE'), ('line_count','BIGINT'),
                   ('units','HUGEINT'), ('gross_value','DECIMAL(38,2)'), ('invoice_count','BIGINT')]
rows: 85
duplicate rows over (country, sales_date): 0     <- the grain, measured
duplicate rows over (country,): 63
duplicate rows over (sales_date,): 64
```

DuckDB widened the aggregates: sum(INTEGER) is HUGEINT, sum(DECIMAL(10,2)
times INTEGER) is DECIMAL(38,2), count(*) is BIGINT. A contract authored
from the SQL would get these wrong; a contract authored from the profile
gets them exactly.

**B2. Profile the fixture** (one config entry added to
`profiling.targets`; `make profile`):

```
wrote profiles/bronze.online_retail_ii/v0002.json (sha256:b650dbc1...)   <- sandbox re-land deviation, documented Aug 8
unchanged: profiles/silver.silver_invoice_lines already holds sha256:e65bee81...
wrote profiles/silver.silver_country_daily_sales/v0001.json (sha256:0c1b052c...)
  country        VARCHAR        null_rate=0.0 distinct=22
  sales_date     DATE           null_rate=0.0 distinct=21
  line_count     BIGINT         null_rate=0.0 distinct=63
  units          HUGEINT        null_rate=0.0 distinct=80
  gross_value    DECIMAL(38,2)  null_rate=0.0 distinct=85
  invoice_count  BIGINT         null_rate=0.0 distinct=25
rows 85, duplicate_row_rate 0.0
```

**B3. The describe proposal, evidence-only, rendered and linted.** Columns,
physical types, and required flags came from the profile alone; the grain
keys were supplied by the operator (the judgment input); descriptions were
templated from evidence where a live run would have the model write them.
Rendered with the stance renderer from the same day's stance probe.

```
validator errors: none
rendered columns: [('country','VARCHAR',True,1), ('sales_date','DATE',True,2), ('line_count','BIGINT',True,None),
                   ('units','HUGEINT',True,None), ('gross_value','DECIMAL(38,2)',True,None), ('invoice_count','BIGINT',True,None)]
datacontract lint prep-lab/draft.silver_country_daily_sales.odcs.yaml -> data contract is valid. exit=0
```

**B4. verify-grain** (deterministic, through the existing read-only
warehouse protocol `duplicate_row_count(schema, table, columns)`):

```
duplicate rows over ['country', 'sales_date']: 0   <- PASS
duplicate rows over ['sales_date']: 64
duplicate rows over ['country']: 63
```

**B5. Approval simulated**: the linted draft copied to
`contracts/silver_country_daily_sales.odcs.yaml`. No properties file
exists for the model yet. See Probe D for what sync did next.

**B6. The two human edits rule 11 owns**, applied from the contract:
`config.contract.enforced: true` and `constraints: [not_null]` on the
contract's required columns (rule 5). Then the gates:

```
gate 2: dbt build --select silver_country_daily_sales -> Done. PASS=9 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=9
        (contract enforcement at HUGEINT and DECIMAL(38,2) data_types: green)
gate 3 sync  -> silver_country_daily_sales.odcs.yaml: Synced 1 model: updated 0 YAML files.   <- fixed point; hand edits preserved
gate 3 test  -> silver_country_daily_sales@1.0.0 passed; silver_invoice_lines@1.1.0 passed; Tested 4 contract(s): 1 no tests, 3 passed.
```

**B7. Enforcement proven on the adopted model.** Two edits to the model
SQL, each reverted afterward:

```
drop invoice_count from the model -> gate 2:
  Compilation Error in model silver_country_daily_sales
  This model has an enforced contract that failed.
  | column_name   | definition_type | contract_type | mismatch_reason       |
  | invoice_count |                 | BIGINT        | missing in definition |
  Done. PASS=0 WARN=0 ERROR=1 SKIP=8 TOTAL=9   exit=1

cast line_count to INTEGER -> gate 2:
  | column_name | definition_type | contract_type | mismatch_reason    |
  | line_count  | INTEGER         | BIGINT        | data type mismatch |
  Done. PASS=0 WARN=0 ERROR=1 SKIP=8 TOTAL=9   exit=1

restored -> Done. PASS=9
```

## Probe D: does `datacontract dbt sync` create a properties file?

The repository's evidence only ever showed sync updating files in place;
the "model with no properties file" case had never been measured. Measured
twice (once inside B5, once from a clean slate with the generated file and
tests deleted first):

```
$ ls transform/models/silver/
silver_country_daily_sales.sql  silver_invoice_lines.sql  silver_invoice_lines.yml
$ uv run datacontract dbt sync contracts/silver_country_daily_sales.odcs.yaml --project-dir transform --target local
  + tests/datacontract_cli/silver_country_daily_sales/..._row_count_85_at_v0001.sql
  + tests/datacontract_cli/silver_country_daily_sales/..._line_count__line_count_is_never_negative.sql
  + tests/datacontract_cli/silver_country_daily_sales/..._grain_enforcement__no_duplicate__country.sql
  (plus the unique_combination test)
$ ls transform/models/silver/
silver_country_daily_sales.sql  silver_country_daily_sales.yml  silver_invoice_lines.sql  silver_invoice_lines.yml
```

**Sync CREATED `silver_country_daily_sales.yml`**, carrying: `version: 2`,
the model name and the contract's table description,
`config.meta.datacontract_cli.contract_id`, and every column with the
contract's exact physicalType as `data_type` (VARCHAR, DATE, BIGINT,
HUGEINT, DECIMAL(38,2)), the contract descriptions, and warn-severity
`not_null` data_tests per required column with the generated-test
metadata. It did NOT write `config.contract.enforced` and did NOT write
`constraints` (`grep -c "enforced\|constraints"` = 0). Those two are the
human edits of B6. This is the opposite of F-02's export scaffold: sync
writes exact DuckDB types, so the properties file is two keys away from
enforcing.

One naming nit worth a render rule: the generated test file for the
rowCount rule is `..._row_count_85_at_v0001.sql` because the rule's
`description` text was the evidence sentence; rule descriptions must be
stable prose ("The table is never empty"), and the evidence belongs in the
proposal record, never in `description`.

## Probe C: the contract-before-model window for an amended existing model

D-08 orders a shape change as contract PR first, implementation PR after.
CI had proven gate 3 tolerates a contract whose model does not exist yet,
never an amended contract adding a column to an existing model. Measured
on `silver_invoice_lines` (contract v1.1.0 to v1.2.0 adding
`invoice_day DATE`; the model and its committed properties file left
unchanged; contract, properties, and generated tests restored after each
variant):

```
=== invoice_day required: false (optional addition) ===
gate 1 lint                      -> valid
gate 2 build (committed yml)     -> Done. PASS=10 WARN=0 ERROR=0 TOTAL=10
gate 3 sync                      -> Synced 1 model: updated 1 YAML file, wrote 4 tests   (invoice_day added to the yml)
gate 3 test                      -> dbt tests passed. Ran 11 tests.   exit=0
a build AFTER sync touched yml   -> Compilation Error: invoice_day | DATE | missing in definition   (the model PR's job)

=== invoice_day required: true (required addition) ===
gate 1 lint                      -> valid
gate 2 build (committed yml)     -> Done. PASS=10
gate 3 sync                      -> Synced 1 model: updated 1 YAML file, wrote 4 tests
gate 3 test                      -> error | Check that field invoice_day has no missing values | Runtime Error in test not_null_silver_invoice_lines_invoice_day: "invoice_day" not found   <- RED
```

Reading: in CI's order (build, then sync, then test on the workspace copy)
a contract-only PR that ADDS AN OPTIONAL column is green in the window and
the model PR that follows carries the column plus the canonicalized
properties file. A contract-only PR that adds a REQUIRED column is red at
gate 3, because the generated not_null test references a column the model
does not produce yet. The executable form of D-08's order is therefore a
two-step amendment for required additions: add as optional, land the
model, then tighten to required in a second contract version. The amend
stance should propose additions as optional with a declared follow-up
change, never as required in the first step.

## Cross-reference

The deterministic scan prototype and its four-scenario transcript
(`scan_transcript.md`) ran on a snapshot of this lab at the B1 state; see
`scan.py`. Both are evidence for the same finding set.

Files beside this transcript: `fixture-silver_country_daily_sales.sql`,
`profile-silver_country_daily_sales-v0001.json`,
`rendered-describe-silver_country_daily_sales.odcs.yaml`,
`properties-after-sync-and-enforce.yml`, `sync-creates-properties.log`.
