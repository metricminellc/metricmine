# Ingestion Component Specification

**Status:** adopted (Session C, spec PR).
**Governing decisions:** [D-15](../decisions/decision-register.md#d-15) (committed
sample), [D-04](../decisions/decision-register.md#d-04) (transform plane),
[D-03](../decisions/decision-register.md#d-03) (warehouse files).

## 1. Purpose and scope

Ingestion lands source data into the bronze schema of the working DuckDB
warehouse. PyAirbyte owns ingestion in this system. Scope, in full:

- The Airbyte `source-file` connector lands every committed sample CSV
  (D-15 as amended by Amendment T): one connector type, many files. The
  `ingestion.sources` list in `config/default.yaml` names each dataset,
  its committed CSV, and any reader options its landing needs; the
  landing loops the connector over the list, each dataset one bronze
  stream (D-41). CSV now. The Parquet twin of a sample is a recorded
  later increment, not built here.
- `source-faker` remains the keyless synthetic path for tests that need no
  real data.
- Nothing else. The README non-goals stand: streaming, Redshift, orchestration
  platforms, and any ingestion connector type beyond this one.

Boundary: the [current-state baseline](current-state/data-capture-baseline.md)'s
acquisition stages are historical record; PyAirbyte owns ingestion in this system.

## 2. source-file connector configuration (verified 2026-07-26)

Connector: `source-file`, docs at version 0.6.0 at verification. Keys
verified against the Airbyte connector documentation and spec, never from
memory:

| Key | Value here | Notes |
| --- | --- | --- |
| `dataset_name` | the entry's `dataset_name` (`online_retail_ii` for the retail sample) | Becomes the bronze stream and table name; unique across the list |
| `format` | `csv` | Enum: csv, json, jsonl, excel, excel_binary, fwf, feather, parquet, yaml |
| `url` | the entry's `sample_csv` (`data/samples/<source>/<extract>.csv`) | The committed extract |
| `provider` | `{"storage": "local"}` | Storage enum: HTTPS, GCS, S3, AzBlob, SSH, SCP, SFTP, local. `local` is restricted on Airbyte Cloud; PyAirbyte runs it locally, which is this system |
| `reader_options` | the entry's `reader_options` (`{"dtype": {"Invoice": "str"}}` for the retail sample) | Optional JSON string of pandas read_csv options, per entry. The Invoice dtype pin keeps C-prefixed cancellation ids as text at the reader, so inference and records agree. Code columns pin `str` so leading zeros survive, and a source whose codes collide with pandas' default missing markers (`NA` is a continent and a country in OurAirports) sets `"keep_default_na": false, "na_values": [""]` so the empty string is the only missing marker (F-50). Any further addition is recorded here first |

## 3. Bronze conventions

- Schema `bronze` inside `warehouse/metricmine.duckdb` (gitignored, D-03).
- One table per stream, named by `dataset_name`: `bronze.online_retail_ii`
  for the retail sample; every entry in `ingestion.sources` lands beside it.
- `_airbyte_*` metadata columns are kept exactly as landed.
- No renames, no casts, no cleanup in bronze. Bronze is evidence; cleanup
  is silver's contracted job.
- Full-refresh replace semantics: rerunning the landing leaves row counts
  unchanged.

## 4. PyAirbyte runtime behavior

- `get_source("source-file", config=..., install_if_missing=True)`, once
  per entry in `ingestion.sources`; the landing loops the connector and
  reads each source into the same cache with replace semantics. The
  connector installs into its own venv on first run and needs network.
- Cache: `DuckDBCache(db_path="warehouse/metricmine.duckdb",
  schema_name="bronze")`. Parameters verified against the PyAirbyte API
  reference 2026-07-26; `schema_name` defaults to `main`, so it is set
  explicitly.
- The end-to-end landing runs in two places since the bronze-in-CI change
  (D-27): locally as the make target, and in CI, where the contract-gates
  job runs `make ingest` (offline mode, connector venv pre-provisioned by
  the Makefile) before the gates. pytest in CI still covers the unit
  surface only; the landing smoke test stays local-marked.
- PyAirbyte version: 0.49.0 at spec verification (2026-07-10); pinned at
  the implementation PR as airbyte >=0.53,<0.54 (resolved 0.53.2 in
  uv.lock; CLAUDE.md rule 1). The connector is pinned separately:
  airbyte-source-file 0.3.15 with numpy<2 on uv-provisioned CPython 3.10
  (Makefile).

## 5. Acceptance criteria (Phase 2 exit)

1. Every bronze table's row count equals its committed sample's count
   (`bronze.online_retail_ii` first; each further source records its
   count in its sample README).
2. Rerunning the landing leaves the count unchanged (replace semantics).
3. Bronze is inspectable via `duckdb -readonly warehouse/metricmine.duckdb`.
4. `_airbyte_*` columns are present.

## 6. Provenance

The committed sample is governed by D-15: Online Retail II (Daqing Chen,
UCI Machine Learning Repository, CC BY 4.0), a deterministic one-month
complete-invoice extract under 5 MB, fetch script committed, raw download
gitignored, Kaggle mirror acceptable for retrieval with UCI cited.

Every further sample follows D-15 as amended (Amendment T): a public
dataset cited in `data/samples/<source>/README.md` with its license and
its publisher artifact, fetched by `scripts/fetch_<source>.py` pinned to
that artifact (a repository commit, a published month) with the raw
download under gitignored `data/raw/`. The script records the raw
download's sha256 and refuses to extract from bytes that differ from
it, so a rerun is byte-identical while the publisher artifact stands
and a publisher revision is a loud finding. Budgets: 20 MB for the one
event source, 10 MB for every other source, 40 MB for an arc, enforced
in the script. The aviation family (D-41): the nycflights13 package's
flights, hourly weather, carriers, and aircraft tables at a pinned
commit (CC0; New York City's three airports, January through June 2013
for the dated tables), and OurAirports airports and runways at a pinned
commit (public domain). `docs/sources.md` is the register of every
extract with its pin, license, digest, and window.
