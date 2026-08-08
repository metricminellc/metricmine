# Prep-Session Probe Transcript — P1, P2, P3 (August 1, 2026)

Architect-side toolchain probes run before Sitting G, per the Phase 4
ladder's rehearsal and probe map. Staged into the repository by Justin
under the external-evidence cadence (#46 pattern). These results graduate
into `docs/verification/gate_proof_findings.md` as findings F-12 through
F-14 at Sitting G; the planning session's function-semantics probe
graduates as F-11 in the same PR (its transcript lives in the project's
planning records; its results are restated in F-11).

## Environment

Captured in `2026-08-01_baseline_environment.log` (staged beside this
transcript): fresh clone of `github.com/metricminellc/metricmine`, head
`7345e4e` (#51), clean status; pins verified by import (dbt-core 1.11.12 ·
dbt-duckdb 1.10.1 · duckdb 1.4.3 · airbyte 0.53.2 · datacontract-cli
1.0.12 as the isolated uv tool with the CLAUDE.md pin string); bronze
landed by `AIRBYTE_OFFLINE_MODE=1 make ingest` through the pre-provisioned
CPython 3.10 connector venv — 45,228 rows, matching the recorded count;
CI job env replicated verbatim (absolute `DBT_PROFILES_DIR`, absolute
`MM_WAREHOUSE_PATH`); gate 1 exit 0, gate 2 `PASS=12` exit 0, gate 3 sync
exit 0 with a clean `git status` over the committed state (the silver
fixed point re-confirmed), gate 3 test exit 0 with 11 tests passed.

Sandbox deltas, stated for honesty (neither affects probe validity):
dbt_utils 1.3.3 vendored into `transform/dbt_packages/` from the GitHub
tag, because the sandbox cannot reach hub.getdbt.com (the Mac and CI run
`dbt deps` normally); Python interpreters are uv-managed in the sandbox.

Method note on exit codes: the first capture pass for P1a/P1b/P1c piped
tool output through `tail`, which masks exit codes (`$?` reports tail's
status). Those three were re-captured unpiped
(`2026-08-01_probe_p1_exitcodes.log`, `..._p1c_exitcodes.log`); only the
P1c reading changed (sync/test 0 → 1). The P1a re-capture ran in the P1b
state (query rule present); P1a's own codes are corroborated by its
original success output. Every later probe (P1d, P2, P3, P3b) captured
exit codes unpiped directly.

## Probe P1 — permanent model-less contract in contracts/ (Q6 evidence)

**Question.** Gate 1 lints `contracts/*.odcs.yaml` flat and gate 3
syncs/tests the same glob. A mapping contract is an ODCS document with no
corresponding dbt model, ever. Is flat placement permanent-safe at the
pinned toolchain, or does gate 3 half-apply it?

**Method.** A candidate mapping contract
(`gold_invoice_lines_mapping.odcs.yaml`, schema object named
`invoice_lines`, physicalType `mapping`) added beside the silver contract;
gates run over the glob in four variants. The P1b-state fixture is
preserved as `2026-08-01_probe_p1_mapping_fixture.odcs.yaml`; the P1d
fixture as `2026-08-01_probe_p1d_fixture.odcs.yaml`.

**P1a — model-less contract, no query rules.**

- `datacontract lint` on the mapping contract: exit 0, "data contract is
  valid" (per-property `customProperties` included — lint tolerates them).
- `datacontract dbt sync contracts/*.odcs.yaml ...`: exit 0. Warning on
  stderr: ``Schema `invoice_lines` resolves to model `invoice_lines`,
  which has no matching dbt model (no `.sql` or YAML entry) in this
  project — nothing to test, skipping. [...]`` (the elided remainder
  suggests `--model-resolution physicalName`; full text in the log).
  Output: `gold_invoice_lines_mapping.odcs.yaml: Synced 0 models: updated
  0 YAML files.` The silver contract synced 1 model, 0 updates, unchanged.
- `git status --porcelain` after sync: the only entry is the probe's own
  untracked contract — sync created and modified nothing.
- `datacontract dbt test contracts/*.odcs.yaml ...`: exit 0. Contract
  results: `⚪ gold_invoice_lines_mapping@0.0.1 — no tests` ·
  `🟢 silver_invoice_lines@1.1.0 — passed` · "Tested 2 contract(s): 1 no
  tests · 1 passed." Silver still ran its 11 tests; zero
  cross-contamination.

**P1b — model-less contract WITH a query-bearing error-severity quality
rule** (the half-apply hazard: would sync emit a singular test that then
runs against a nonexistent table?).

- lint 0, sync 0, test 0 — identical to P1a
  (`2026-08-01_probe_p1_exitcodes.log`). No singular test file was
  generated for the unmatched object; `transform/tests/datacontract_cli/`
  unchanged. The skip happens at schema-object → model resolution, BEFORE
  quality-rule translation, so an unmatched object's rules are never
  half-applied. Corollary, stated plainly: they are never applied at all —
  a quality rule on a model-less contract is a dead letter, silently.

**P1c — name-collision hazard.** The mapping object renamed to
`silver_invoice_lines`, colliding with the model the silver contract
claims.

- sync: exit **1**. ``Cannot sync — overlapping dbt models:
  `silver_invoice_lines` is claimed by different contracts. [...]`` (the
  elided remainder names both contract files; full text in the log).
  Nothing written; the silver properties file was NOT contaminated
  (`git diff` empty).
- test: exit **1**, same overlap error
  (`2026-08-01_probe_p1c_exitcodes.log`).
- The failure is loud and fail-safe: a collision cannot merge through the
  gate, and it corrupts nothing on the way down.

**P1d — first-class key tolerance.** A variant carrying the mapping
declaration as first-class YAML keys — object-level `entityGroup`,
`sourceTable`, `timeColumn`, `timeGrain`, and a structured `grain:` block
with `degenerateIdentifiers`; property-level `mappingRole` — with no
customProperties decoration. Fixture preserved
(`2026-08-01_probe_p1d_fixture.odcs.yaml`).

- lint: exit 0, valid (`2026-08-01_probe_p1d_firstclass_lint.log`).
  Independently corroborated: the engine spec's example contract carries
  the same first-class key set and lints clean
  (`2026-08-01_example_lint_full.out`). ODCS lint at 1.0.12 validates the
  known ODCS structure and tolerates additive first-class keys. The pin
  freezes that behavior; a datacontract-cli upgrade re-verifies it under
  the rule-1 amendment discipline.

**P1 verdict (→ F-12).** Flat placement is permanent-safe at the pinned
toolchain. Adopted consequences for the engine spec: mapping contracts
live flat in `contracts/`; the category object name must never equal a
dbt model name (structural rule: category names are bare, emitted models
carry `dim_`/`fact_`/`vw_` prefixes or the reserved `context_registry`
name); mapping contracts carry no query-bearing quality rules (dead
letters per P1b); `physicalType: mapping` is the machine discriminator.

## Probe P2 — partially-modeled multi-object contract (Sitting J ordering)

**Question.** At Sitting J the gold contract v1.1.0 adds
`context_registry` plus its C3 error-severity rule at PR 23, one PR
before the registry model lands at PR 24. Does the partially-modeled
window hold the gate green (preferred order), or red (fallback order,
D-08 application reading)?

**Method.** Probe contract `gold_probe_star.odcs.yaml`
(`2026-08-01_probe_p2p3_fixture_contract.odcs.yaml`) with two schema
objects: `dim_probe_values` (dbt model built, engine-emitted-style
properties file, contract enforced) and `probe_registry` (no model), each
carrying a query-bearing error-severity sql rule. The unmodeled object's
rule references the nonexistent `gold.probe_registry` — the exact C3
shape. Baseline `dbt build` green (13 = 12 + the probe model; a
contract-enforced gold-schema model built through the real gate).

**Observed** (`2026-08-01_probe_p2_sync_full.out`,
`..._p2_test_full.out`).

- sync: exit 0. The modeled object synced (`Synced 1 model: updated 1
  YAML file, wrote 1 singular SQL test`); the unmodeled object skipped
  with the same warning as P1. NO test file was generated for
  `probe_registry`'s rule.
- test: exit 0. Per-contract runs, both visible in the full log:
  `gold_probe_star@0.0.1 — passed` with `Ran 3 tests` (the matched
  object's singular sql test plus its two generated not_null tests), then
  `silver_invoice_lines@1.1.0 — passed` with `Ran 11 tests`. "Tested 2
  contract(s): 2 passed." The unmodeled object's C3-analog rule did not
  run — no catalog error, no red.

**P2 verdict (→ F-13).** The partially-modeled window is SAFE at the
pinned toolchain. Sitting J takes the PREFERRED order: PR 23 (gold
v1.1.0, contract-only, adds context_registry + C3) merges green before
PR 24 (the regeneration that lands the registry model). The D-08 fallback
application reading is moot and stays out of Decision Record 004. One
consequence to state honestly: during the PR 23 → PR 24 window C3 is
declared but NOT enforced (skip means no coverage, not passing coverage);
the window is one PR on one branch and closes when the model lands, at
which point sync generates the C3 test and it gates from then on.

## Probe P3 — sync fixed point over engine-emitted properties (Q8 evidence)

**Question.** Gate-3 sync edits properties files in place (F-05). If sync
edited an engine-emitted file, its ownership-manifest checksum would
diverge and the engine would flag its own gate as drift (rule 8). Does a
fixed point exist, and what exactly must the emitter pre-emit to sit on
it?

**Method, two rounds.** Round one (P3): the P2 fixture's properties file,
written the way a naive emitter would (contract enforcement, columns with
name + data_type, not_null constraints, `contract_id` binding, a
generated-by header comment, no sync-generated blocks); sync pass 1, then
pass 2 over the post-sync state with sha256 capture. Round two (P3b, run
after review flagged that round one's delta capture came from `git diff`
over an UNTRACKED file and was therefore empty): the same fixture with
deliberately DIVERGENT model and column descriptions, pre-sync bytes
preserved (`2026-08-01_probe_p3b_presync_fixture.yml`), and the delta
MEASURED as a real `diff -u`
(`2026-08-01_probe_p3b_pass1_delta.log`).

**Pass-1 delta, measured (P3b diff) — the fixed-point shape the emitter
must produce:**

1. The model-level `description` AND every column-level `description` are
   REPLACED with the governing contract's text, verbatim (the diff shows
   all three divergent emitter texts overwritten).
2. Every `required: true` property gains a `data_tests: - not_null:`
   block: `config.severity: warn`, `config.meta.datacontract_cli`
   carrying `check: <model>__<column>__field_required`,
   `include_in_tests: true`, `contract_versions: [<version>]`,
   `generated: true`, plus `description: Check that field <column> has no
   missing values`.
3. Every query-bearing quality rule on a MATCHED object becomes a
   singular test under `transform/tests/datacontract_cli/<contract_id>/`
   (`2026-08-01_probe_p2p3_fixture_singular_test.sql`), named
   `<contract_id>__<version, dots to underscores>__<model>__<description
   slug, truncated>.sql`, with header `-- AUTO-GENERATED by `datacontract
   dbt sync`. Do not edit.`, a config line carrying the contract-declared
   severity and datacontract_cli meta (`check: <model>__custom_sql`), and
   the query wrapped as `WITH _dc_metric (metric_value) AS (<query>)
   SELECT metric_value FROM _dc_metric WHERE metric_value IS NULL OR
   metric_value <> 0`.
4. Comment headers SURVIVE in-place editing: the P3b log shows the mock
   generated-by header intact after pass 1. Generated-by headers are
   sync-safe.

Nothing else changed in the properties file in either round; the delta
list above is what the two rounds observed at this fixture shape (a
richer fixture at the pre-regeneration rehearsal re-checks it over the
real emitted star).

**Fixed point.** Both rounds: a second sync over the post-sync state
reports `updated 0 YAML files` for both contracts, and `sha256sum -c`
over the pre-captured manifest returns OK for the properties file and the
singular test (P3: `2026-08-01_probe_p3_fixedpoint.log`; P3b with the
commands named in the log: `2026-08-01_probe_p3b_pass1_delta.log`). The
singular test file is left byte-identical by the second sync.

**P3 verdict (→ F-14).** The fixed point exists and is reachable by
emission: an engine that emits descriptions from the contract, the
contract_id binding, and the per-required-column not_null data_tests
block in sync's exact shape produces files sync leaves byte-identical.
Ownership-manifest checksums are defined over that state. Singular test
files under `transform/tests/datacontract_cli/` are SYNC-owned (their
header says so), sit outside the engine's manifest, and stay under the
committed-post-review discipline (F-05/F-08). The pre-regeneration
rehearsal re-verifies sync no-op over the real emitted star before the
first regeneration PR goes live.

## Incidental evidence (recorded, not claimed beyond its scope)

- A contract-enforced, engine-emitted-style model in
  `transform/models/gold/` built green through gate 2 with the custom
  schema macro landing it in the `gold` schema — a down payment on the
  dbt-path verification, which still lands properly at the
  pre-regeneration rehearsal (Q4 discipline unchanged).
- `datacontract dbt test` reports per-contract results and runs
  per-contract test batches; a contract whose objects all lack models
  reports `no tests` and exits 0 without affecting sibling contracts in
  the same glob.

## Staged evidence set (this directory)

This transcript plus: `2026-08-01_baseline_environment.log` ·
`2026-08-01_probe_p1a_gate3.log` · `2026-08-01_probe_p1_exitcodes.log` ·
`2026-08-01_probe_p1c_exitcodes.log` ·
`2026-08-01_probe_p1d_firstclass_lint.log` ·
`2026-08-01_probe_p1d_fixture.odcs.yaml` ·
`2026-08-01_probe_p1_mapping_fixture.odcs.yaml` ·
`2026-08-01_probe_p2_sync_full.out` · `2026-08-01_probe_p2_test_full.out`
· `2026-08-01_probe_p2p3_fixture_contract.odcs.yaml` ·
`2026-08-01_probe_p2p3_fixture_model.sql` ·
`2026-08-01_probe_p2p3_fixture_postsync.yml` ·
`2026-08-01_probe_p2p3_fixture_singular_test.sql` ·
`2026-08-01_probe_p3_fixedpoint.log` ·
`2026-08-01_probe_p3b_presync_fixture.yml` ·
`2026-08-01_probe_p3b_pass1_delta.log` ·
`2026-08-01_example_lint_full.out` ·
`2026-08-01_uvadd_jsonschema_rehearsal.log`. The wider prep archive
(intermediate captures superseded by the above) stays outside the
repository in the project's planning records.
