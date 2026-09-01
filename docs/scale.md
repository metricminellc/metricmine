# Scale: what grows, what it costs, and the built paths

> Repo path: `docs/scale.md`
> Governing decisions: [D-38](decisions/decision-register.md#d-38)
> (incremental materialization), [D-39](decisions/decision-register.md#d-39)
> (batch-scoped gates and the audit), [D-40](decisions/decision-register.md#d-40)
> (this document and the measurement rule).

## The rule every number here follows

A performance number is published only with its environment stated. No
number is a promise. Throughput claims and SLAs are non-goals and stay
non-goals. If your machine differs, your numbers will differ; the shapes
below are the durable part.

## What scales by design

The build is linear in rows. The unified event star is string
construction plus SHA-256 plus writing wide hash columns, all
proportional to input size, with no joins in the build path. It
degrades gracefully under memory pressure: DuckDB spills to disk and
finishes.

The query path is a solved problem at the typed mart. The star's fact
and dimension tables are a content-addressed provenance layer; asking
analytical questions of them directly re-joins hash keys and re-parses
JSON per question. The materialized typed mart
(`mart_<category>_typed`, D-36) answers the same questions 100 to
2,000 times faster and is the default typed surface. The serving layer
steers agents to it.

Continuous loading has a built path. With
`engine.materialization: incremental` (D-38), each build processes the
new batch: silver rows above the stored `captured_at` watermark, hashed
once, inserted through content-key anti-joins. A 1 percent batch costs
seconds where a full rebuild costs minutes. The gates scope with it
(D-39): pass `mm_batch_floor` and the expensive checks cover the batch;
run `make audit-gold` for the full-table forms on demand.

## The measured curve

Environment: a 2-CPU, 7 GB sandbox, August 23, 2026. dbt-core 1.11.12,
dbt-duckdb 1.10.1, duckdb 1.4.3, one dbt thread, synthetic bronze
generated to match the committed sample's shapes and skews. Full
`dbt build`, every node green at every size.

| bronze rows | dbt build | peak RSS | file on disk |
|---|---|---|---|
| 45,228 | 3.3 s | 0.30 GB | 17 MB |
| 1,058,539 | 15.7 s | 0.93 GB | 320 MB |
| 5,290,130 | 65.9 s | 3.77 GB | 1.6 GB |
| 10,573,228 | 118.0 s | 4.76 GB | 3.2 GB |
| 21,138,876 | 250.3 s | 4.94 GB (spilled) | 6.8 GB |
| 21,138,876 at a 2 GB memory cap | 289.8 s | 2.62 GB | 6.8 GB |

Typed-surface latency at 21 million rows, same environment, best of two
runs: revenue by country through the projection view 19.6 s; the same
question through the materialized mart 105 ms; first 100 rows 6.8 s
through the view, 11 ms through the mart. The mart's one-time build:
61 s at 10.57 million rows, 151 s at 21.14 million.

Incremental loading, same environment: a 1 percent batch of new
invoices costs about 5.5 s at a 10.57-million-row base and about 15 s
at 21.14 million, against full rebuilds of 118 s and 250 s plus the
mart. Batch-scoped gates cost 0.04 s and 0.8 s at those sizes, against
17 to 18 s per full-table uniqueness or C2 check at 21 million rows.

## Disk and memory guidance

Plan roughly 3.5 times the bronze bytes on disk, plus spill space.
Twenty-one million rows needs about 25 GB free including the mart. A
2 GB DuckDB memory cap completes the full build; it just spills and
takes about 15 percent longer. DuckDB does not shrink a database file
after a failed run: rebuild into a fresh file rather than reusing one
that died mid-build.

Storage shape, measured at 21 million rows: hash columns are about 95
percent of the fact table's bytes. The star holds silver's information
at roughly ten times the bytes; the lean typed mart holds it at
roughly two. That ratio is the price of content addressing with
hexadecimal keys in JSON text, chosen deliberately for provenance. The
mart exists so it is not the price of answering a question.

## The profile gotcha

Do not set `temp_directory` in dbt-duckdb profile settings. The
adapter re-applies settings per cursor, and DuckDB refuses to switch a
temp directory after the first spill has used it. Leave the default
spill location beside the database file. When pushing beyond memory,
set `memory_limit` in the profile's settings block and let spill do
its job.

## The incremental recipe (D-38)

1. Set `engine.materialization: incremental` in `config/default.yaml`
   and run `make regen`. The diff is one config line per model; land it
   as a regeneration pull request under the ownership manifest (D-09).
2. Build. The first incremental build over an empty warehouse is a full
   build; every later build processes silver rows at or above each
   table's stored `captured_at` high-water mark and inserts through
   content-key anti-joins, so boundary re-scans are idempotent.
3. Gate each batch with the floor of its capture window:
   `uv run dbt test --project-dir transform --target local --select "path:tests/datacontract_cli/gold_unified_event_star" --vars '{mm_batch_floor: "<batch floor timestamp>"}'`.
4. Run `make audit-gold` on whatever cadence suits: it runs every
   contract-generated gold test in its unscoped full-table form.
5. A full rebuild in `table` mode remains the reset and the ultimate
   audit: determinism means it reproduces the same star from the same
   silver, byte-reproducibly at the emitted-model layer.

Silver stays the human-owned plane (D-04): the committed silver model
materializes as a table, and `make demo` stays a keyless full replay.
A deployment loading continuously can make its silver model
incremental with the same watermark pattern; the shape is:

    {{ config(materialized='incremental') }}
    ...
    {% if is_incremental() %}
    where captured_at >= (
        select coalesce(max(captured_at), timestamp '1900-01-01')
        from {{ this }}
    )
    {% endif %}

with the model's dedup grain deciding what an insert-worthy new row
is. That edit belongs to the silver owner and lands like any silver
model change: contract first if the shape moves, then the model.

## What remains, honestly

One source type at one committed scale. The curve above is synthetic
data on a small machine; the Mac re-measure lands below with its own
environment line. Cross-version record linkage is out of scope for the
star (`line_identity` is a row fingerprint). Binary keys, entity-group
splitting, and a cheaper digest were measured and parked with their
numbers; none is built, and the register records why. There is no
freshness monitoring, volume anomaly detection, or alerting: the
project claims traceability and conservation, not observability.

## The Mac re-measure

Environment: Apple M3 Pro, 36 GB, macOS 26.6.2, mains power. Measured
with the Arc 5 pressure bundle's generator and probes at the Arc 5b
exit; same committed toolchain, one dbt thread.

| bronze rows | dbt build | mart: revenue by country | view: revenue by country |
|---|---|---|---|
| 1,058,539 | 5.9 s | 2 ms | 118 ms |
| 10,573,228 | 25.2 s | 9 ms | 1.0 s |

The shapes match the sandbox curve: the build linear in rows, the mart
answering in milliseconds where the view takes seconds. Numbers differ
with hardware; the environment line above is part of the measurement.
