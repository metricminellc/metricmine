# Serving: the shared query module, the MCP server, and the demo export

> Repo path: `docs/spec/serving.md`
> Phase 5 specification. Governing decisions: D-31 (serving layer), D-32
> (MCP SDK pin), D-33 (demo export), over the standing D-03, D-11, D-17,
> and D-24. The tool surface below was frozen in
> [`docs/spec/gold-unified-event-star.md`](gold-unified-event-star.md)
> (Serving surface) in July 2026; this spec implements it and does not
> redesign it. Mechanics marked "probed" were measured on the pinned
> toolchain (duckdb 1.4.3, mcp) on August 13, 2026, in the pre-L prep
> session. The mcp mechanics were first probed at 2.0.0 and re-measured
> unchanged at the pinned 1.29.0 when Amendment D moved the pin to the
> maintenance line (F-22). None are inferred from documentation.

## 1. Purpose and boundary

Gold serves consumers only through one shared module,
`src/metricmine/query.py` (D-17). The MCP server at
`src/metricmine/server/` is the primary consumer and a thin adapter: it
exposes exactly the five spec tools, delegates every one of them to the
shared module, and never opens DuckDB itself. The optional hosted demo
(Phase 7) imports the same module. The serving layer adds zero agents
(D-10) and zero write paths: everything below is a read.

## 2. The tool surface (frozen)

Five tools, exactly. Names are snake_case (the mcp SDK convention) and
map one-to-one onto module methods.

| Tool | Arguments | Returns | Truth source |
|---|---|---|---|
| `list_fact_categories` | none | categories with fact table name and row count | `information_schema` (physical tables `fact_<category>_values` in schema `gold`), cross-checkable against the registry |
| `get_schema` | `schema_key` | entity group, contract name and version, role, manifest (the declared field list) | `gold.context_registry` |
| `get_context` | `schema_key` | the full compiled context (fields, descriptions, derivations) plus its contract citation | `gold.context_registry` |
| `query` | `sql`, optional `row_cap` | columns, rows, `row_count`, `truncated`, `row_cap` | the statement-gated, row-capped read path (§3, §4) |
| `lookup_record` | `content_key` | every place the key resolves: registry row, fact row(s), dimension row(s), or a derived `line_identity` hit, each labeled with where it was found | all star tables plus the registry (the provenance tool) |

Not-found is a clean empty result with `found: false`, never an error:
an unknown key is a legitimate answer about content-addressed storage.

## 3. Read-only, three layers deep

The posture is defense in depth. Each layer was probed on August 13,
2026; the middle layer exists because the probe showed the first is not
enough.

**Layer 1 — the connection.** `duckdb.connect(path, read_only=True)`.
Probed: DELETE and CREATE refuse (`Cannot execute statement of type
... on data`), and in-memory ATTACH refuses. But **ATTACH of another
file database is ALLOWED on a read-only connection** (probed both bare
and `(READ_ONLY)`): read-only protects the served file, not the
filesystem. Layers 2 and 3 close that.

**Layer 2 — session hardening.** Immediately after connect, before any
client statement:

```sql
SET enable_external_access = false;
SET timezone = 'UTC';
SET lock_configuration = true;
```

Probed effects: `read_csv_auto(...)` refuses with a Permission Error;
`ATTACH` of a file refuses at the filesystem layer; `INSTALL` refuses;
config-changing pragmas refuse; and `SET enable_external_access=true`
refuses once the configuration is locked. Normal SELECTs over gold are
unaffected. (Session settings are not DML; the profiler set a timezone
the same way under D-11.)

The lock goes last. Probed at 1.4.3 while implementing this module:
`lock_configuration = true` seals `timezone` along with everything else,
so the D-11 determinism setting must be applied before the seal. Applied
after it, DuckDB raises `Cannot change configuration option "timezone" -
the configuration has been locked` and the session keeps the machine's
local zone.

**Layer 3 — the statement gate.** The `query` tool accepts exactly one
statement that is literally a SELECT. Three checks, in order, all
probe-validated at duckdb 1.4.3:

