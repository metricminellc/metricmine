# Current-State Baseline: The 2023 Data Capture Pipeline (Abridged)

> Repo path: `docs/spec/current-state/data-capture-baseline.md`
> Historical record and provenance artifact, abridged from the clean-room
> Current-State Technical Specification v1.0 (a project record). This is a
> **baseline, not a build target**: PyAirbyte owns ingestion in this system,
> so the acquisition machinery below is summarized for the record only. What
> the rebuild preserves at full fidelity (the event-packet data model, the
> hashing contract, the row-conservation invariants, and the tuning
> parameters) is reproduced here in full.
>
> Provenance: this baseline is an independent, technology-agnostic
> transcription by purpose and flow. No original source code, function names,
> or internal naming conventions appear here or anywhere in this repository.

## 1. What the 2023 system was

A scheduled batch application. Each run loaded a queue of capture jobs from a
configuration store and executed them sequentially: authenticate to a source
reporting API, compute the effective capture window (full history on first
run, else yesterday), acquire report rows through an adaptively windowed,
paginated, resumable request loop, reshape every row into a self-describing
event packet, and persist uniform fixed-size slices as numbered files to an
object-store landing zone. A separate downstream load decomposed the landing
table into the hash-keyed star schema. It moved roughly 26 million records in
its largest verified run within bounded memory.

Three behaviors carried the value and are preserved by the rebuild:

1. **The event-packet data model** (Section 3): carried forward into the
   gold design ([`docs/spec/gold-unified-event-star.md`](../gold-unified-event-star.md), D-17).
2. **Arithmetically self-verifying logging** (Section 4): carried forward as
   conservation tests C1–C4 plus ledger-style engine logs.
3. **Bounded-memory batching** (Section 5): carried forward as principles;
   the mechanics belong to PyAirbyte, dbt, and DuckDB now.

## 2. Pipeline stages (historical summary)

| Stage | Purpose | Rebuild disposition |
|---|---|---|
| 0 Orchestration | Job queue, credentials, historical-vs-scheduled phase, compute lifecycle | Historical; not rebuilt |
| 1 Job run | Accounts × measure-set passes; accumulate; fail fast | Fail-fast posture preserved |
| 2 Adaptive acquisition | Windowed, paginated, resumable pulls; quota and timeout handling on independent axes | Historical; PyAirbyte owns ingestion |
| 3 Flattening | Pages → positional rows-and-columns table | Historical |
| 4 Packet assembly | Serialize, manifest, hash, widen to the 24-field layout | **Preserved: the data model (Section 3)** |
| 5 Distribution | Chunked hand-off to the compute environment | Historical |
| 6 Uniform slicing | Fixed-size slices with leftover carry across passes | Historical (principle: uniform outputs) |
| 7 Persistence | Per-format partitioned writes with running-total reconciliation | Historical (principle: reconciled totals) |
| 8 Hygiene | Explicit release, forced GC, environment resets | Historical |

Notable acquisition behaviors, recorded for the pattern: quota exhaustion was
treated as purely time-based (pause just past the replenishment cycle, resume
in place at a saved window + offset); timeouts were size-based (shrink the
temporal window early in a run when discarding is cheap, shrink only the page
size mid-run when a resume position exists); both axes had floors and retry
budgets so adaptation always terminated in success or a clean, logged abort.
Zero-activity rows were deliberately retained: the absence of activity is
itself data.

## 3. The event-packet data model (full fidelity)

### 3.1 Concept

Every captured row was wrapped in a self-describing event packet organized
into six entity groups (job, source, account, capture timeframe, dimension
set, measure set), each carrying four elements:

| Element | Form | Description |
|---|---|---|
| Value payload | JSON object (text) | The group's field names mapped to their values for this record. |
| Schema manifest | JSON array (text) | The group's field names, in order: the schema the payload conforms to. |
| Record key | 64-char SHA-256 hex | Hash of the canonicalized value payload: content-derived identity of the record within the group. |
| Schema key | 64-char SHA-256 hex | Hash of the canonicalized schema manifest: content-derived identity of the field set itself. |

Four groups (job, source, account, timeframe) were constant per pass:
serialized and hashed once, replicated onto every record. Two groups
(dimension set, measure set) varied per row: payloads serialized and hashed
row by row, manifests and schema keys computed once per pass.

Because schema travels with data, downstream consumers could detect a change
in the requested field set from a schema-key change alone, reconstruct the
exact layout of any historical record from its own row, and deduplicate or
idempotently reload on content-derived keys instead of sequence surrogates.
This packet model is the load-bearing idea the rebuild keeps.

### 3.2 Canonicalization and hashing (the 2023 contract)

```
FUNCTION canonical_key(value)
  IF value is JSON-object text            # detected by a leading brace
    normalized <- lowercase( compact_serialize( parse(value) ) )
  ELSE                                    # scalars and JSON-array manifests
    normalized <- lowercase( text(value) ) with all spaces AND hyphens removed
  RETURN hex( sha256( normalized ) )      # 64-character digest
```

Properties relied on downstream: deterministic across runs and machines;
case-insensitive; whitespace-insensitive. Two properties are recorded as
constraints of the 2023 scheme: keys were **field-order sensitive** (payloads
serialized in configuration/insertion order, unsorted), and the scalar path
stripped **hyphens** as well as spaces.

