# The ten-minute demo

> Repo path: `docs/demo.md`
> The full walkthrough behind the README's *See it run* section. Two
> paths: serve the released gold artifact immediately (no build, no
> keys), then optionally replay the entire pipeline from raw data. A
> recording of this walkthrough is attached to the
> [latest release](https://github.com/metricminellc/metricmine/releases/latest).

## What you need

- macOS or Linux, with `git` and [uv](https://docs.astral.sh/uv/)
  installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`). uv
  provisions the pinned Python 3.12 and every dependency; nothing else is
  installed globally.
- [Claude Desktop](https://claude.ai/download) for the serving beat
  (optional; path A works from the terminal without it).
- No API keys, no accounts, no cloud resources. Everything below is
  keyless by design (D-24).

## Path A: serve the released gold star (2 minutes)

Every tagged release ships `demo/demo.duckdb` as a release asset: an
export carrying the gold schema only, verified content-equal by query
to the built warehouse (D-33). The repository commits its digest
manifest, `demo/demo.digest.json`, which names the release and pins the
asset's sha256, size, and content (D-03 as amended by Amendment S).
`make demo-fetch` downloads and verifies it, and the MCP server reads
it by default, so serving works from a fresh clone:

```bash
git clone https://github.com/metricminellc/metricmine.git
cd metricmine
uv sync
make demo-fetch
uv run python -c "from metricmine.query import GoldWarehouse; print(GoldWarehouse().list_fact_categories())"
```

Between tags, `main` may name no published release in its manifest; the
fetch then says so and Path B (`make demo`) builds the same content
keyless in a few minutes.

Expected output: three categories, each with its fact table, row count,
typed table, authored subject, and registry keys: `airport_weather`
(13,014 rows), `flights` (166,158 rows), and `invoice_lines` (44,721
rows). Two of them come from the same family of sources and share a
conformed airport code and the conformed calendar; the third is the
retail sample that shares nothing with them but the star's shape.

### Wire it into Claude Desktop

Merge this entry into `claude_desktop_config.json` (on macOS at
`~/Library/Application Support/Claude/claude_desktop_config.json`), keeping
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
| `list_fact_categories` | which fact categories exist, with row counts, the typed table to query, each category's subject in the words of the people who approved its contracts, and the registry keys `get_context` resolves |
| `get_schema` | the declared field manifest behind a schema key |
| `get_context` | the full compiled context behind a schema key, in two named parts: `data` (what the columns are) and `expert_context` (what people wrote about them), plus the contract citation |
| `query` | one row-capped SELECT; anything else refuses, naming the failed check |
| `lookup_record` | every place a content key resolves: registry, fact, dimension, or a derived identity |

### What the agent knows, and where it came from

Every registry entry keeps two things apart by name, so an agent (and
the person testing it) can tell what was measured from what was written:

- `data` is derived from the contracts' typed declarations: each
  column's type and role, the grain, the conformed keys and which other
  categories share them, the typed surface to query, and the note that
  string values there are lowercase.
- `expert_context` is authored knowledge: the subject, how to read the
  table, its limitations, its lineage and vintage, the joins it settled
  with their measured completeness, the cross-category joins the star
  declares with a worked example, the decisions taken, and a meaning
  for every field. It opens with a note saying it is authored, not
  measured, and that where a claim and the data disagree, the data is
  the fact and the claim is what to check.

That split is the point of the multi-source demo. The weather table
says that a null gust means no gust was reported, not zero; the flights
table says that a null arrival delay covers cancelled flights and 597
flights that departed with no arrival record; the airport reference is
a 2026 snapshot joined to 2013 flights, so Palm Beach flew as PBI and is
coded DJT in the reference, and 3,471 flights carry no destination
attributes on purpose. None of that is in the rows. All of it is in the
registry, and an agent that reads the context before it queries answers
correctly; one that does not, does not. Ask it to say which of the two
an answer rests on.

### Ask it something

Start with a cross-source question the star was built to answer:

> Using the metricmine-gold tools: do flights departing New York in an
> hour with precipitation at their origin run later than flights in a
> dry hour, and are they cancelled more often? Say what you joined on
> and what the context told you.

The answer joins the flights and airport_weather typed marts on the
conformed airport code and the conformed calendar hour (the join the
registry declares, with its measured completeness), and it should land
on 29.44 minutes against 12.42, with 8.95 percent cancelled against
2.41. The full set, with the SQL and the answers measured at the
committed samples, is `tests/fixtures/serving_questions.json`; the
local test lane proves each one through the serving path. Some worth
asking, and what to check for:

- *"Which carrier had the highest average departure delay, among
  carriers with at least 1,000 flights?"*: ExpressJet (ev) at 23.41
  minutes, cancellations excluded by construction; a good answer says
  why the average excludes them, and writes the carrier code in
  lowercase.
- *"How many flights went to PBI, and why do they carry no destination
  name?"*: 3,471, and the reason is in the expert context (the 2026
  reference codes it DJT), not in the rows.
- *"Which manufacturers' aircraft flew the most, and how old were
  they?"*: Boeing, Embraer, Airbus; a good answer notes that about 16
  percent of flights resolve no aircraft and says where that number
  came from.
- *"What are the top three countries by invoice line count, and what
  does the country field mean?"*: the retail category, unchanged from
  v1.0.0; the meaning cites the mapping contract version that created
  it.
- *"Take one flight_identity from a dimension payload and run
  lookup_record on it."*: the provenance round trip: every payload is
  reachable by content key, in every category.

## Path B: replay the whole pipeline (about 8 minutes)

Every source is a committed sample (D-15 as amended by Amendment T:
the retail extract and the six aviation extracts, each pinned to its
publisher's commit and digest; [docs/sources.md](sources.md) lists
them), so the full path is keyless too. From the repo root:

```bash
export DBT_PROFILES_DIR="$PWD/transform"
uv run dbt deps --project-dir transform
make ingest
uv run dbt build --project-dir transform --target local
make export-demo
uv run pytest -q
```

Steps 1 to 3 also run as one command, `make demo`: it lands bronze,
installs the dbt packages, builds the contracted models, and exports the
artifact, keyless by construction (a CI test proves the chain never
invokes a proposer). Run `uv run pytest -q` after it to verify.

What to expect, step by step:

1. `make ingest` provisions a small connector environment on first run,
   then lands **247,555 bronze rows across seven tables** exactly as
   they appear in the committed extracts.
2. `dbt build` compiles the 31 contracted models (nine human-owned
   silver tables, 22 engine-emitted gold objects) and runs every
   generated and declared test: it ends
   **`PASS=334 WARN=0 ERROR=0 SKIP=0`**. Shape is enforced at compile
   time; content rules run as tests with contract-declared severity,
   the declared joins among them.
3. `make export-demo` rebuilds `demo/demo.duckdb` from your freshly built
   warehouse, verifies it (per-table equal counts plus symmetric
   EXCEPT, and a content digest over every typed view compared across
   per-file connections), and writes `demo/demo.digest.json` beside it.
   The claim is content equality by query, never byte equality (D-33),
   so your artifact proves equal even though its bytes may differ; the
   manifest's content section is what CI holds every build to.
4. `pytest` runs the full suite, including the local lane that exercises
   the query gate's 29-case refusal matrix, the serving round trip, the
   export verification, the declared-join gate, the aviation
   conservation and business-logic checks, and the demo question set.

## Troubleshooting

Start with `make doctor`: it checks the platform, the interpreter, uv,
the locked toolchain, and the demo artifact (a hint, not a failure, when
it has not been fetched or built yet), and prints the two
environment exports the local dbt lanes need.

- **`uv: command not found`**: install uv (link above) and reopen the
  terminal. Everything else flows from it.
- **`dbt` cannot find a profile**: `DBT_PROFILES_DIR` must point at the
  repo's `transform/` directory (the export line above); run dbt from the
  repo root, not from inside `transform/`.
- **Claude Desktop does not show the server**: quit it fully (Cmd+Q on
  macOS) rather than closing the window; confirm the config file is valid
  JSON and the `command` path exists (`ls .venv/bin/python` from the repo
  root). Running `uv run python -m metricmine.server` by hand should
  produce no output at all; silence is correct on stdio; Ctrl-C to exit.
- **First tool call asks for permission, or the chat runs a visible
  tool-search step**: both are normal Desktop behavior on a newly added
  server; approve and continue.
- **macOS asks whether Claude may access your Documents folder**: approve
  it if the clone lives there; the server reads the fetched or built
  database from the repo.
- **A query returns `truncated: true`**: by design. Results are
  row-capped (default 100, hard cap 500) and a truncated result announces
  itself; aggregate or narrow the query instead of raising the cap.
- **A write or PRAGMA attempt refuses**: also by design. Serving is
  read-only three layers deep; the refusal names the failed check
  ([serving spec](spec/serving.md)).
- **`uv sync` fails with `CERTIFICATE_VERIFY_FAILED` while building
  `dbt-core-experimental-parser`**: the parser's source distribution
  fetches its wheel from GitHub releases through the project
  interpreter's own TLS trust, and a python.org framework CPython on
  macOS ships with no CA bundle at its OpenSSL default path. Run the
  framework's `Install Certificates.command` once, or export
  `SSL_CERT_FILE=/etc/ssl/cert.pem` for the session, then rerun
  `uv sync`.

## Where to next

The [README](../README.md) is the front door. The
[gold layer spec](spec/gold-unified-event-star.md) explains the star the
demo queries, including the *Reading the star* rules for its
content-addressed keys. [docs/sources.md](sources.md) lists every
committed extract with its pin, its license, and the vintage effects
the joins carry. The
[sources, explained](sources-explained.md) page carries the reasoning
behind every decision and join the demo sources took, and
[docs/operating.md](operating.md) is the operator's manual. The
[signature test](verification/signature-test.md) is the evidence behind
the project's central claim, and the multi-source proof (D-41) is its
second act: two source families, one star, one calendar, and the joins
measured rather than assumed.
