# The Auto-Modeling Engine: Mapping Contract In, Gold Models Out

**Status:** adopted at the Phase 4 opening sitting (spec PR; ladder position
PR 12). Implements across the Phase 4 sittings: keys and contracts first,
the engine and its first regeneration after, per the plan of record.
**Governing decisions:** [D-07](../decisions/decision-register.md#d-07)
(emits models, never DDL), [D-08](../decisions/decision-register.md#d-08)
(symmetric gates), [D-09](../decisions/decision-register.md#d-09)
(regeneration via PR under an ownership manifest),
[D-17](../decisions/decision-register.md#d-17) (the unified event star),
[D-18](../decisions/decision-register.md#d-18) (canonical_key v2),
[D-19](../decisions/decision-register.md#d-19) (context by content address),
[D-28](../decisions/decision-register.md#d-28) (contract-declared severity);
minted with this spec: [D-29](../decisions/decision-register.md#d-29)
(this specification), [D-30](../decisions/decision-register.md#d-30)
(registry population), and Amendment C to
[D-16](../decisions/decision-register.md#d-16) (properties-file ownership
boundary).
**Companion artifacts, same directory:**
[`engine/mapping-contract.schema.json`](engine/mapping-contract.schema.json)
(the machine-readable mapping contract schema) and
[`engine/example-mapping-contract.odcs.yaml`](engine/example-mapping-contract.odcs.yaml)
(the validated example). `tests/test_mapping_contract_schema.py` holds the
schema to its example in CI.
**Evidence:** findings [F-11 through F-14](../verification/gate_proof_findings.md#f-11)
and the probe transcript
[`evidence/2026-08-01_prep_probe_transcript.md`](../verification/evidence/2026-08-01_prep_probe_transcript.md).
All toolchain behavior cited below was observed at the pinned toolchain
(dbt-core 1.11.12 · dbt-duckdb 1.10.1 · duckdb 1.4.3 · datacontract-cli
1.0.12), never inferred from documentation.

## 1. Purpose and boundary

The auto-modeling engine is deterministic code, not an agent. It consumes
two approved contracts, a **mapping contract** (declared by this spec) and
the **gold star contract** (`contracts/gold_unified_event_star.odcs.yaml`),
and emits the dbt model files that build the unified event star: the
values/columns dimension pairs, the category fact table, the context
registry, and the uncontracted typed surface per category: the
materialized typed mart and the projection view, per the `engine.marts`
configuration (D-36). It never
executes DDL, never writes to the warehouse, never runs at proposer
runtime, and never writes outside `transform/models/gold/` plus its
ownership manifest (D-07, D-09). dbt builds what the engine emits; the
three gates judge the result exactly as they judge human work (D-08).

The signature property this machinery exists to demonstrate (D-17): a new
dimension added to the mapping contract flows through regeneration and
`dbt build` with no engine code change, no physical schema change, and no
gold contract amendment, announced by a new schema key in the columns
dimension and a registry row.

## 2. The mapping contract

One mapping contract declares how one silver table maps into one fact
category. It is a native ODCS v3.1.0 document living flat in `contracts/`
beside the table contracts, and simultaneously an instance of the machine
schema in [`engine/mapping-contract.schema.json`](engine/mapping-contract.schema.json).
Every mapping element is **first-class YAML**: machine-consumed schema
elements, never customProperties decoration. ODCS lint at 1.0.12 validates
the known ODCS structure and tolerates these additive keys (F-12, probe
P1d); the pin freezes that behavior, and any datacontract-cli upgrade
re-verifies it under the rule-1 amendment discipline.

Document shape (normative; the JSON Schema is the enforceable statement):

- Exactly **one** schema object: the category. `name` is the category name
  (for example `invoice_lines`); `physicalType: mapping` is the machine
  discriminator separating mapping contracts from table contracts;
  `logicalType: object`.
- Object-level first-class keys: `entityGroup` (the star's dimension-group
  assignment), `sourceTable` (schema-qualified silver source, for example
  `silver.silver_invoice_lines`), `timeColumn` (the declared time field),
  `timeGrain` (enum: minute, hour, day, week, month, quarter, year), and
  `grain` (below).
- `properties`: the mapped silver columns. Each carries the ODCS basics
  (`name`, `logicalType`, `physicalType`, `required`, `description`) plus
  first-class `mappingRole`: one of `dimension`, `measure`, `time`.
  Exactly one field carries role `time`, and it must be the `timeColumn`.
- `grain` (first-class object, one of two shapes):
  - **`type: transaction`** with `degenerateIdentifiers`, a non-empty
    array. Each entry is either `source: column` naming a declared field
    to be carried in the dimension payload for content-key uniqueness
    (a field may be so named regardless of its role; a measure that is
    part of the declared silver grain tuple may deliberately appear in
    both payloads), or `source: derived` with `name`, `derivation:
    canonical-key-v2`, and `of` (the declared fields hashed into one
    content-derived line identity). The schema expresses both candidate
    forms; the category instance picks one, citing the silver contract's
    grain declaration.
  - **`type: aggregated`** with `aggregations` (a map of measure name to
    one of sum, min, max, avg, count). The engine adds the standard
    `_row_count` measure so conservation stays checkable by arithmetic.
- `customProperties` carry provenance and rationale ONLY: `proposedBy`,
  `profileHash` (the silver profile artifact this mapping was authored
  from; for `invoice_lines`, silver profile v0001), `proposedAt`, and the
  proposer keys per the agent-layer Appendix B when an agent authored the
  draft. Rationale entries are welcome; mapping semantics are not.
- **No quality rules, anywhere in a mapping contract.** Gate 3 resolves
  schema objects to dbt models by name and skips unmatched objects before
  quality-rule translation (F-12), so a rule here would never run, a dead
  letter inviting false confidence. The JSON Schema rejects `quality` on
  the category object and on every field. Enforcement belongs to the gold
  star contract, whose objects are all modeled.

### Placement and the gates (the flat-glob rules)

Verified end to end at the pinned toolchain (F-12, F-13):

- Gate 1 lints every `contracts/*.odcs.yaml` including mapping contracts;
  a mapping contract must lint clean. Verified: the first-class shape does.
- Gate 3 syncs and tests the same flat glob. A model-less contract is
  skipped per schema object with a stderr warning, `Synced 0 models`,
  `no tests`, exit 0, zero files written, zero effect on sibling
  contracts. Flat placement is permanent-safe; no CI change and no D-12
  amendment is needed.
- **Naming rule (load-bearing):** the category name must never equal a dbt
  model name. The collision is loud and fail-safe: sync and test both
  exit 1 with `Cannot sync — overlapping dbt models` and write nothing
  (F-12, probe P1c), but it reddens the gate, so the rule is structural:
  category names are bare nouns; every emitted model carries a `dim_`,
  `fact_`, `vw_`, or `mart_` prefix or the reserved name
  `context_registry`; the JSON Schema rejects category names matching any
  of those patterns, and the reader re-checks (defense in depth).

### The Phase 6 hook (the agent-layer obligation, discharged)

The gold mapping proposer (Phase 6) emits its structured proposal against
a **proposal schema projected from this schema**
([`docs/spec/agent-layer/gold-mapping-proposal.schema.json`](agent-layer/gold-mapping-proposal.schema.json))
via `output_config.format: json_schema`, and **this schema validates the
rendered output** (D-21 as amended by Amendment F;
[F-26](../verification/gate_proof_findings.md#f-26): the API's JSON
Schema subset cannot compile the composition keywords this schema is
built from). Freezing the schema here discharges the agent layer's
Phase 4 obligation: degenerate identifiers, grain, roles, and provenance
are first-class, machine-consumed elements, so the proposal-to-ODCS
render in the harness is deterministic and every valid proposal renders
to exactly one document this schema accepts. A schema change after this
point is a spec amendment with a version bump, in its own documentation
PR, and it re-derives the projection in the same PR.

## 3. Keys: the dual-implementation rule (D-18)

All keys are canonical_key v2. Where they compute is split by what they
depend on:

- **Record keys** (values-dimension and fact content keys) are
  data-dependent: computed **in SQL inside the emitted models at build
  time**: `sha256(lower(to_json(<payload struct>)))` over the canonical
  payload.
- **Schema keys** (columns-dimension manifest keys) are contract-derived:
  computed **in Python at emission time** and embedded in the emitted SQL
  as literals: `sha256` over the lowercased compact JSON array of the
  manifest in declared order.

Because the same value must be computable on both paths, the rule is
dual implementation with proof: `src/metricmine/keys.py` is the Python
reference implementation; committed golden vectors
(`tests/golden/canonical_key_v2.json`) pin the answers; a consistency test
executes the SQL path against in-memory DuckDB and asserts byte-for-byte
agreement with the Python path on every vector. DuckDB is an explicit
runtime dependency, so this test runs keyless in the CI pytest lane.

Function-level semantics were probed live at the pinned engine (F-11) and
the following are therefore requirements, not hopes:

1. **Sorted payload fields are an emission-time property.** DuckDB's
   `to_json` preserves struct insertion order and does not sort. The
   emitter writes payload struct fields pre-sorted (Unicode codepoint
   order over the lowercased field names); nothing relies on the engine
   function sorting.
2. **Payload values render as canonical text, not native JSON numbers.**
   Every payload value is cast to VARCHAR by the canonical rendering
   before serialization, so the payload is a JSON object of strings (or
   JSON null). Rationale: DECIMAL as a JSON number would collapse scale
   (2.50 to 2.5) and float repr is platform-hostile; VARCHAR casts are
   scale-preserving ("2.50" stays "2.50", F-11). TIMESTAMP renders
   "YYYY-MM-DD HH:MM:SS". The Python reference renders decimals with
   `decimal.Decimal`, never float repr, and matches both renderings
   exactly; the golden vectors include decimal and timestamp cases.
3. **Payload nulls are included as JSON null** (include-as-null, decided
   here): a declared field whose value is NULL appears in the payload as
   `"field": null`, which is exactly what `to_json` over a struct with a
   NULL member emits (F-11). Include-as-null keeps every declared field
   present in every payload, keeps the SQL path free of per-row key
   filtering, and keeps payload shape congruent with the manifest. The
   golden vectors cover it.
4. **Lowercasing is applied to the full serialization** and is
   unicode-safe over JSON text at the pinned engine (F-11); parity between
   Python `str.lower()` and DuckDB `lower()` is vector-verified.
5. Scalars and manifests: cast to text, lowercase, strip whitespace,
   hyphens preserved; manifests serialize as compact JSON arrays in
   declared order (D-18, unchanged).

The timeframe dimension payload derives from `timeColumn` truncated to
`timeGrain` (`date_trunc` at the declared grain), then rendered canonically
like every other payload value.

## 4. Registry population (D-30)

The gold spec places the registry's content with the context compiler and
its materialization with the engine. The mechanism, decided here:

1. The **context compiler** (`src/metricmine/context/`) merges the
   governing contracts and their harvested context fields (silver contract,
   mapping contract, gold star contract, and the profile references they
   cite) into one **compiled-context artifact**:
   `context/compiled/vNNNN.json` plus a `vNNNN.meta.json` sidecar:
   canonical JSON, deterministic content only, write-if-changed, immutable
   monotonic versions. The same artifact discipline as `profiles/`, and
   the same reason: a committed, reviewable, versioned input.
2. The **engine emits `context_registry` as a dbt model whose rows are
   SQL VALUES literals** carried from the compiled-context artifact at
   emission time: `schema_key`, `entity_group`, `contract_name`,
   `contract_version`, `compiled_context` (canonical JSON text). String
   literals are escaped deterministically (single-quote doubling).
3. Consequences, and the reason this mechanism won: every warehouse write
   stays inside `dbt build`; there are **no build-time file reads**, so
   the F-09 working-directory disease cannot reach the registry (gate 3
   re-invokes dbt from inside `transform/`, where a relative artifact path
   would break); the demo path stays keyless and byte-reproducible; C3
   stays a gate-capable test; and a registry change is visible as a
   reviewable model diff in a regeneration PR, under the manifest.

A context change (a contract amendment, new harvested context) mints the
next compiled-context version; the engine re-emits the registry model from
it; the diff arrives as a regeneration PR (D-09).

## 5. Emission mechanics

- **Inputs:** the mapping contract (validated against the JSON Schema,
  then cross-checked), the gold star contract, and the compiled-context
  artifact version pinned for the registry.
- **Reader cross-checks beyond the JSON Schema** (the engine's static
  groundedness, all fail-closed): every mapped field exists in the silver
  contract named by `sourceTable`; `timeColumn` is declared with role
  `time` and exists in the silver contract; every `grain` reference
  (`degenerateIdentifiers` columns, `of` lists, `aggregations` keys)
  names a declared field; measures are numeric logical types; the
  category name violates no reserved pattern.
- **Outputs (the emission set: category-parameterized tables plus the
  star-global objects):** `dim_<category>_values.sql`,
  `dim_<category>_columns.sql`, the shared group dims
  (`dim_source_*`, `dim_run_*`, `dim_timeframe_*`), the fact
  `fact_<category>_values.sql`, `context_registry.sql`, the typed
  surface per `engine.marts` (D-36: `mart_<category>_typed.sql` under
  `table` or `both`, `vw_<category>_typed.sql` under `view` or `both`;
  the committed default is `both`; an unrecognized value fails closed),
  and **one properties yml per emitted model**
  at the sync fixed point (section 6). The set follows the gold
  contract's object catalog: star tables always; `context_registry` and
  the typed surface join it once the contract declares
  `context_registry` (the extended-star activation, F-20 era), and the
  ownership manifest then pins the compiled-context artifact version. `dim_run` payload carries the
  mapping contract name and version and the engine version, lineage as
  deterministic content (D-17); audit stamps (`loaded_at`) stay plain
  columns outside every hashed payload.
- **Generated-by headers** (D-09), exact form, first two lines of every
  emitted file (`--` for SQL, `#` for YAML):

  ```
  -- Generated by metricmine-engine v<engine_version> from <mapping_contract_id> v<version> + gold_unified_event_star v<version>.
  -- Engine-owned (D-09): do not edit; flag drift instead (rule 8). Spec: docs/spec/engine.md.
  ```

  Projections replace the second line with the derivative label:
  `-- Derivative typed projection over the star; uncontracted by design (D-17). Do not edit; flag drift instead (rule 8).`
  The mart replaces it with its own:
  `-- Derivative typed mart over the star; uncontracted by design (D-17 as amended by D-36). Do not edit; flag drift instead (rule 8).`
  Headers survive sync verbatim (F-14).
- **Ownership manifest:** `transform/models/gold/ownership-manifest.json`,
  canonical JSON, deterministic content only (no timestamps; regeneration
  must be byte-reproducible): `engine_version`, `sources` (mapping
  contract id + version, gold contract id + version, compiled-context
  version), and `files` mapping each emitted path to `sha256:<hex>` over
  its fixed-point bytes. The manifest never lists itself.
- **Write discipline:** compute the full emission set in memory; validate
  everything; **drift-check before writing**: any target file whose
  current bytes diverge from its manifest baseline is human-owned now
  (rule 8): the engine refuses to overwrite it, names it, and exits
  nonzero; then write-if-changed per file (byte compare; temp-then-rename
  in the same directory, the established writer discipline), manifest
  last. No partial emission: any failure exits nonzero with nothing
  written.
- **Idempotency, now a testable claim:** engine re-run over unchanged
  inputs writes nothing and leaves `git status` clean. This claim is only
  meaningful because emission targets the sync fixed point; see section 6.
- **Interface:** `uv run python -m metricmine.engine.emit`, config-driven
  from an `engine:` block in `config/default.yaml`, no CLI arguments (the
  ingest and profile posture). `make regen` wraps it. Beside
  `engine.marts` (D-36), `engine.materialization` selects `table`, the
  committed default, or `incremental` (D-38); an unrecognized value
  fails closed before anything emits. The emitted SQL is one shape in
  both modes: every model carries an explicit config line and inert
  `is_incremental()` blocks (the `captured_at >=` watermark filter on
  the silver-derived models and the content-key anti-join on every
  insert), so a mode flip regenerates as one config-line diff per
  model. Incremental config lines add `on_schema_change='fail'`
  (F-34).
- **Unit surface (CI lane):** emission determinism (same contracts, byte-
  identical files), golden emitted-file fixtures, the SQL-versus-Python
  keying consistency test, JSON Schema validation of the example mapping
  contract, and reader cross-check rejection cases.

## 6. The sync fixed point (Q8; F-14)

Gate 3's `datacontract dbt sync` edits properties files in place (F-05).
If sync modified an engine-emitted file, the file's manifest checksum
would diverge and the engine would flag its own gate as drift. The
resolution, verified by probe: **the engine emits the post-sync fixed
point directly**, and manifest checksums are defined over that state.
Sync then has nothing to add: pass 2 over the fixed point updates zero
files, byte-identically (F-14).

What the fixed point requires of the emitter, exhaustively at the pinned
toolchain (F-14):

1. Every description, model-level and column-level, is emitted from the
   governing contract, verbatim. Measured, not assumed: with deliberately
   divergent emitter texts, sync replaced the model description and every
   column description with the contract's text (the F-14 delta diff);
   emitting anything else guarantees a first-sync diff.
2. The `config.meta.datacontract_cli.contract_id` binding and
   `contract.enforced: true` are emitted by the engine itself.
3. Every `required: true` column carries the sync-shaped
   `data_tests: - not_null:` block verbatim: `config.severity: warn`,
   `config.meta.datacontract_cli` with
   `check: <model>__<column>__field_required`, `include_in_tests: true`,
   `contract_versions: [<contract_version>]`, `generated: true`, and the
   description `Check that field <column> has no missing values`. A
   column flagged `primaryKey: true` ALONE additionally carries the
   sync-shaped `unique:` twin (`check: <model>__<column>__field_unique`,
   description `Check that field <column> has no duplicate values`);
   composite keys generate only the sync-owned `unique_combination`
   singular test (F-17).
4. Columns carry `name`, `data_type` (all-or-nothing, rule 4), and
   `constraints: - type: not_null` for required columns (only not_null is
   a trusted constraint, rule 5).
5. The emitted properties files carry **nothing else**. In particular the
   engine emits no data_tests of its own invention: enforcement rides the
   gold contract's severity-declared quality rules (section 7), so the
   fixed-point delta list above stays exhaustive.

Singular test files under `transform/tests/datacontract_cli/` are
**sync-owned** (their header says "AUTO-GENERATED by `datacontract dbt
sync`. Do not edit."), are left byte-identical by a second sync at the
fixed point, and sit **outside the engine's ownership manifest**. They stay under the
committed-post-review discipline that governs them today (F-05, F-08,
rule 11): the regeneration PR author runs sync, reviews the generated
tests, deleting any duplicateValues mistranslation on sight, and
commits the reviewed state.

The pre-regeneration rehearsal re-verifies sync no-op over the real
emitted star before the first regeneration PR goes live.

## 7. Test placement (conservation as contract severity)

All gate-capable enforcement on gold lives as **error-severity sql quality
rules in the gold star contract**, generated into singular tests by sync,
the one channel proven to gate at the pinned toolchain (D-28, F-08), and
the channel the partially-modeled probe verified end to end (F-13):

- **C1** conservation arithmetic: silver rows in scope equal fact rows
  (transaction grain) or `sum(_row_count)` (aggregated grain), referencing
  silver by schema-qualified SQL (the F-08 nuance: such tests
  catalog-error loudly, rather than skip, when a referenced table is
  missing: a louder red, same verdict).
- **C2** key resolution: one anti-join rule per fact group key (source,
  timeframe, dim, plus the non-key run reference and the manifest's
  columns-dim reference), each requiring zero unresolved keys. The gold
  spec's C2 assertion is unchanged; the mechanism is the contract rule,
  for two stated reasons: contract-declared severity is the one channel
  proven to gate at this pin (D-28, F-08), and emitting dbt-native
  relationship tests into the properties files would break the
  fixed-point exhaustiveness F-14 rests on (section 6, rule 5). The gold
  spec's mechanism parenthetical is aligned by a one-line edit traveling
  with this spec's PR.
- **C3** registry coverage: every schema key present in gold exists in
  `context_registry`. Declared on the registry object; it becomes live
  the moment the registry model lands (F-13 records the one-PR window in
  which it is declared but not yet running; skip is no coverage, not
  passing coverage).
- **C4** payload validity: `json_valid` over every values payload
  (function behavior verified, F-11).
- **C5** field-level reconciliation (V1-06, star contract v1.3.0):
  every silver row joins the typed surface on the derived line
  identity and every mapped field matches its served value,
  null-safe, with text fields compared lowercased per D-18 and the
  time column at the declared grain.
- **Grain enforcement** on the fact at transaction grain: zero duplicate
  content-key tuples, the error-severity twin of the composite PK flags
  (whose generated composite test is hardcoded warn, F-08).

The emitted properties files carry none of this (section 6.5): contracts
declare enforcement, sync generates it, review approves it.

The twelve expensive rules carry the `mm_batch_floor` guard in their
contract SQL (D-39): unset, CI included, they run full-table exactly
as declared; an incremental deployment passes its batch floor to
scope them, cross-batch guarantees riding the D-38 anti-join inserts;
`make audit-gold` runs the unscoped forms on demand. Sync carries the
jinja guards verbatim into the generated singular tests (F-35).

## 8. Ownership boundary (Amendment C to D-16; rule 11 scoped)

Hand-authored properties files govern the human-owned plane: silver.
Engine-emitted properties files govern engine-owned models: gold star
tables and the registry, emitted at the sync fixed point, reviewed as
generated code in regeneration PRs against an expected-file list, under
the ownership manifest. The review obligations rule 11 exists for are
unchanged on both planes: sync output is a proposal until reviewed;
`export dbt-models` output remains scaffold only; the duplicateValues
deletion rule stands. What changes is only who authors the bytes on the
gold plane, and that authorship is exactly what D-07 and D-09 exist to
govern.

## 9. Provenance for non-profile-derived contracts (Q9)

Rule 16's provenance keys assume a profile-derived contract. Two honest
cases exist in Phase 4:

- The **mapping contract** IS profile-derived: it carries
  `profileHash` of the silver profile artifact it was authored from
  (silver v0001), with `proposedBy: human` and `proposedAt`.
- The **gold star contract** is pattern-derived: authored from the
  unified event star specification, not from any profile artifact. It
  carries the standard keys with `profileHash` **absent**, plus
  `provenanceNote: pattern-derived; authored from
  docs/spec/gold-unified-event-star.md, not from a profile artifact; no
  profileHash exists`. Absence-with-rationale extends the agent layer's
  Appendix B absent-for-humans pattern; fabricating a hash would violate
  rule 16's own point.

## 10. Layout

```
src/metricmine/
├── keys.py                  # canonical_key v2 reference (shared; lands before the engine)
├── engine/
│   ├── __init__.py          # engine version constant (semver; starts 0.1.0)
│   ├── emit.py              # entry point: python -m metricmine.engine.emit
│   ├── reader.py            # contract loading, JSON Schema validation, cross-checks
│   ├── emitters.py          # dims / fact / registry / projection / properties emission
│   └── manifest.py          # ownership manifest read, drift check, write
├── context/                 # context compiler (compiled-context artifact)
docs/spec/engine/
├── mapping-contract.schema.json
└── example-mapping-contract.odcs.yaml
context/compiled/            # vNNNN.json + vNNNN.meta.json (committed artifacts)
transform/models/gold/       # emitted models + properties + ownership-manifest.json
tests/golden/canonical_key_v2.json
```

`src/metricmine/modeling/` is the empty pre-spec placeholder package; this
spec names `src/metricmine/engine/` as the engine's home, and removing the
placeholder is a standalone chore, not part of any ladder PR.

## 11. Explicitly out of scope

Everything the gold spec excludes (partitioning, multiple dimension
groups per category, performance claims),
plus: the engine never reads the warehouse (it reads contracts and the
compiled-context artifact; conservation numbers come from dbt tests, not
engine queries); no template language or plugin surface (emitters are
plain Python); no multi-source fan-in (one mapping contract, one silver
table, one category; more source types stay a standing non-goal); no
engine-side scheduling (regeneration is a human-invoked make target
landing as a PR).

## References

- [`docs/spec/gold-unified-event-star.md`](gold-unified-event-star.md):
  the star this engine builds; object catalog, keying scheme, conservation
  ledger, signature property.
- [`docs/spec/agent-layer.md`](agent-layer.md): the Phase 6 proposer that
  will emit proposals against this spec's JSON Schema; Appendix B
  provenance keys.
- [`docs/spec/profiler.md`](profiler.md): the artifact discipline the
  compiled-context artifact mirrors; the silver profile the mapping
  contract cites.
- [`docs/verification/gate_proof_findings.md`](../verification/gate_proof_findings.md):
  F-11 (function semantics), F-12 (flat placement), F-13 (partial
  modeling), F-14 (sync fixed point), atop F-01 through F-10.
- Project records (design history outside the repository; nothing here
  depends on them): Gold Layer Design 001 (July 11, 2026) and Phase 4
  Runbook 002 Rev 1 (August 1, 2026). The probe transcript and its raw
  logs are NOT project records: they are committed evidence in this
  repository, cited above.