1. `duckdb.extract_statements(sql)` parses to **exactly one** statement
   (refuses multi-statement input and empty input; a parse error refuses
   with the parser's message).
2. The statement's type is `StatementType.SELECT`. This refuses ATTACH,
   COPY, INSERT, UPDATE, DELETE, CREATE, DROP, EXPLAIN, SET/RESET, CALL,
   INSTALL/LOAD (type LOAD), and EXPORT by type.
3. The first meaningful keyword (after comments) is `select`, `with`, or
   `from`. This makes "SELECT only" literal: probed at 1.4.3, DuckDB
   rewrites `PRAGMA database_list`, `SHOW`, `DESCRIBE`, and `SUMMARIZE`
   into SELECT-typed reads, so a type check alone would pass them. The
   keyword check refuses them; schema questions belong to `get_schema`.

The 29-case refusal matrix (every case above plus CTE, FROM-first,
comment-led, VALUES, parenthesized, and garbage input) is pinned in the
module's unit tests; the probe run passed all 29. Refusals name their
reason; the message states which check failed.

Read-class rewrites reachable *inside* a legitimate SELECT (for example
`SELECT * FROM pragma_database_list()`) stay reachable; under layers 1
and 2 they can reveal engine metadata only. The threat model here is
writes and filesystem reach, and both are closed twice over.

## 4. Row caps and truncation

Every `query` result is row-capped. The default cap is 100 rows; a
caller may request up to the hard cap of 500; the cap floor is 1.
The runner fetches `cap + 1` rows and sets `truncated: true` when the
extra row exists, so a capped result always announces itself (the
Sitting K lesson: a truncated result that does not announce itself is a
measurement error waiting to happen). Registry and schema lookups return
at most a handful of rows by construction; `lookup_record` caps its
per-table hits at the same default.

## 5. Database resolution

The module resolves its database in this order:

1. `MM_SERVE_DB` (environment variable), if set — absolute path
   recommended; the MCP server is launched by a desktop client whose
   working directory is not the repo root.
2. `demo/demo.duckdb` — the committed demo artifact (D-03 as amended,
   Amendment E), the default surface. The keyless posture holds: no
   credentials, no network, one file. The stem is deliberately not
   `gold`: a directly opened DuckDB file takes its catalog name from its
   stem, and a catalog named for the schema inside it makes every
   two-part `gold.<x>` reference ambiguous at 1.4.3
   ([F-25](../verification/gate_proof_findings.md#f-25)).

Until the demo artifact exists (it is built at Session M), local serving
runs with `MM_SERVE_DB` pointed at the working warehouse. A missing
database fails closed at startup with a message naming both paths and
the `make export-demo` remedy.

## 6. The shared module (`src/metricmine/query.py`)

One class, `GoldWarehouse`, holding the hardened read-only connection
(§3 layers 1-2) and five methods mirroring §2. It lives beside, and in
the same posture as, the D-11 protocol in `src/metricmine/warehouse/`
(whose docstring has promised this consumer since the profiler PR):
every method is a SELECT; no DDL, no DML, anywhere. Results are plain
dicts/TypedDicts (JSON-shaped), so the MCP server and the hosted demo
serialize them without translation.

Method sketch (signatures are the contract; bodies are Session L work):

```python
class GoldWarehouse:
    def __init__(self, path: str | Path | None = None) -> None: ...
        # resolves per §5, connects read_only, applies §3 layer 2

    def list_fact_categories(self) -> CategoryList: ...
    def get_schema(self, schema_key: str) -> SchemaResult: ...
    def get_context(self, schema_key: str) -> ContextResult: ...
    def query(self, sql: str, row_cap: int = 100) -> QueryResult: ...
    def lookup_record(self, content_key: str) -> LookupResult: ...
```

`lookup_record` search order, probed against the live star: the registry
by `schema_key`; the fact table by `fact_hash_id` (and each of its
`*_hash_id` foreign columns); each values dimension by its hash-id
column; then derived identities inside dimension payloads
(`json_extract_string(dim_values, '$.line_identity')`). Each hit is
labeled with table and column; the probe round-tripped a real
`line_identity` to its one dimension row and one fact row.

## 7. The MCP server (`src/metricmine/server/`)

A thin adapter and nothing else: `app.py` builds the `FastMCP` server
(`mcp.server.fastmcp`, the official SDK on the 1.x maintenance line per
D-32 as amended) named `metricmine-gold`, registers the
five tools as plain functions that call one shared `GoldWarehouse`
instance, and `__main__.py` runs `server.run(transport="stdio")`, so
`python -m metricmine.server` serves a desktop client.

Probed mcp facts the implementation relies on, measured at 2.0.0 and
re-measured unchanged at the pinned 1.29.0 (F-22):

- Tool input schemas derive from type hints; defaulted parameters render
  as optional with their defaults.
- **Structured output requires a concrete typed return shape** (a
  `TypedDict` here). A bare `dict` annotation produced no output schema
  and no structured content in the probe; every tool therefore declares
  a TypedDict return.
- Discovery and round trip verified end to end over stdio: an
  in-process `ClientSession` listed both probe tools with correct
  schemas and round-tripped both calls (protocol `2025-11-25`), and the
  same server wired into Claude Desktop on the Mac passed live tool
  discovery and calls (probe P1 platform pass).
- **A union return is wrapped; a single shape is not.** Structured output
  is validated against the declared schema and undeclared keys are
  dropped, so a refusal cannot ride inside `QueryResult` — `query`
  declares `QueryResult | QueryRefusal`, and the SDK renders that as a
  `result` property whose schema is an `anyOf` over both. Its structured
  content is therefore `{"result": {…}}`, while the other four tools
  return their shape at the top level. Measured at 1.29.0 against this
  server; the asymmetry is real and the round-trip tests assert both
  forms.
- **A gated SELECT that fails to execute is deliberately not caught.**
  `query` catches `QueryRefused` and nothing else. A statement that
  passes the gate and then fails to run — `SELECT * FROM gold.typo` —
  surfaces as `isError` with DuckDB's own diagnostic, `structuredContent`
  null, and the session continues serving (measured). A refusal is a
  policy decision and stays a normal answer; a broken statement is a
  mistake in the SQL and stays an error, so the two remain
  distinguishable by `isError`. Catching it here would mean catching
  broadly enough to disguise real defects as user error, since the
  adapter imports no duckdb by design.

stdio discipline: the server process never prints to stdout — stdout
carries JSON-RPC. Diagnostics go to stderr or nowhere.

Claude Desktop wiring (documented shape, verified live at P1):

```json
{
  "mcpServers": {
    "metricmine-gold": {
      "command": "/ABSOLUTE/PATH/TO/metricmine/.venv/bin/python",
      "args": ["-m", "metricmine.server"],
      "env": { "MM_SERVE_DB": "/ABSOLUTE/PATH/TO/metricmine/warehouse/metricmine.duckdb" }
    }
  }
}
```

(The `env` entry disappears once `demo/demo.duckdb` exists and becomes
the default.)

## 8. The demo export (`make export-demo`)

D-03 named the target and the artifact; D-33 fixes the mechanism and the
claim. `make export-demo` runs the keyless replay tail: with the working
warehouse built (ingest, build, gates green), a Python exporter
(`src/metricmine/export_demo.py`) creates `demo/demo.duckdb` fresh:

1. connect to the new file; `ATTACH` the working warehouse `READ_ONLY`;
2. `CREATE SCHEMA gold`; copy each gold table with
   `CREATE TABLE gold.<t> AS SELECT * FROM wh.gold.<t>`, in sorted-name
   order;
3. `DETACH`, then recreate `vw_invoice_lines_typed` from the working
   catalog's stored SQL (`duckdb_views()`), re-anchoring the database
   qualifier (`metricmine.gold.` → `gold.`) so the view resolves inside
   its own file — probed: the stored SQL is db-qualified and fails
   verbatim in another catalog. The view lands after the detach, with
   only the export's own catalog attached: its stem is deliberately not
   `gold` (F-25), so the plain `gold.` target and body references bind
   cleanly. Until the detach, schema `gold` exists in two catalogs,
   which is why the step-2 copy statements carry the destination
   catalog qualifier explicitly;
4. `CHECKPOINT`; verify; report size.

**The claim is content equality, proven by query, never byte equality**:
a DuckDB file embeds storage details that make byte determinism a claim
this project does not need and will not make. Verification, probed
clean on August 13: per table, equal counts plus symmetric
`EXCEPT` both ways returning zero, run from one comparator connection
with both files attached read-only; for the view, an ordered
`md5(string_agg(...))` content digest compared across **direct
per-file connections** (probed: a view's stored refs resolve against its
own catalog; comparing views through cross-attachment is where `gold.`
could bind ambiguously, so the exporter never does).

Probed measurements at the current sample: export 11,022,336 bytes
(11.02 MB) against a 14.95 MB working warehouse; schemas in the export:
`gold` only (bronze and silver absent — the committed artifact carries
no raw data, D-03/D-15 posture); read-only open works; the typed view
answers the top-countries question with the same rows as the working
warehouse.

Refresh policy (D-33): the artifact is rebuilt only when gold content
changes — at regeneration merges and at tags — never on a schedule. Each
refresh travels in a PR whose body carries the size and the verification
line.

## 9. Testing

- **Pure-unit (CI lane):** the 29-case statement-gate matrix; database
  resolution order; refusal messages; category-name parsing. No
  warehouse required.
- **Local lane (`@pytest.mark.local`, the established marker):** every
  lookup against the built warehouse (registry keys, schema/context
  round trips, `line_identity` provenance round trip); row-cap and
  truncation behavior over the 44,721-row fact; the in-process stdio
  round trip against the real server with `MM_SERVE_DB` set; export
  content-equality on a freshly built export.
- The server's tool registration (five tools, expected names) is
  asserted in the CI lane by importing the app and listing tools
  in-process — no subprocess, no warehouse.

## 10. Explicitly out of scope

No auth and no remote transports (local stdio only; the server binds to
nothing). No mutation tools, ever. No second server and no per-consumer
query logic: the hosted demo imports the module. No caching, pooling, or
performance claims (legibility first; performance is a stated
non-goal). No UI beyond the optional read-only demo. Non-goals in the
README remain standing.

## References

In this repository:
[`docs/decisions/decision-register.md`](../decisions/decision-register.md)
— D-03, D-10, D-11, D-17, D-24, and (minted with this phase) D-31,
D-32, D-33.
[`docs/spec/gold-unified-event-star.md`](gold-unified-event-star.md) —
the frozen serving surface and the star this layer serves.
[`docs/verification/gate_proof_findings.md`](../verification/gate_proof_findings.md)
— the evidence discipline this spec's probed claims follow.

Project records (design history outside the repository; nothing here
depends on them): the Phase 5 planning checkpoint and pre-L probe
transcript, August 2026.
