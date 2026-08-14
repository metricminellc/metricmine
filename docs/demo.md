# The ten-minute demo

> Repo path: `docs/demo.md`
> The full walkthrough behind the README's *See it run* section. Two
> paths: serve the committed gold artifact immediately (no build, no
> keys), then optionally replay the entire pipeline from raw data. A
> recording of this walkthrough is attached to the
> [latest release](https://github.com/metricminellc/metricmine/releases/latest).

## What you need

- macOS or Linux, with `git` and [uv](https://docs.astral.sh/uv/)
  installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`). uv
  provisions the pinned Python 3.12 and every dependency; nothing else is
  installed globally.
- [Claude Desktop](https://claude.ai/download) for the serving beat
  (optional — path A works from the terminal without it).
- No API keys, no accounts, no cloud resources. Everything below is
  keyless by design (D-24).

## Path A — serve the committed gold star (2 minutes)

The repository commits `demo/demo.duckdb`: a ~11 MB export carrying the
gold schema only, verified content-equal by query to the built warehouse
(D-33). The MCP server reads it by default, so serving works from a fresh
clone:

```bash
git clone https://github.com/metricminellc/metricmine.git
cd metricmine
uv sync
uv run python -c "from metricmine.query import GoldWarehouse; print(GoldWarehouse().list_fact_categories())"
```

Expected output: one category, `invoice_lines`, table
`fact_invoice_lines_values`, 44,721 rows.

### Wire it into Claude Desktop

Merge this entry into `claude_desktop_config.json` — on macOS at
`~/Library/Application Support/Claude/claude_desktop_config.json` — keeping
any existing keys, and replacing the command path with your absolute clone
path:

```json
{
  "mcpServers": {
    "metricmine-gold": {
      "command": "/absolute/path/to/metricmine/.venv/bin/python",
      "args": ["-m", "metricmine.server"]
    }
  }
}
```

Quit Claude Desktop fully and reopen it. A new chat should list
`metricmine-gold` with five tools:

| Tool | What it answers |
|---|---|
| `list_fact_categories` | which fact categories exist, with row counts |
| `get_schema` | the declared field manifest behind a schema key |
| `get_context` | the full compiled context: descriptions, derivations, and the contract citation |
| `query` | one row-capped SELECT; anything else refuses, naming the failed check |
| `lookup_record` | every place a content key resolves: registry, fact, dimension, or derived line identity |

### Ask it something

> Using the metricmine-gold tools: what are the top three countries by
> invoice line count, and what does the country field mean in this model?

The answer carries the counts from the star and the meaning from the
context registry, cited to the mapping contract version that created it —
data and meaning in one exchange. Two follow-ups worth trying:

- *"By gross value instead of line count, does the podium change?"* — the
  model does analysis, not retrieval, and the answer is different in an
  interesting way.
- *"Take one line_identity from a dimension payload and run
  lookup_record on it."* — the provenance round trip: every payload is
  reachable by content key.

## Path B — replay the whole pipeline (about 8 minutes)

The Online Retail II sample is committed (D-15), so the full path is
keyless too. From the repo root:

```bash
export DBT_PROFILES_DIR="$PWD/transform"
uv run dbt deps --project-dir transform
make ingest
uv run dbt build --project-dir transform --target local
make export-demo
uv run pytest -q
```

What to expect, step by step:

1. `make ingest` provisions a small connector environment on first run,
   then lands **45,228 bronze rows** exactly as they appear in the raw
   files.
2. `dbt build` compiles the contracted models and runs every generated
   and declared test: it ends **`PASS=108 WARN=0 ERROR=0 SKIP=0`**. Shape
   is enforced at compile time; content rules run as tests with
   contract-declared severity.
3. `make export-demo` rebuilds `demo/demo.duckdb` from your freshly built
   warehouse and verifies it: per-table equal counts plus symmetric
   EXCEPT, and a content digest over the typed view compared across
   per-file connections. The claim is content equality by query, never
   byte equality (D-33), so your artifact proves equal even though its
   bytes may differ.
4. `pytest` runs the full suite, including the local lane that exercises
   the query gate's 29-case refusal matrix, the serving round trip, and
   the export verification.

## Troubleshooting

- **`uv: command not found`** — install uv (link above) and reopen the
  terminal. Everything else flows from it.
- **`dbt` cannot find a profile** — `DBT_PROFILES_DIR` must point at the
  repo's `transform/` directory (the export line above); run dbt from the
  repo root, not from inside `transform/`.
- **Claude Desktop does not show the server** — quit it fully (Cmd+Q on
  macOS) rather than closing the window; confirm the config file is valid
  JSON and the `command` path exists (`ls .venv/bin/python` from the repo
  root). Running `uv run python -m metricmine.server` by hand should
  produce no output at all — silence is correct on stdio; Ctrl-C to exit.
- **First tool call asks for permission, or the chat runs a visible
  tool-search step** — both are normal Desktop behavior on a newly added
  server; approve and continue.
- **macOS asks whether Claude may access your Documents folder** — approve
  it if the clone lives there; the server reads the committed database
  from the repo.
- **A query returns `truncated: true`** — by design. Results are
  row-capped (default 100, hard cap 500) and a truncated result announces
  itself; aggregate or narrow the query instead of raising the cap.
- **A write or PRAGMA attempt refuses** — also by design. Serving is
  read-only three layers deep; the refusal names the failed check
  ([serving spec](spec/serving.md)).

## Where to next

The [README](../README.md) is the front door. The
[gold layer spec](spec/gold-unified-event-star.md) explains the star the
demo queries, including the *Reading the star* rules for its
content-addressed keys. The
[signature test](verification/signature-test.md) is the evidence behind
the project's central claim.