> **Superseded for the rebuild (D-18).** The rebuild uses `canonical_key` v2:
> sorted-key compact serialization (order-insensitive), lowercase, SHA-256;
> scalars/manifests lowercase and whitespace-stripped with hyphens
> **preserved**. The baseline permitted a successor scheme only with an
> explicit migration plan; the plan is that the clean-room rebuild carries
> zero legacy data, so 2023 keys and v2 keys never need to match. See the
> [decision register](../../decisions/decision-register.md#d-18).

### 3.3 The 24-field packet layout

Every output record had the same 24 fields in the same order: the six record
keys grouped at the front (job, source, account, timeframe, dimension,
measure, so loaders could key, join, and deduplicate without parsing any
payload), followed by a schema-key / manifest / payload triplet per group in
the same group order. Constant-group fields were replicated onto every row.

### 3.4 Landing-to-warehouse decomposition (the star pattern)

The 24-field packet table was, structurally, the landing-zone event table. A
downstream load decomposed each entity group into a **values dimension**
(record key as PK, schema key as FK, payload as attribute) and a **columns
dimension** (schema key as PK, manifest as attribute), and built
category-parameterized fact tables keyed by a composite of the record keys,
with the measure payload as the fact attribute. Naming pattern in the
original warehouse: `*_hash_id` (record keys), `*_col_hash_id` (schema keys),
`*_columns` (manifests), `*_values` (payloads); `dim_` and `fact_` prefixes
for the row-varying groups. A load timestamp was stamped on the timeframe
group at load time, outside the hashed payload.

The original ERD also defined a `user` entity group following the same
four-element pattern; this pipeline never populated it. The rebuild's
deliberate deltas from this decomposition (fact-key composition, group set,
grain declaration) are specified in the
[gold layer spec](../gold-unified-event-star.md).

## 4. The row-conservation ledger (full fidelity)

Every counting log line stated its operands and result ("N rows + O offset =
T total"), each loop carried a cumulative offset, and every persistence run
ended with a reconciliation summary. Taken together the logs asserted a chain
of invariants, checkable from adjacent lines, localizing any loss or
duplication to a single stage boundary:

| Id | Invariant |
|---|---|
| I1 | Within a window: page rows + prior offset = running window total. |
| I2 | Per pass: sum of page rows across windows = flattened row count. |
| I3 | Per pass: flattened rows = packet-table rows. |
| I4 | Per job: pass rows + prior cumulative = new cumulative. |
| I5 | Slicing: slice size × new full slices + leftover = incoming rows; slice size × total slices + final leftover = cumulative rows. |
| I6 | Persistence: part rows + prior offset = running total; final summary = the cumulative ledger. |

End-to-end statement: *rows acquired = rows flattened = packets assembled =
rows sliced = rows persisted*. Severity discipline: INFO for expected
progress, WARNING for adaptive self-healing events, ERROR for fatal
conditions followed immediately by an abort. No silent branching: every skip,
resume, restart, reduction, and pause was logged with its reason.

> **Carried forward.** The rebuild enforces the same contract as dbt tests
> (C1: silver rows reconcile to fact rows or `sum(_row_count)`; C2: every
> group key resolves; C3: every schema key exists in the context registry;
> C4: every payload parses) and keeps ledger-style arithmetic in engine build
> logs. See the [gold layer spec](../gold-unified-event-star.md).

## 5. Batching parameters (full fidelity, for the record)

The 2023 tunables, preserved because they document the operating envelope the
data model was proven at:

| Parameter | Default | Rule / bound |
|---|---|---|
| PAGE_LIMIT_INITIAL | 250,000 rows | shrinks ÷1.1 (early) or ÷1.5 (mid-run) on timeout |
| PAGE_LIMIT_FLOOR | 1,000 rows | reaching the floor aborts the run |
| WINDOW_INITIAL | full requested span | one window per query |
| WINDOW_SHRINK | ÷4 first timeout, ÷2 after | floor of 1 day |
| EARLY_RUN_THRESHOLD | 10 pages | below: restart queue smaller; at/above: resume in place |
| TIMEOUT_RETRY_MAX | 10 attempts | budget exhaustion aborts |
| QUOTA_RETRY_MAX | 12 attempts | budget exhaustion aborts |
| QUOTA_PAUSE | 65 minutes | slightly exceeds the source's hourly replenishment |
| KEEP_EMPTY_ROWS | on | zero-activity rows are data |
| HANDOFF_CHUNK | 50,000 rows | driver-to-cluster transfer block |
| SLICE_ROWS_COLUMNAR | 900,000 rows | rows per columnar output file |
| TARGET_ROWS_DELIMITED | 55,000 rows | via byte-based repartitioning |
| SAMPLE_CAP | 200,000 rows | bytes-per-row estimation cap |
| TARGET_FILE_SIZE | ≈128 MB | loader-friendly target both row counts aim at |
| COMPRESSION_RATIO | ≈17:1 observed | explains the two row targets |

No stage ever required a whole job's data in driver memory at once; the
memory profile stayed roughly flat regardless of queue size.

## 6. Reimplementation guidance (from the baseline, with dispositions)

**Preserved by the rebuild:** the packet model with four-element groups and
content-derived keys (as the unified event star, D-17); the conservation
invariants (as tests C1–C4); fail-fast with no silent partial landings;
uniform, reconciled outputs; deterministic keys enabling idempotent reloads.

**Deliberately not rebuilt:** credential-materialization mechanics,
compute-environment choreography, adaptive request geometry, slicing and
partitioned persistence: their purposes (secure auth, clean memory, bounded
transfer, loader-friendly files) are honored by the new stack (PyAirbyte,
dbt, DuckDB) through its own means.

**Deliberately changed:** the canonicalization scheme (Section 3.2 note;
D-18), the fact-key composition and entity-group set, and grain handling,
each specified with rationale in the
[gold layer spec](../gold-unified-event-star.md).
