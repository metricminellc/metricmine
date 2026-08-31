# Gold Layer Specification: The Unified Event Star

> Repo path: `docs/spec/gold-unified-event-star.md`
> Lands via PR: `docs(spec): gold layer specification, the unified event star`
> Source of truth for the gold layer. Governing decisions:
> [D-07](../decisions/decision-register.md#d-07), [D-17](../decisions/decision-register.md#d-17),
> [D-18](../decisions/decision-register.md#d-18), [D-19](../decisions/decision-register.md#d-19).
> Companion diagram: `docs/diagrams/gold_unified_event_star_flow.svg` (+ `.mmd` Mermaid twin)
> (committed rename of the delivered `MetricMine_Gold_Unified_Event_Star_Flow.svg/.mmd`, to match repo naming).

## Purpose

Gold is the unified event star: a source-invariant, self-describing, content-addressed
star schema. Every source lands in the same physical shape, so new sources add rows,
not schema. The auto-modeling engine consumes an approved mapping contract and emits
the dbt models that build it (D-07). The star is the terminal gold layer (D-17); it
serves consumers only through the shared query module, with the MCP server primary.

## Objects

One `gold` schema in the working DuckDB file. All objects are engine-emitted dbt
models, landing as pull requests under the ownership manifest (D-09).

| Object | Kind | Key | Contents |
|---|---|---|---|
| `dim_source_values` / `dim_source_columns` | table | record hash / schema hash | Source-system group. Constant per build per source. |
| `dim_run_values` / `dim_run_columns` | table | record hash / schema hash | Lineage group: mapping contract name + version, engine version. Deterministic content only. |
| `dim_timeframe_values` / `dim_timeframe_columns` | table | record hash / schema hash | Time group from the mapping contract's declared time columns, at declared grain. Per row. |
| `dim_<category>_values` / `dim_<category>_columns` | table | record hash / schema hash | Dimension set per fact category: attribute payload + manifest. Deduplicated by content key. |
| `fact_<category>_values` | table | composite PK, below | Measure payload, manifest FK, group-key FKs. One row per declared grain. |
| `context_registry` | table | schema key PK | `schema_key`, entity group, contract name, contract version, compiled context. Written by the context compiler. |
| `vw_<category>_typed` | view | none | Typed projection: `json_extract` + cast per manifest field. Uncontracted; header-labeled derivative. |
| `mart_<category>_typed` | table | none | Materialized typed mart (D-36 as amended): the projection's SELECT as a table, lean, typed columns plus `fact_hash_id` and `captured_at`, ordered by the time column. Uncontracted; header-labeled derivative. |

Every `*_values` row carries the four-element pattern: value payload (JSON object),
schema manifest (held in the columns dim, referenced by schema key), record key,
and schema key. Audit stamps (`loaded_at`, and `captured_at` on the silver-derived
tables, D-38) sit outside the pattern as plain columns,
outside every hashed payload. Hashed payloads contain deterministic content only;
that rule keeps `make demo` byte-reproducible.

## Keys: canonical_key v2 (D-18)

- Payloads (JSON objects): parse, serialize compact (no whitespace) with **sorted keys**,
  lowercase the entire serialization, SHA-256, hex-encode (64 chars).
- Scalars and manifests: cast to text, lowercase, strip whitespace. **Hyphens are
  preserved.** Manifests serialize as compact JSON arrays in declared order.
- Properties: deterministic across runs and machines; case-insensitive;
  whitespace-insensitive; **order-insensitive for payloads** (delta from 2023).
- Migration note: none needed. The clean-room rebuild carries zero legacy data;
  2023 keys and v2 keys never need to match.

## Fact key and grain

Fact PK = (`fact_hash_id`, `source_hash_id`, `timeframe_hash_id`, `dim_hash_id`).
`run_hash_id` is a non-key attribute referencing `dim_run_values`, so a contract
version bump never mints duplicate facts. Deliberate deltas from the 2023 ERD:
the `user` group is dropped (never populated), the `account` group is absorbed into
declared dimension groups, and `run` (successor to `job`) leaves the key.

Grain is declared per category in the mapping contract, never assumed:

- **Aggregated grain:** the emitted fact model GROUP BYs the dimension tuple and applies
  the declared aggregation per measure, adding a standard `_row_count` measure so
  conservation stays checkable by arithmetic.
- **Transaction grain:** the mapping contract declares a degenerate identifier
  (e.g. invoice line id) carried inside the dimension payload so content keys stay unique.

Without a declared grain the composite hash key silently collapses duplicate rows.
With it, content addressing guarantees idempotent rebuilds.

## Reading the star: content keys, not row identifiers

The hash keys are content addresses. Four reading rules, stated here
because the first live serving sessions proved a consumer needs them
([F-23](../verification/gate_proof_findings.md#f-23),
[F-24](../verification/gate_proof_findings.md#f-24)):

- **Row counts at transaction grain:** `COUNT(*)` on the fact table, or
  `COUNT(DISTINCT line_identity)` through the typed view. The typed mart
  is one row per fact row and does not carry `line_identity`, so
  `COUNT(*)` is the row count there. Never
  `COUNT(DISTINCT fact_hash_id)`: that column addresses the measure
  payload alone, and identical measure payloads collide by design (F-24).
- **The category dimension is 1:1 with its fact at transaction grain, by
  construction:** the declared degenerate identifier rides inside the
  dimension payload precisely so content keys stay unique (F-23). Dedup
  shows up where payloads repeat (the timeframe, source, and run
  groups), not in the category group, which spends it to keep the grain
  lossless.
- **`line_identity` is a row fingerprint, not a business key:** a
  restated measure mints a new identity, with nothing linking old to
  new. Cross-version record linkage is out of scope for this star and
  stated as such.
- **The signature-test citation:** the registry's `country` context calls
  it "the signature-test dimension"; what that test asserts (a new
  dimension by contract amendment and regeneration alone) is narrated
  with evidence in
  [`docs/verification/signature-test.md`](../verification/signature-test.md).

The trade these rules record, and the alternatives deliberately not taken
before v0.1.0 (relocating the degenerate identifier onto the fact;
renaming `fact_hash_id`), are banked in F-23/F-24 as one post-tag
decision candidate.

## Context registry (D-19)

Schema keys are the address of meaning. The context compiler writes one row per
schema key: entity group, governing contract name + version, and the compiled
context gathered at approval time. Contracts are never embedded in payloads.
`get-context` in the MCP server is a registry lookup.

## Conservation tests (carried from the 2023 ledger)

Enforced as dbt tests in CI on every pull request:

- **C1** silver rows in scope = fact rows (transaction grain) or `sum(_row_count)` (aggregated grain).
- **C2** every fact group key resolves to its values dimension (anti-join
  key-resolution rules in the gold contract; mechanism per
  [`engine.md`](engine.md) section 7).
- **C3** every schema key present in gold exists in `context_registry`.
- **C4** every payload parses as valid JSON.
- **C5** field-level reconciliation: every silver row joins the typed
  surface on the derived line identity and every mapped field matches
  its served value (V1-06; the Session J runbook validation promoted
  to a standing test at contract v1.3.0).

When a deployment runs incrementally, the expensive rules batch-scope
behind the `mm_batch_floor` var and `make audit-gold` runs the
unscoped full-table forms on demand (D-39); with the var unset, CI
included, every rule runs full-table exactly as declared.

Regeneration output and the regeneration PR narrative keep the arithmetic
self-verification style (`N rows + offset = total`); the engine itself
never queries the warehouse ([`engine.md`](engine.md) section 11), and
enforcement lives in the tests.

## Materialization and contracts

Star tables materialize as `table` by default, or `incremental` behind
`engine.materialization` (D-38; D-07 as amended); dbt contract
enforcement requires
table or incremental, so views are not an option for contracted
objects. At incremental, every silver-derived model filters its
source to the `captured_at` watermark and inserts by content-key
anti-join, and contracted models set `on_schema_change: 'fail'`
(F-34): a shape change arrives through a contract amendment and a
regeneration, never silently at build time.
Projections are views and carry no contract. The typed mart (D-36) is a
table and also carries no contract: enforcement is a property of the star
tables and the registry, and the typed surface stays derivative. One ODCS contract,
`contracts/gold_unified_event_star.odcs.yaml`, covers all star tables plus the
registry as schema objects, versioned as one unit. Because the physical shape is
source-invariant, this contract is stable: payload evolution surfaces as new
schema keys (data), never as contract amendments (governance).

## Signature test (restated per D-17)

A new dimension added to the mapping contract flows through regeneration and
`dbt build` with **no engine code change, no physical schema change, and no gold
contract amendment**, announced by a new schema key in `dim_<category>_columns`
and a registry row.

## Serving surface

All access through `src/metricmine/query.py` (the shared module) over the D-11
read-only protocol. MCP tools: list fact categories; get schema by schema key;
get context by schema key; row-limited query; lookup record by content key
(the provenance tool). The hosted demo imports the same module.

## Explicitly out of scope

Partitioning, multiple dimension groups per category, and any
performance claims without measurement (D-40 states the measurement
rule; `docs/scale.md` carries the measured curve). Non-goals in the
README remain standing.

## References

In this repository:

- [`docs/decisions/decision-register.md`](../decisions/decision-register.md):
  D-07, D-08, D-09, D-11, D-17, D-18, D-19 (all adopted), with the
  CLAUDE.md rule crosswalk.
- [`docs/spec/current-state/data-capture-baseline.md`](current-state/data-capture-baseline.md):
  the abridged clean-room baseline: packet model, 2023 canonicalization
  contract, conservation ledger, decomposition pattern, and the recorded
  deltas this spec makes deliberately.
- [`docs/verification/gate_proof_findings.md`](../verification/gate_proof_findings.md):
  empirical toolchain findings this spec's materialization and gate rules
  rest on.

Project records (design history maintained outside the repository; nothing
here depends on them): Gold Layer Design 001 and the unabridged Current-State
Technical Specification v1.0, both July 11, 2026.
