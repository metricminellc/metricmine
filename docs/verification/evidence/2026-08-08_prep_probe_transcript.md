# Sitting H Prep Probe Transcript (August 8, 2026)

Environment: Cowork sandbox, fresh clone of github.com/metricminellc/metricmine
at head e165d63 (#58). Toolchain verified at the pins before any probe:
Python 3.12.3 via uv sync, duckdb 1.4.3, dbt-core 1.11.12 + dbt-duckdb 1.10.1,
datacontract-cli 1.0.12 as an isolated uv tool with [duckdb], dbt_utils 1.3.3
vendored from GitHub tag 1.3.3 (the sandbox cannot reach hub.getdbt.com; CI
and the Mac use dbt deps per the standing lesson), airbyte-source-file 0.3.15
on uv-provisioned CPython 3.10, AIRBYTE_OFFLINE_MODE=1. CI env replicated:
absolute DBT_PROFILES_DIR and MM_WAREHOUSE_PATH.

## Baseline at head e165d63 (before any prep edit)

- `uv run pytest -m "not local" -q` → **37 passed, 8 deselected**.
- `make ingest` (offline) → landed {'online_retail_ii': 45228} into bronze.
- `uv run dbt build --project-dir transform --target local` → **PASS=12** (1 model, 11 tests).
- Gate 1: silver contract lints valid. Gate 3: sync `Synced 1 model: updated
  0 YAML files` (fixed point), test 11 passed, both exit 0, tree clean.
- `SELECT COUNT(*) FROM silver.silver_invoice_lines` → **44721**.

## Silver profile mint (PR 17 rehearsal)

With the targets-list run.py + config staged, `make profile`:

- Run 1: `wrote profiles/silver.silver_invoice_lines/v0001.json`
  `(sha256:e65bee8117b65958b8c4741b43509ece19a581dd1d6bad9a7e1da9b67b0b5fcd)`
- Run 2: `unchanged: ... already holds sha256:e65bee81...` — write-if-changed
  no-op, byte-identical, determinism rule 6 verified live.
- Artifact facts: row_count **44721**, duplicate_row_rate **0.0**, 9 columns,
  `invoiced_at` min/max present (`2009-12-01T07:45:00` / `2009-12-23T16:58:00`)
  — the temporal-evidence gap the profiler spec §3 recorded for bronze is
  discharged at silver. country distinct_count 24 (above the 20 cap, so
  sample_values, no distinct_values). 197 lines.
- **Sandbox-only deviation, expected and understood:** run 1 also minted a
  bronze v0002 (content_hash sha256:7f053bd7...) because the sandbox
  RE-LANDED bronze, and re-landed bronze is new bronze by spec §4 rule 5
  (fresh `_airbyte_raw_id` ULIDs and `_airbyte_extracted_at`). The v0002
  files were deleted from the prep tree; nothing committed changed. On the
  Mac, IF bronze has not been re-landed since the committed v0001 mint
  (July 30), `make profile` reports bronze `unchanged`; the runbook carries
  the deviation branch for the other case.

## canonical_key v2 golden vectors: SQL-vs-Python parity (F-16 candidate)

`gen_vectors.py` produced tests/golden/canonical_key_v2.json: 16 payload,
5 manifest, 4 scalar vectors (25 total; canonical serializations stored
beside every key for reviewability). `probe_sql_parity.py` then recomputed
every payload and manifest serialization AND key through DuckDB 1.4.3 SQL —
`lower(to_json(struct_pack(...)))` over VARCHAR-cast members in
lowercase-sorted field order, `sha256()` over the result; manifests via
`lower(to_json([...]))` — and compared byte-for-byte:

- **18 payload + 6 manifest serializations checked; failures: 0.**
- Coverage exercised through SQL: unicode lowercase parity (ü/ä/ß),
  DECIMAL(10,2) scale-preserving text ("2.50", "5.00"), TIMESTAMP
  "YYYY-MM-DD HH:MM:SS" with its interior space, include-as-null, boolean
  true/false, embedded-quote escaping, hyphen preservation, empty string,
  and the two form-(b) derived line_identity compositions over the real
  silver grain tuple types.
- The scalar-path vectors (4) pin the Python side only (schema keys embed as
  emission-time literals; no SQL path exists for them by design), and the
  empty-string digest was asserted equal to hashlib's
  e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.
- The dbt-path half (same semantics THROUGH dbt-built models) remains
  deliberately unverified until the pre-I rehearsal, per the ladder.

Raw log: `2026-08-08_probe_sql_python_parity.log`.

## json_valid over VARCHAR canonical text (F-15 candidate)

At duckdb 1.4.3: a VARCHAR column holding canonical JSON text returns
json_valid = true for object, object-with-null-member, unicode, and array
(manifest) forms; false for garbage and truncated JSON; `COUNT(*) WHERE NOT
json_valid(payload)` counts exactly the invalid rows (the C4 rule shape);
json_extract / json_extract_string project fields, and a projected string
casts cleanly to DECIMAL(10,2). This is the basis for declaring every
payload and manifest column `physicalType: VARCHAR` in the gold star
contract with error-severity C4 rules. Raw log:
`2026-08-08_probe_json_valid_varchar.log`.

## Contract instruments verified end to end (PR 18 / PR 19 rehearsal)

With both new contracts in contracts/ beside silver:

- Gate 1: **all three lint valid** at datacontract-cli 1.0.12
  (`2026-08-08_gate1_lint_three_contracts.log`).
- Gate 3 sync: the mapping contract's `invoice_lines` skipped (F-12 notice),
  all NINE gold star objects skipped per-object with the F-13 notice,
  `Synced 0 models` for both, silver still `Synced 1 model: updated 0 YAML
  files`, exit 0, **zero transform files changed**
  (`2026-08-08_gate3_sync_three_contracts.log`).
- Gate 3 test: mapping ⚪ no tests, gold star ⚪ no tests, silver 🟢 passed
  (11) — `Tested 3 contract(s): 2 no tests · 1 passed`, exit 0
  (`2026-08-08_gate3_test_three_contracts.log`).
- Gate 2 unchanged: PASS=12 (`2026-08-08_gate2_build_at_prep_tree.log`).
- The real mapping contract also validates against the frozen JSON Schema
  via the extended tests/test_mapping_contract_schema.py (parametrized
  discovery over contracts/*.odcs.yaml with physicalType: mapping).

## Pytest ledger (CI lane, -m "not local")

- Head e165d63: 37 passed, 8 deselected.
- Full prep tree: **75 passed, 13 deselected** (33 canonical-key tests,
  +2 schema-test additions incl. the real-contract validation, +3
  profiling-config tests; local lane 13 passed incl. 5 silver profile
  tests).
- Tree without the two contracts (empty real-mapping discovery): 74 passed,
  **1 skipped** — pytest reports the empty parameter set as one skip, so
  the PR 16 stage EXPECT is "71 passed, 1 skipped" (37 + 33 + 1 discovery
  guard) and the skip converts to a pass when PR 18 lands the contract.
- ruff: clean at every stage.

## One authoring lesson (caught at prep, cost zero live time)

Three unquoted YAML descriptions containing "manifest: compact JSON array"
parsed as nested mappings and failed gate-1 lint plus pytest collection.
Fixed by quoting. Lesson for contract authoring: any description with a
colon-space travels quoted or block-folded; the staged-file cadence means
the sitting inherits the fixed bytes.
