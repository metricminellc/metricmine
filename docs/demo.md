# The ten-minute demo

> Repo path: `docs/demo.md`
> The full walkthrough behind the README's *See it run* section. Two
> paths: serve the released gold artifact immediately (no build, no
> keys), then optionally replay the entire pipeline from raw data. Every
> command is given for macOS and Linux and, in a collapsed block beside
> it, for Windows (PowerShell).

## What you need

- macOS, Linux, or Windows x64. Windows on Arm is outside the matrix
  (the dbt parser ships no Windows Arm wheel); WSL runs the Linux path.
  On Windows, use PowerShell (Windows PowerShell 5.1 or PowerShell 7,
  either one); Command Prompt is not a target. Clone to a short path
  such as `C:\src\metricmine`: Path B compiles files whose paths run
  past 200 characters below the clone, and a deep OneDrive folder puts
  them over Windows' 260-character limit.
- `git`. macOS offers to install it the first time you type `git`;
  Linux has it in every package manager; on Windows,
  `winget install --id Git.Git -e` or the installer at
  [git-scm.com](https://git-scm.com/download/win). The Windows
  installer asks for administrator approval (`winget` requests it even
  with `--scope user`); where that approval is not yours to give, the
  portable build on the same download page unpacks anywhere with no
  installer, and its `cmd` folder goes on your user PATH.
- [uv](https://docs.astral.sh/uv/). On macOS or Linux:
  `curl -LsSf https://astral.sh/uv/install.sh | sh`. On Windows, in
  PowerShell, the line Astral documents:
  `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`,
  or `winget install --id=astral-sh.uv -e` where a managed execution
  policy refuses it. Then open a new terminal so the shell sees it (the
  installer adds `%USERPROFILE%\.local\bin` to your user PATH). uv
  provisions the pinned Python 3.12 and every dependency; nothing else
  is installed globally. uv installs per user, and nothing after the two
  installs needs administrator rights.
- Windows ships no `make`, so every `make <target>` on this page has the
  form `uv run mm <target>`: the Makefile's targets delegate to that
  entry point and the two are the same code (D-42). A Linux that ships
  without `make` (a fresh Ubuntu, a WSL distribution) runs the same
  `uv run mm <target>` lines, or installs it from its package manager.
  Each Windows block runs in Windows PowerShell 5.1 and PowerShell 7
  alike, one command per line. Elsewhere in the repository, a `make`
  target that is not on this page is the one-line `uv run ...` command
  the Makefile shows for it.
- [Claude Desktop](https://claude.ai/download) for the serving beat
  (optional; Path A works from the terminal without it).
- No API keys, no accounts, no cloud resources. Everything below is
  keyless by design (D-24).

If a Python 3.12 is already on the machine, `python3 scripts/doctor.py`
from the clone (`python scripts/doctor.py` on Windows) answers the first
questions before uv is installed: the platform, the interpreter, its
trust store, and whether uv is on PATH. It reports the rest as measured
after `uv sync`. Without one, skip it: `uv sync` provisions the Python
and `make doctor` measures everything after it.

## Path A: serve the released gold star (2 minutes)

The demo artifact, `demo/demo.duckdb`, ships as a release asset: an
export carrying the gold schema only, verified content-equal by query
to the built warehouse (D-33). The repository commits its digest
manifest, `demo/demo.digest.json`, which names the release to fetch it
from and pins the asset's sha256, size, and content (D-03 as amended by
Amendment S); a code-only release keeps naming the last one that shipped
the artifact. `make demo-fetch` downloads and verifies it, and the MCP
server reads it by default, so serving works from a fresh clone. On
macOS or Linux:

```bash
git clone https://github.com/metricminellc/metricmine.git
cd metricmine
uv sync
make doctor
make demo-fetch
uv run python -c "from metricmine.query import GoldWarehouse; print(GoldWarehouse().list_fact_categories())"
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
git clone https://github.com/metricminellc/metricmine.git
cd metricmine
uv sync
uv run mm doctor
uv run mm demo-fetch
uv run python -c "from metricmine.query import GoldWarehouse; print(GoldWarehouse().list_fact_categories())"
```

</details>

`make doctor` (`uv run mm doctor`) is the preflight: eight checks on the
platform, the interpreter, its trust store, uv, the locked toolchain,
and the artifact, each with the command that fixes it, and exit 0 when
the demo can run. Read it before the fetch, not after something fails.

Between tags, `main` may name no published release in its manifest; the
fetch then says so and Path B (`make demo`, `uv run mm demo` on Windows)
builds the same content keyless in a few minutes.

Expected output: one line, about 5 KB, listing three categories, each
with its fact table, row count, typed table, authored subject, and
registry keys: `airport_weather` (13,014 rows), `flights` (166,158
rows), and `invoice_lines` (44,721 rows). Two of them come from the same
family of sources and share a conformed airport code and the conformed
calendar; the third is the retail sample that shares nothing with them
but the star's shape. For a two-line proof that the server itself
answers, `uv run python scripts/serve_smoke.py` launches it the way a
desktop client does and prints `server: metricmine-gold, 5 tools` and
the three categories with their counts.

### Wire it into Claude Desktop

Merge this entry into `claude_desktop_config.json`, keeping any existing
keys, and replacing the command path with your absolute clone path.
Claude Desktop opens the file from Settings, Developer, Edit Config on
either platform, and creates it there when none exists yet. On macOS the
file is
`~/Library/Application Support/Claude/claude_desktop_config.json`:

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

<details>
<summary>Windows</summary>

The file is `%APPDATA%\Claude\claude_desktop_config.json`; Claude
Desktop opens it from Settings, Developer, Edit Config. The interpreter
is the clone's `.venv\Scripts\python.exe`, and every backslash in the
JSON is doubled:

```json
{
  "mcpServers": {
    "metricmine-gold": {
      "command": "C:\\absolute\\path\\to\\metricmine\\.venv\\Scripts\\python.exe",
      "args": ["-m", "metricmine.server"]
    }
  }
}
```

The command this entry launches is proven over stdio on a fresh Windows
runner in CI (`uv run python scripts/serve_smoke.py` runs it the way a
desktop client does); the click-through in Claude Desktop on Windows
follows the MCP client guide and is not something a runner can measure.
If Claude Desktop came from the Microsoft Store and the server does not
appear after a full restart, the app may read a virtualized copy of the
config at
`%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json`
(anthropics/claude-code issue 26073, open at the time of writing); merge
the same entry there.

</details>

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

Path A is the demo. Path B is the proof behind it, and it provisions
more: on first run it downloads a second, CPython 3.10 environment for
the pinned Airbyte connector (its pandas has no wheel past 3.10) and
installs the dbt packages, so it is the larger install and the one to
run once Path A has answered a question. Every source is a committed
sample (D-15 as amended by Amendment T: the retail extract and the six
aviation extracts, each pinned to its publisher's commit and digest;
[docs/sources.md](sources.md) lists them), so the full path is keyless
too. From the repo root, on macOS or Linux:

```bash
export DBT_PROFILES_DIR="$PWD/transform"
uv run dbt deps --project-dir transform
make ingest
uv run dbt build --project-dir transform --target local
make export-demo
uv run pytest -q
```

<details>
<summary>Windows (PowerShell)</summary>

```powershell
$env:DBT_PROFILES_DIR = "$PWD\transform"
uv run dbt deps --project-dir transform
uv run mm ingest
uv run dbt build --project-dir transform --target local
uv run mm export-demo
uv run pytest -q
```

</details>

Steps 1 to 3 also run as one command, `make demo` (`uv run mm demo` on
Windows): it lands bronze, installs the dbt packages, builds the
contracted models, and exports the artifact, keyless by construction (a
unit test holds the sequence to never invoking a proposer). Run
`uv run pytest -q` after it to verify.

What to expect, step by step:

1. `make ingest` (`uv run mm ingest`) provisions a small connector
   environment on first run (a CPython 3.10 that uv downloads, with the
   pinned connector), then lands **247,555 bronze rows across seven
   tables** exactly as they appear in the committed extracts.
2. `dbt build` compiles the 31 contracted models (nine human-owned
   silver tables, 22 engine-emitted gold objects) and runs every
   generated and declared test: it ends
   **`PASS=334 WARN=0 ERROR=0 SKIP=0`**. Shape is enforced at compile
   time; content rules run as tests with contract-declared severity,
   the declared joins among them.
3. `make export-demo` (`uv run mm export-demo`) rebuilds `demo/demo.duckdb`
   from your freshly built warehouse, verifies it (per-table equal counts plus symmetric
   EXCEPT, and a content digest over every typed view compared across
   per-file connections), and writes `demo/demo.digest.json` beside it.
   The claim is content equality by query, never byte equality (D-33),
   so your artifact proves equal even though its bytes may differ; the
   manifest's content section is what CI holds every build to. The
   export rewrites the committed manifest to name your local artifact
   and no release, so `git status` shows `demo/demo.digest.json`
   modified; `git checkout demo/demo.digest.json` restores the published
   one, and `make demo-fetch` fetches those bytes again.
4. `pytest` runs the full suite, including the local lane that exercises
   the query gate's 29-case refusal matrix, the serving round trip, the
   export verification, the declared-join gate, the aviation
   conservation and business-logic checks, and the demo question set.

## Troubleshooting

Start with `make doctor` (`uv run mm doctor` on Windows; before uv
exists, `python3 scripts/doctor.py`): it checks the platform, the
interpreter, the interpreter's TLS trust store, uv, the locked toolchain,
and the demo artifact (a hint, not a failure, when it has not been
fetched or built yet), and prints the two environment lines the local
dbt lanes need, in the form your shell takes.

- **`uv: command not found`** (on Windows, `The term 'uv' is not
  recognized`): install uv (the lines under What you need) and open a
  new terminal. Everything else flows from it.
- **`make: command not found`** (Linux; a fresh Ubuntu or a WSL
  distribution ships without it): run the same target as
  `uv run mm <target>`, the form every Windows block on this page
  uses, or install `make` from the package manager (`sudo apt install
  make` on Debian and Ubuntu).
- **`dbt` cannot find a profile**: `DBT_PROFILES_DIR` must point at the
  repo's `transform/` directory (the first line of Path B, `export` or
  `$env:`); run dbt from the repo root, not from inside `transform/`.
- **`this tree has no published demo artifact yet` from `make demo-fetch`
  after Path B**: your export rewrote `demo/demo.digest.json` to name
  your local artifact and no release. `git checkout demo/demo.digest.json`
  restores the committed manifest, and the fetch works again.
- **`AirbyteConnectorRegistryError: Failed to connect to the connector
  registry`** during `make ingest` or `make demo`: the connector
  registry at connectors.airbyte.com is unreachable from this network
  (a filtering proxy, an offline machine). Set `AIRBYTE_OFFLINE_MODE=1`
  for the session (`export AIRBYTE_OFFLINE_MODE=1`;
  `$env:AIRBYTE_OFFLINE_MODE = "1"` on Windows) and rerun. The pinned
  connector is already provisioned, and CI lands bronze the same way
  (D-27).
- **Claude Desktop does not show the server**: quit it fully (Cmd+Q on
  macOS; on Windows, exit the app rather than closing its window) and
  reopen it; confirm the config file is valid JSON and the `command` path
  exists (`ls .venv/bin/python` from the repo root, or
  `Test-Path .venv\Scripts\python.exe` in PowerShell). Running
  `uv run python -m metricmine.server` by hand should produce no output
  at all; silence is correct on stdio; Ctrl-C to exit. To prove the
  configured command end to end without the desktop,
  `uv run python scripts/serve_smoke.py` spawns it the way a client does
  and prints the server name, the tool count, and the three categories.
  Claude Desktop keeps its MCP logs under `~/Library/Logs/Claude` on
  macOS and `%APPDATA%\Claude\logs` on Windows; `mcp.log` records the
  connection attempts and `mcp-server-metricmine-gold.log` carries
  whatever the server wrote to stderr.
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
  `uv sync`. This project's own downloads are not affected: they add
  certifi's bundle to whatever this machine already trusts (F-58). The parser
  build above runs in uv's subprocess, outside that code, so it needs
  the interpreter's own trust store wired. `make doctor` names the same
  condition as a `trust store` warning rather than a failure, and stays
  exit 0: the demo path runs on a bare store, this build does not.
  CPython on Windows reads the system certificate store and needs no
  such step.
- **Behind a proxy that inspects TLS**: the demo's own downloads verify
  against the machine's trust plus certifi, so a proxy whose CA the
  machine already trusts (the Windows system store; `SSL_CERT_FILE` on
  macOS or Linux) passes, and this was measured behind one (F-58). uv's
  own downloads use bundled Mozilla roots unless told otherwise:
  `UV_SYSTEM_CERTS=true` reads the platform store, and `SSL_CERT_FILE`
  names a bundle (uv then trusts that file alone).

Windows:

- **`The term 'uv' is not recognized`** right after installing: the
  installer added `%USERPROFILE%\.local\bin` to your user PATH, but a
  terminal that was already open does not see it. Open a new one.
- **The installer line is refused by execution policy**: the line under
  What you need carries `-ExecutionPolicy ByPass` for that one process,
  which needs no administrator rights. Where a managed policy refuses
  even that, `winget install --id=astral-sh.uv -e` installs the same uv.
- **The git line asks for an administrator**: the Git for Windows
  installer requests elevation, `--scope user` included. Approve it if
  the machine is yours. Where it is not, the portable build on the
  git-scm.com download page unpacks anywhere with no installer; put its
  `cmd` folder on your user PATH and open a new terminal. Everything
  after git installs per user.
- **`python` opens the Microsoft Store**: Windows ships an alias that
  does so when no Python is installed. Nothing here needs one: uv
  provisions the project's Python during `uv sync`, so skip the
  pre-install check and run `uv run mm doctor` after the sync.
- **`The token '&&' is not a valid statement separator`**: Windows
  PowerShell 5.1 has no `&&`. Every Windows block on this page is one
  command per line; PowerShell 7 accepts either form.
- **`The term 'make' is not recognized`**: expected. Windows ships no
  `make`; run `uv run mm <target>` for the demo-path targets, and for
  any other `make` line the one-line `uv run ...` command the Makefile
  shows for it.
- **`$env:` is not recognized, or the environment line does nothing**:
  you are in Command Prompt. Open PowerShell (Windows PowerShell 5.1 or
  PowerShell 7) and run the same lines there.
- **`uv sync` fails building `dbt-core-experimental-parser` with `no
  prebuilt ... wheel for this platform`**: this is Windows on Arm. The
  parser ships wheels for Windows x64, macOS, and Linux only, so the
  Windows path is x64 only; WSL runs the Linux path.
- **A path-too-long error during Path B**: dbt compiles test files whose
  paths run past 200 characters below the clone. Clone to a short path
  (`C:\src\metricmine`), or enable long paths in Windows and in Git
  (`git config --global core.longpaths true`).
- **Line endings**: Git on Windows is often set to convert line endings
  on checkout (`core.autocrlf=true`). The repository's `.gitattributes`
  keeps every text file LF regardless, so the contracts' hashes and the
  samples' digests measure the same on every platform. A clone made
  before that file existed can still show `w/crlf` in
  `git ls-files --eol` after pulling it; clone again.

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
