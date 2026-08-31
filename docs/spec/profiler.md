# Profiler Component Specification

**Status:** adopted (spec PR, issue #21). Implements in Phase 3
(issue #22).
**Governing decisions:** [D-11](../decisions/decision-register.md#d-11)
(read-only warehouse protocol), [D-23](../decisions/decision-register.md#d-23)
(profile artifact as sole agent context),
[D-04](../decisions/decision-register.md#d-04) (profiler outside dbt),
[D-03](../decisions/decision-register.md#d-03) (warehouse files),
[D-25](../decisions/decision-register.md#d-25) (golden-profile evaluation).

Boundary, stated once and binding everywhere below: the profiler describes
bronze, the input; contracts govern silver, the output. The profiler
proposes, never decides. It reads the warehouse strictly read-only and never
writes to it.

## 1. Purpose and consumers

The profiler is deterministic standalone Python (D-04, CLAUDE.md rule 3): it
carries no contract because its output is a reviewable artifact, not a
table. It turns one bronze table into one committed, versioned JSON profile
artifact. Three consumers, in the order they arrive:

1. **The human authoring the silver contract (Phase 3).** The profile is the
   evidence sheet: observed types, null rates, cardinality, ranges, and
   duplicate-row rate, read instead of ad-hoc warehouse queries.
2. **The two contract-proposer agents (Phase 6).** Per D-23 the proposers
   use no retrieval; the profile artifact is the SOLE context, injected
   complete into the call ([agent layer spec](agent-layer.md)). Every
   proposal is bound to the `content_hash` of the profile it consumed; a
   regenerated profile fails the staleness check. This spec discharges the
   debt D-23 records: deterministic serialization, a `schema_version`
   field, a content hash, and token-budget caps.
3. **Tests.** Committed profiles serve as fixtures, including the
   golden-profile evaluation set, whose location D-25 fixes; this spec
   only guarantees the artifacts are deterministic and committable.

## 2. Authority: what the profiler may propose

The profiler reports observable facts; a human owns every normative
judgment. By ODCS 3.1.0 field group:

| ODCS 3.1.0 field group | Profiler can propose | Human judgment only |
| --- | --- | --- |
| Physical names (`name`, schema/table binding) | ✔ observed | |
| Physical types (`physicalType`) | ✔ observed | |
| Nullability (`required`) | ✔ evidence: null counts and rates | |
| Uniqueness (`unique`, uniqueness quality checks) | ✔ evidence: distinct counts vs row count | |
| Example values (`examples`) | ✔ deterministic capped samples | |
| Observed ranges (min/max toward `validValues`-style checks) | ✔ numeric and temporal columns | |
| Descriptions and business meaning (`description`, `businessName`) | | ✔ |
| Cleanup and filtering rules (transform logic) | | ✔ |
| Quality thresholds (`quality` severities and limits) | | ✔ |
| Classification (`classification`) | | ✔ |
| SLAs (`slaProperties`) | | ✔ |
| Ownership (`team`, ownership fields) | | ✔ |

Evidence is not a decision: a zero null count is grounds for a human (or,
in Phase 6, a proposer subject to human approval) to declare `required`,
never a declaration by itself. In Phase 6 this table becomes the cleanup
proposer's job description: the left column is what it may fill from the
profile, the right column is what review holds. The `describe` stance
(D-35) reads the same table over a table's own profile: it may fill the
left column from evidence and may propose, never decide, the right.

## 3. The profile artifact

One JSON document per profiled table. Top-level layout:

- `schema_version`: semver string for the artifact schema itself; starts
  at `"1.0.0"`. Additive fields bump minor; anything else bumps major.
- `content_hash`: `"sha256:<hex>"` (64 hex chars) over the canonical
  serialization of the `dataset` section only. `schema_version`, `caps`,
  and the sidecar are outside the hashed region; versioning nonetheless
  keys on the whole artifact (section 6). This hash is the value the
  agent layer's provenance and proposal records carry as `profileHash` /
  `profile_hash`: one field, same `sha256:<hex>` format everywhere.
- `caps`: the token-budget constants in force when the profile was
  produced (section 5), echoed so a reader never guesses which limits
  shaped the artifact.
- `dataset`: the canonical body:
  - `schema`, `table`: the profiled relation.
  - `row_count`: total rows.
  - `duplicate_row_rate`: defined below.
  - `columns`: an array in warehouse ordinal order. Each entry: `name`,
    `physical_type`, `null_count`, `null_rate`, `distinct_count`, `min`
    and `max` (present for numeric and temporal types only; temporal
    values serialize as ISO 8601 strings), `sample_values`
    (deterministic, capped per section 5; omitted when `distinct_values`
    is present, which it would merely duplicate), `distinct_values` (the
    full value list, present only when `distinct_count` is at or under
    the cap), and `is_airbyte_metadata` (true for `_airbyte_*` columns).
    Inapplicable fields are omitted, never null.

`duplicate_row_rate` is computed over source columns only, excluding
`_airbyte_*` columns: `(row_count − distinct source-column rows) /
row_count`, rounded per the float rule (section 4). Its purpose is grain
evidence: it feeds the mapping contract's grain declaration, aggregated
(with `_row_count`) versus transaction (with a degenerate id), per the
"Fact key and grain" section of the
[gold spec](gold-unified-event-star.md). A nonzero rate means the source
rows are not unique as a tuple, so the category either aggregates or needs
a degenerate identifier.

One consequence worth stating: because `min`/`max` applies to numeric and
temporal types only and `invoicedate` lands VARCHAR in bronze, the
artifact carries only the low end of its date range: ascending
`sample_values` show the earliest values, and nothing marks the last.
Full date-range evidence arrives once silver casts the column and
`min`/`max` applies.

### Annotated example

> **Every statistic below is illustrative.** The shape is normative; the
> numbers, sample values, and hash are invented to show that shape. Only
> `row_count: 45228` and the column names and physical types are real
> (they match the landed bronze table). The first measured profile,
> `v0001`, is minted by the implementation PR (issue #22).

```json
{
  "caps": {
    "max_distinct_values": 20,
    "max_sample_values": 10,
    "max_string_chars": 120
  },
  "content_hash": "sha256:6b1e0c9a4d7f2358e6a09c4b1d8f7e23a5c091b64d2e8f7a3c5019b8d4e6f2a7",
  "dataset": {
    "columns": [
      {
        "distinct_count": 2010,
        "is_airbyte_metadata": false,
        "name": "invoice",
        "null_count": 0,
        "null_rate": 0.0,
        "physical_type": "VARCHAR",
        "sample_values": ["489434", "489435", "489436", "489437", "489438",
                          "489439", "489440", "489441", "489442", "489443"]
      },
      {
        "distinct_count": 3661,
        "is_airbyte_metadata": false,
        "name": "stockcode",
        "null_count": 0,
        "null_rate": 0.0,
        "physical_type": "VARCHAR",
        "sample_values": ["10002", "10080", "10109", "10120", "10123C",
                          "10124A", "10124G", "10125", "10133", "10135"]
      },
      {
        "distinct_count": 3667,
        "is_airbyte_metadata": false,
        "name": "description",
        "null_count": 590,
        "null_rate": 0.013045,
        "physical_type": "VARCHAR",
        "sample_values": ["10 COLOUR SPACEBOY PEN", "12 COLOURED PARTY BALLOONS",
                          "12 DAISY PEGS IN WOOD BOX", "12 EGG HOUSE PAINTED WOOD",
                          "12 HANGING EGGS HAND PAINTED", "12 IVORY ROSE PEG PLACE SETTINGS",
                          "12 MESSAGE CARDS WITH ENVELOPES", "12 PENCILS SMALL TUBE RED RETROSPOT",
                          "12 PENCILS SMALL TUBE SKULL", "12 PENCILS TALL TUBE POSY"]
      },
      {
        "distinct_count": 331,
        "is_airbyte_metadata": false,
        "max": 19152.0,
        "min": -9360.0,
        "name": "quantity",
        "null_count": 0,
        "null_rate": 0.0,
        "physical_type": "DECIMAL(38,9)",
        "sample_values": [-9360.0, -1930.0, -1440.0, -720.0, -600.0,
                          -288.0, -240.0, -192.0, -144.0, -100.0]
      },
      {
        "distinct_count": 1801,
        "is_airbyte_metadata": false,
        "name": "invoicedate",
        "null_count": 0,
        "null_rate": 0.0,
        "physical_type": "VARCHAR",
        "sample_values": ["2009-12-01 07:45:00", "2009-12-01 07:46:00",
                          "2009-12-01 09:06:00", "2009-12-01 09:08:00",
                          "2009-12-01 09:24:00", "2009-12-01 09:28:00",
                          "2009-12-01 09:34:00", "2009-12-01 09:42:00",
                          "2009-12-01 09:45:00", "2009-12-01 09:46:00"]
      },
      {
        "distinct_count": 480,
        "is_airbyte_metadata": false,
        "max": 10953.5,
        "min": 0.0,
        "name": "price",
        "null_count": 0,
        "null_rate": 0.0,
        "physical_type": "DECIMAL(38,9)",
        "sample_values": [0.0, 0.06, 0.1, 0.12, 0.19, 0.21, 0.25, 0.29, 0.3, 0.32]
      },
      {
        "distinct_count": 955,
        "is_airbyte_metadata": false,
        "max": 18287.0,
        "min": 12346.0,
        "name": "customer_id",
        "null_count": 10759,
        "null_rate": 0.237884,
        "physical_type": "DECIMAL(38,9)",
        "sample_values": [12346.0, 12347.0, 12348.0, 12349.0, 12352.0,
                          12356.0, 12357.0, 12358.0, 12359.0, 12360.0]
      },
      {
        "distinct_count": 19,
        "distinct_values": ["Australia", "Austria", "Belgium", "Channel Islands",
                            "Cyprus", "Denmark", "EIRE", "France", "Germany",
                            "Greece", "Italy", "Lithuania", "Netherlands",
                            "Norway", "Poland", "Portugal", "Spain", "Sweden",
                            "United Kingdom"],
        "is_airbyte_metadata": false,
        "name": "country",
        "null_count": 0,
        "null_rate": 0.0,
        "physical_type": "VARCHAR"
      },
      {
        "distinct_count": 45228,
        "is_airbyte_metadata": true,
        "name": "_airbyte_raw_id",
        "null_count": 0,
        "null_rate": 0.0,
        "physical_type": "VARCHAR",
        "sample_values": ["01J00A3V0R8Z9K2M4P6Q8S0T1V", "01J00A3V0R8Z9K2M4P6Q8S0T2W",
                          "01J00A3V0R8Z9K2M4P6Q8S0T3X", "01J00A3V0R8Z9K2M4P6Q8S0T4Y",
                          "01J00A3V0R8Z9K2M4P6Q8S0T5Z", "01J00A3V0S1A2B3C4D5E6F7G8H",
                          "01J00A3V0S1A2B3C4D5E6F7G9J", "01J00A3V0S1A2B3C4D5E6F7GAK",
                          "01J00A3V0S1A2B3C4D5E6F7GBL", "01J00A3V0S1A2B3C4D5E6F7GCM"]
      },
      {
        "distinct_count": 1,
        "distinct_values": ["2026-07-26T18:04:11"],
        "is_airbyte_metadata": true,
        "max": "2026-07-26T18:04:11",
        "min": "2026-07-26T18:04:11",
        "name": "_airbyte_extracted_at",
        "null_count": 0,
        "null_rate": 0.0,
        "physical_type": "TIMESTAMP"
      },
      {
        "distinct_count": 1,
        "distinct_values": ["{\"changes\": [], \"sync_id\": 26}"],
        "is_airbyte_metadata": true,
        "name": "_airbyte_meta",
        "null_count": 0,
        "null_rate": 0.0,
        "physical_type": "JSON"
      }
    ],
    "duplicate_row_rate": 0.000199,
    "row_count": 45228,
    "schema": "bronze",
    "table": "online_retail_ii"
  },
  "schema_version": "1.0.0"
}
```

Walkthrough, keyed to the example:

- **Keys are sorted everywhere; only `columns` carries meaning in its
  order** (warehouse ordinal order, section 4). Key order matches the
  canonical serialization; arrays are wrapped here for page width, where
  the canonical form puts one element per line.
- **`quantity.sample_values`** shows the ascending-order rule's effect on
  numerics: samples are the low tail (here, cancellation quantities);
  `min`/`max` carry the range. Both together are the evidence.
- **`invoicedate`** has no `min`/`max` because it is VARCHAR, the
  consequence stated above. Its samples are the date-range evidence.
- **`country`** sits at or under the distinct-values cap, so the full
  sorted `distinct_values` list appears and `sample_values` is omitted
  as redundant (section 3).
- **`customer_id`** shows nullability evidence (`null_count`,
  `null_rate`) the silver contract author will weigh; the profiler does
  not declare `required` either way.
- **The three `_airbyte_*` columns** are profiled and flagged
  `is_airbyte_metadata: true`, and are excluded from
  `duplicate_row_rate`.
- **`duplicate_row_rate`** here says roughly 9 of 45,228 source-column
  rows are exact duplicates: grain evidence that the invoice-line tuple is
  not unique as landed.

## 4. Determinism rules

Testable requirement: two profiler runs over identical bronze produce
byte-identical artifacts. The rules that guarantee it:

1. **Canonical JSON.** UTF-8, sorted keys, 2-space indent, `ensure_ascii`
   false, single trailing newline.
2. **Ordering.** `columns` is in warehouse ordinal order; every other list
   (`sample_values`, `distinct_values`) is explicitly sorted. String
   ordering is Unicode codepoint order: no locale collation, no case
   folding; an engine ORDER BY must be pinned to it (binary collation) or
   the sort happens in Python, so a DuckDB or ICU change cannot shift the
   artifact.
3. **Samples.** `sample_values` is the first N distinct non-null values in
   ascending value order: a fixed ORDER BY, no randomness, and never a
   LIMIT without an ORDER BY.
4. **Floats.** Rounded to 6 decimal places before serialization. This spec
   fixes the float rule for profile artifacts; bronze's `DECIMAL(38,9)`
   columns make it load-bearing.
5. **No profiler-injected time.** The profiler writes nothing
   time-dependent of its own into the artifact: no run timestamp, no
   build id. Run metadata (timestamp, library versions) lives in a
   sidecar `vNNNN.meta.json` that is exempt from the determinism
   guarantee. Observed values of audit-stamp columns
   (`_airbyte_extracted_at`) are source data, not artifact metadata, and
   stay. The guarantee is over identical bronze: re-landing bronze
   legitimately changes those values, and with them the content hash:
   accepted behavior; re-landed bronze is new bronze.
6. **Write-if-changed.** When the newly serialized artifact is
   byte-identical to the newest committed `vNNNN.json`, the profiler
   writes nothing; a rerun over unchanged bronze leaves `git status`
   clean. The comparison is over the whole artifact, not `content_hash`
   alone, so a caps or `schema_version` change mints a new version even
   when the dataset bytes are unchanged.

This mirrors the canonical_key v2 discipline (CLAUDE.md rule 13): hashed
payloads carry deterministic content only; audit stamps stay outside. The
`content_hash` itself is an artifact checksum, not a warehouse hash key;
canonical_key v2 governs warehouse keys and is untouched here.

## 5. Token-budget caps

Versioned profiler constants, echoed verbatim in the artifact's `caps`
block; changing any of them is a profiler version change:

| Constant | Value | Effect |
| --- | --- | --- |
| `max_sample_values` | 10 | at most 10 sample values per column |
| `max_distinct_values` | 20 | `distinct_values` emitted only when `distinct_count <= 20` |
| `max_string_chars` | 120 | longer strings cut at 120 chars and suffixed `…[truncated]` |

`max_string_chars` governs every emitted string value, `sample_values`
and `distinct_values` alike, and applies after distinctness is computed,
so `distinct_count` stays authoritative even when truncation collapses
two long values to the same emitted string. The `…[truncated]` marker is
deliberately in-band: a truncated sample that reaches a proposed
contract's `examples` field stays visibly marked, and the human reviewer
strips or replaces it before approval.

Worst-case size arithmetic (D-23): a column emits either up to 10 samples
or, at or under the distinct cap, up to 20 distinct values: at most 20
strings of ≤120 characters, about 2,400 characters, roughly 600 tokens at
~4 characters per token, call it ~750 with keys and punctuation.
Table-level fields are noise. Even a 40-column table lands near 30k
tokens, inside the case the [agent layer spec](agent-layer.md) already
prices: "A bounding case (profile near the 30k-input-token cap, contract
near 5k output tokens) prices under roughly twenty cents at standard
rates." `bronze.online_retail_ii`, at 11 columns mostly far under the
caps, runs a few thousand tokens.

Sample values are untrusted source data carried verbatim (agent layer
spec, threat model). Truncation is a budget control, not a security
control; the prompt-side delimiting and the deterministic validator carry
that defense.

## 6. Artifact versioning

- Path: `profiles/<schema>.<table>/vNNNN.json`, with the sidecar
  `vNNNN.meta.json` beside it. The repo-root `profiles/` directory is
  committed (it exists today with a `.gitkeep`). It is unrelated to dbt's
  connection profiles, which arrive as `transform/profiles.yml` with the
  dbt project PR.
- Artifacts are immutable once committed and monotonically numbered. Any
  changed artifact byte (dataset, caps, or `schema_version`) mints the
  next number (determinism rule 6); an existing file is never edited.
  `v0001` is a table's first profile.

## 7. Read-only warehouse protocol (D-11)

D-11 places a thin read-only protocol in `src/metricmine/warehouse/`; the
profiler is its first consumer, so the protocol is specified here. Its
second consumer, the shared query module serving gold, arrives later and
will extend the protocol with serving methods of its own; the six
profiling methods below are that surface, not the whole of D-11.
`relation_kinds` joins at Phase 6 for the adoption scan (D-35).

- `src/metricmine/warehouse/base.py` (created by the implementation PR)
  defines a thin engine-agnostic protocol (D-11's "~5 methods"), now seven:
  `list_tables`, `columns`, `row_count`, `column_profile`, `sample_values`,
  `duplicate_row_count`, and `relation_kinds` (name to `table` or `view`
  per schema). `relation_kinds` exists because information_schema.tables
  lists views beside base tables, so `list_tables` alone cannot tell them
  apart; the adoption scan needs the distinction to classify models
  without reaching past the protocol (adoption lab, August 21, 2026).
- The DuckDB implementation opens the warehouse with `read_only=True`.
  No DDL, no DML. The profiler cannot write to the warehouse even by
  accident; its only outputs are files under `profiles/`.

## 8. Scope, interface, failure modes

Scope, in full:

- Profiles `bronze.online_retail_ii` and, from the gold phase,
  `silver.silver_invoice_lines`, the silver pass the runtime workflow
  diagram records, run by the same code over the silver schema. The
  `profiling` config block becomes a list of targets, one artifact
  directory per table (`profiles/silver.silver_invoice_lines/v0001.json`
  at first mint). The silver profile is the evidence sheet for the
  mapping contract and the artifact its `profileHash` cites, and in
  Phase 6 it is the exact input the gold mapping proposer consumes.
- Skips PyAirbyte's internal tables: any `_airbyte_*`-prefixed table
  (`_airbyte_streams` today; state tables appear under other sync
  modes): they are connector bookkeeping, not data streams.
- `_airbyte_*` columns are profiled and flagged `is_airbyte_metadata: true`
  but excluded from `duplicate_row_rate` (section 3).
- The runtime workflow diagram records a later silver pass running the
  same code over silver. The header boundary is about authority (the
  profiler describes and proposes, contracts decide), not about which
  schema may ever be profiled.

Interface: `make profile` wraps a config-driven entry point that reads a
`profiling:` block in `config/default.yaml`. No CLI arguments, the same
posture as ingestion's `land_sample` entry point.

Failure modes: a missing warehouse file or a missing bronze table fails
with a message naming `make ingest` as the remedy. No partial artifacts
are written on failure.
