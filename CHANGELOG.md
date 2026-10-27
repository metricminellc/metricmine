# Changelog

All notable changes to MetricMine are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
semantic versioning from the first tagged release onward; the stable line
begins at v1.0.0. Entries cite the decision or finding that governs them;
the [decision register](docs/decisions/decision-register.md) is the
binding text, and the
[findings register](docs/verification/gate_proof_findings.md) carries the
measurements.

## [Unreleased]

### Added

- `docs/experiments/`, the experiments lane's written records
  (CLAUDE.md rule 19): the record of E1's canary, measured on Claude
  Desktop on October 21, 2026 (on Claude Desktop 3.1623.0 with the
  model measured, the server's `instructions` do not reach the model,
  so the staged paragraph experiment ends at its canary and the
  serving layer is unchanged), and the experiments register's
  deferred design questions (X-01 to X-06), graduated with each
  item's status measured on main at `2f73dfc`. Nothing in the lane
  binds; no decision and no finding is minted.
- `docs/experiments/e3-skeleton-and-context.md`, the record of E3, the
  skeleton and the context channel on the proposers' API path, as
  measured on October 23, 2026, on the branch
  `experiment/e3-skeleton-and-context` at `cb27197` (420 live runs at
  the three allow-listed models under a key committed before run one;
  the skeleton earned its place by the key's rule and the context
  channel did not in the form it ran), with the lane's index row; and
  finding F-73 in the findings register, the one behavior of head's
  own path the runs measured: at the describe stance the first attempt
  on the 34-column `silver_flights` table stops on the 16384 `max_tokens`
  cap in 14 of 20 runs and the bounded retry re-sends the truncated
  response. Nothing
  in the lane binds; no decision is minted; the proposers, the
  prompts, the pins, and the serving layer on main are unchanged.
- D-44, governed meaning, and Amendment AC to D-35 in the decision
  register (Decision Record 016): the glossary and ontology registers
  as ordinary contracts with rows in git, in the documents register's
  shape; a term identified by a stable id and a content digest over
  its label and definition, a concept by a node digest; a binding by
  id and digest, in the register first and in no data contract; the
  change-set command with its closed vocabulary, its classes
  (additive, changing, removing; deprecate then drop; a changed
  definition re-binds every element that cites it under one recorded
  intent), and the pull request as the only approval; the scan's
  Governed meaning section with its derived states; and the module's
  boundary, under which a term or a concept is never a proposer
  input (CLAUDE.md rule 15, the agent-layer spec's section 7). The
  decision mints before any implementing change: no code, contract,
  pin, prompt, or model changes here.
- Finding F-74 in the findings register, measured at head on October
  26, 2026: the governed documents `bind` command fences its draft
  directory by resolving it under `proposals/` and then writes each
  file by path, so a symbolic link planted at a draft file's path
  carries the draft into `documents/register/bindings.yaml` while the
  command prints that the register is unchanged. The finding bounds the
  assurance (design rule 5 of the governed host plan): a draft is
  written through no link, and a command prints that a protected
  folder is unchanged only after it checked. The fix rides the
  governed meaning slice as a fence both modules share; nothing on
  main changes here.

### Changed

- The digest manifest names the v1.2.0 release asset, `demo.duckdb`
  built from the tagged commit, so `make demo-fetch` restores the
  regenerated star with compiled context v0014 and the corrected
  quantity sentence (F-62; HW-51 closed for anyone who fetches the
  demo); the front door names v1.2.0 as the current tagged release.

## [1.2.0] - 2026-10-21

Governed documents, served: the compiled context carries the register's
certified bindings into `get_context`, labeled as document text a
person bound in the register, under a measured budget, and the
regenerated star behind it is the first built on dbt Core v2. The
refreshed demo asset carries the corrected quantity sentence (F-62), so
a stranger who fetches the demo reads one sentence where two could not
both be true (HW-51). The query tool reads gold by default with an
explicit opt-in, and the five tools declare their annotations.

### Added

- Decision D-43, governed documents, in the decision register (Decision
  Record 014): a document a person certified as the source of a
  contracted column's meaning is governed through a small register that
  records the binding and says where the document's approval lives; the
  governance classes `in_repo`, `platform_governed`, and `pinned`; the
  access classes `in_repo`, `public`, `local_path`, and `pointer_only`;
  the certification source as a closed field; identity as the
  extracted text, never the bytes; anchors and their measured limit; a
  person as the only declarer or binder; register-only first; and the
  boundary of the documents module, deterministic code that never opens
  a private location. Amendment Z to D-35: the scan reports every
  governed document's state, derived on every run and never stored, in
  a fixed vocabulary. Findings F-68 through F-71, measured in the prep:
  the pinned linter resolves a column-level link of type `definition`
  (an HTTPS fetch) or `semantics` (the vendor's semantics service) and
  fails the contract when the resolution fails, and the newest linter
  also fetches `businessDefinition`; a Word or PowerPoint
  file's bytes change on every save while its words do not, so a byte
  digest is not a document's identity; the common Python readers'
  convenient reads miss tables, text boxes, headers, footers, footnotes,
  endnotes, grouped shapes, and notes, and read a pending redline as
  neither view; and an anchor check measures presence, so a
  contradiction beside an untouched quote reads as intact. An addendum
  to F-67 records the fix measured on the Windows legs of its own pull
  request.
- Amendments AA and AB in the decision register (Decision Record 015),
  the first lettered past Z under the scheme the register's header now
  records (two letters in spreadsheet column order). Amendment AA, to
  D-30 and D-31 jointly: the compiled context carries the governed
  documents register's certified bindings, per bound field a `sources`
  list under `expert_context` and per entry a top-level `documents`
  block beside `data` and `expert_context`, declared apart from
  measured, labeled as document text a person bound in the register as
  it read when the context compiled, never a document's text beyond the
  bound quote, never a location the consumer's own host could not open,
  never that a binding was reviewed or a document is current;
  a harvest budget of 4,000 characters per entry, measured and held by
  the compile failing closed; the register's digest and each served
  document's text digest join the artifact's freshness check; compiled
  schema 2.1.0. Amendment AB, to D-31: the five tools declare a title
  and the MCP specification's annotations (HW-47), which declare and
  never prove, and `query` reads the gold schema by default with
  `MM_SERVE_SCOPE=all` as the explicit opt-in for the modeler's read
  path (HR-8). Finding F-72: DuckDB's `query`, `query_table`, and
  `json_execute_serialized_sql` table functions evaluate a string as a
  statement or a table, `duckdb_table_sample` and `pragma_storage_info`
  take a table's name, and a CTE can shadow its own source, so a scope
  gate on a statement's base tables alone is open; the served `query`
  refuses the five functions by name and reads CTE names by scope. The
  serving spec carries both amendments (§2.2, §3.1, §7)
  and corrects a §3 example that named a table function the engine does
  not have.
- `contracts/documents_register.odcs.yaml`, the governed documents
  register's contract (D-43): two table objects, `documents_standing`
  and `documents_bindings`, with their quality rules, and no dbt model;
  gate three records it as having no model, and the contract-change
  issue form lists it.
- Governed documents, slice 1 (D-43; D-35 as amended by Amendment Z):
  `src/metricmine/documents/`, deterministic code and never an agent,
  with extractors for text, markdown, Word, and PowerPoint on the
  standard library that read every text part they name (tables, text
  boxes, headers, footers, footnotes, endnotes, grouped shapes, and the
  notes found through the package's relationships; F-70), refuse
  untrusted input under fixed limits, and give a redlined Word file its
  standing and accepted views; the register as two YAML tables under
  `documents/register/` held to `contracts/documents_register.odcs.yaml`
  by `verify` and the unit lane, with a declarer or binder refused when
  code can tell it is an agent or a model; the derived states
  (`in_sync`, `changed_anchors_intact`, `anchor_broken`, `unreachable`,
  `unverified_pointer`, `unsupported_format`, `refused_package`,
  `no_text_layer`, with the `review_overdue`, `pending_changes`,
  `binding_broken`, and `extractor_changed` flags); the `find`,
  `inspect`, `bind`, and `verify` commands (`make doc-find`,
  `doc-inspect`, `doc-bind`, `doc-verify`), where `bind` drafts into the
  outbox and never writes the register; the demo's first binding,
  `silver_nyc_flights.dep_delay_minutes` to the `flights` help page of
  nycflights13 at `df98ef21` (CC0), committed under
  `documents/sources/nycflights13/` with its upstream URL and digest;
  `docs/documents.md`; and the CLAUDE.md boundary for the module.
- Governed documents served (D-30 and D-31 as amended by Amendment AA;
  D-43): the context compiler harvests the register at compile time
  (`src/metricmine/context/harvest.py`, deterministic code that reads
  committed files only and never a calendar) and the compiled context
  carries, per bound field, `sources` (the anchor a person bound,
  verbatim, with its locator and document id) and, per entry, a
  top-level `documents` block beside `data` and `expert_context`,
  listing each cited document once, declared apart from measured, under
  a note that names it document text a person bound in the register as
  it read when the context compiled, with git holding the review, and
  says the server never opens a document and never says one is
  current; the harvest is held to the
  amendment's budget of 4,000 characters per entry by the compile
  failing closed; the register's digest and each served document's
  text digest join the artifact's `sources`, so a binding change reads
  as stale until `make context` runs; compiled schema 2.1.0; the
  artifact moves to v0014 with the golden oracle refreshed beside it
  (F-21's packaging rule). A second binding rests
  `silver_flights.dep_delay_minutes`, the mapped column, on the demo's
  quote, and `make context` prints that the level-zero binding is not a
  served field. The server's instructions say what the served sources are and
  are not; `docs/documents.md` gains "What is served"; CLAUDE.md rule
  18, the context compiler's boundary, and the documents module's
  boundary say so.
- The tool surface's hints and the query tool's scope (D-31 as amended
  by Amendment AB): every tool declares a title and the MCP
  specification's annotations (read-only, not destructive, idempotent,
  closed world; HW-47), which declare and never prove, the three layers
  proving the posture; and `query` reads the gold schema by default
  (HR-8), refusing a base table outside it, `information_schema`
  included, a schema-less name out of a CTE's scope, and the table
  functions that take a table's name or a statement as a string
  (`query`, `query_table`, `json_execute_serialized_sql`,
  `duckdb_table_sample`, `pragma_storage_info`; finding F-72), naming
  what was refused and the opt-in, `MM_SERVE_SCOPE=all`, for the
  modeler's read path against a working warehouse; the server writes
  its instructions and the query tool's title from the scope it runs
  with, opens the served database at startup, and fails there on any
  other value or a missing file. The
  server instructions, the operating manual (the paragraph HW-58 b
  owed: raw rows reach the host's model provider under the opt-in), and
  CLAUDE.md rule 18 say so; the scope matrix lives in
  `tests/test_query_scope.py`.
- `.mcp.json` at the repository root registers the gold server as a
  project MCP server for Claude Code, launched with `uv run --no-sync`
  so a clone that was never synced fails fast and installs nothing
  (F-63); the contributing guide and the demo guide say what the file
  does and that `uv sync` is the fix.
- Findings F-59 through F-63 in the findings register, from the Arc 8
  audit, the Sitting T validation, the September 17 probes, and the
  Prep A probes: the
  git installer's elevation prompt, the connector registry behind a
  filter, the manifest after Path B, the stale restatement in the
  mapping contract and the class behind it, and the committed
  `.mcp.json`; an addendum to F-54 records the one local test that
  fails instead of skipping without a warehouse.
- Item 10 in the contract review checklist: when a description
  changes, read every contract that restates that column in other
  words, on both edges (F-62).
- The demo guide carries what the first agent-driven Windows run
  reported (a run dated September 23, 2026, reported on October 2): a
  troubleshooting entry for the Microsoft
  Store build of Claude Desktop, whose virtualized `AppData` breaks
  `uv sync` from a terminal the app opened (F-64); the warehouse lock
  a killed run leaves; the `NativeCommandError` text Windows PowerShell
  5.1 paints on captured stderr; two routes for `dbt deps` on a
  network that reaches github.com and not the package hub (F-60
  addendum); which tests skip on which platform and what the
  demo-question tests read; and a short section for the case where an
  agent runs the demo. Findings F-64 and F-65 in the findings
  register, with addenda to F-55 (the desktop step stays unmeasured)
  and F-60.
- Two addenda from the dbt Core v2 sitting of October 5: the second
  addendum to F-63 closes HR-5 (on a base that carries `.mcp.json`,
  the repository's Claude Action loads the project server and the
  session lists its five tools; the log prints no launch line, so the
  reply is the evidence), and an addendum to F-66 records the Windows
  legs of the toolchain pull request (the pinned wheel's `.pyd`
  registered as dbt's driver, 31 models and 303 tests printed on the
  `pwsh` leg and the same demo path green on the `powershell` leg, the
  first run's one path-form test failure, and the DuckDB version the
  legs do not print).
- Finding F-67 in the findings register: PyAirbyte 0.53 leaves each
  temporary file read-only and retries its deletion five times, one
  second apart, which Windows refuses, so a landing there spent about
  140 seconds and left 35 files in the temp folder (measured on the
  toolchain pull request's Windows legs); an addendum to F-64 says its
  temp half was this mechanism and not the Store build's redirection.

### Changed

- `pyproject.toml` carries the release line, `1.2.0`, in place of
  `1.1.3`, with `uv.lock`'s own `metricmine` entry; the server reports
  it to every client as `serverInfo.version`.
- The regeneration (D-09): the emitted gold set under
  `transform/models/gold/` and its ownership manifest carry
  `gold_invoice_lines_mapping` v1.1.2 (held since October 3) and
  compiled context v0014, so the served `context_registry` row for the
  flights measures entry carries the demo's bound source; the emission
  oracle and the emitted set are equal again. The digest manifest's
  content block is refreshed from the regenerated build (the registry's
  digest moves; every row count and typed view digest stands) and names
  no release until the manifest pull request after v1.2.0 names its
  asset (F-61). Demo question Q8, "What does the departure delay
  definition rest on?", joins `tests/fixtures/serving_questions.json` as
  a context question answered through `get_context`, the demo guide's
  "Ask it something" list, and the local lane, which now counts ten
  demo-question tests.
- The `demo-windows` workflow reads which release the committed manifest
  names before Path A and skips the four fetch-dependent steps with a
  notice when it names none, so a tree between a regeneration and its
  release still measures Path B on both shells (an addendum to F-61
  records the window's reach); the steps run whenever a release is
  named.
- The scan's plan carries a Governed documents section (D-35 as amended
  by Amendment Z): the register's standing, the state counts, and one
  item per document with its next command, derived on every run and
  never stored; `plan.json` gains the `documents` key and
  `scan_schema_version` moves to 1.1.0. Document items never enter the
  queue the batch driver walks. The operating manual's command table,
  the gates table, and the glossary, the adoption guide's states, and
  the contract review checklist (item 10's third edge, document to
  description, and item 11, the link types a column-level pointer may
  carry; F-68) say so.

- The dbt line is dbt Core v2: `dbt-oss` 2.0.x (resolved 2.0.5) in
  place of `dbt-core` 1.12 and `dbt-duckdb` 1.11 (D-05 as amended by
  Amendment X); `transform/dbt_project.yml` mirrors the range; the one
  column-level `meta` key v2 refuses moves under `config` (F-66); the
  lock drops 26 packages and adds one. `uv run mm driver` (`make
  driver`) registers the engine inside the pinned duckdb wheel as dbt's
  ADBC driver through a manifest under `.adbc/` (gitignored), the
  Makefile exports `ADBC_DRIVER_PATH`, `mm demo` writes the manifest and
  passes the variable to its dbt steps, the contract-gate workflow sets
  it on its job (the Windows legs reach it through `uv run mm demo`),
  and `make doctor` gains a ninth check for the registration and prints
  the export beside the two F-09 lines. `dbt_utils` 1.3.3 is vendored at
  `transform/vendor/dbt_utils` with its LICENSE and a NOTICE paragraph;
  `packages.yml` names it as a local package and `package-lock.yml`
  carries v2's form, so the package hub is never reached. The README,
  the demo guide, the operating manual, and the engine spec name the new
  line; the guide's `dbt deps` entry for a hub-less network and its two
  `dbt-core-experimental-parser` entries become the engine's download
  entry, the driver entry, and the platform entry.
- Gate two runs `dbt run` and then `dbt test` in place of `dbt build`
  (D-20 as amended by Amendment Y): in CI, in `make demo` (`uv run mm
  demo`), and in the demo guide's and the operating manual's lines. The
  sync-generated singular tests of the level-zero silver tables carry
  no dependency edge (F-51), and dbt Core v2 schedules them before the
  models on a cold build (F-66); the models first and the tests second
  keeps every test and every verdict on both dbt lines.
- The dbt line moves to dbt Core v2 by register amendment before any
  implementing change lands: Amendment X to D-04 and D-05 (the plane is
  `dbt-oss` 2.0.x; the deferral lifts on the GA of September 14, 2026,
  proven at 2.0.5; the DuckDB driver is the pinned wheel's engine,
  registered by the project; `dbt_utils` is vendored as a local package;
  the one properties key v2 refuses moves under `config`), Amendment Y
  to D-20 (gate two is `dbt run`, then `dbt test`, because the
  edge-less generated tests of the level-zero silver tables schedule
  first on a cold build under v2), and the confirmation of D-06 under
  v2 (datacontract-cli stays at 1.0.12). Finding F-66 records the v2
  build and what the engine refuses, downloads, and resolves; an
  addendum to F-63 records what the repository's Claude Action did with
  the committed `.mcp.json` (it restored the file from `origin/main`,
  where it did not yet exist). `CLAUDE.md` rules 1 and 2 and its
  toolchain section name the new line.
- `gold_invoice_lines_mapping` v1.1.2 (D-08, a description patch):
  the quantity sentence restates silver v1.3.0 instead of
  contradicting it, so a consumer no longer reads two sentences that
  cannot both be true (F-62); compiled context v0013 carries the
  corrected sentence (D-30, F-29), and the emission oracle under
  `tests/golden/emitted/` is refreshed beside the bump (F-21). The
  emitted models follow in the regeneration pull request (D-09), and
  the published artifact at the next release that carries one.
- The three public spec examples that restated the stale quantity
  sentence (`docs/spec/engine/example-mapping-contract.odcs.yaml`,
  `docs/spec/agent-layer/example-gold-mapping-proposal.json`,
  `docs/spec/agent-layer/example-silver-cleanup-proposal.json`) carry
  the corrected one (F-62); the earlier compiled-context artifacts and the
  evidence files are history and are unchanged.
- `pyproject.toml` carries the release line, `1.1.3`, in place of the
  `0.1.0` the server had reported to every client as
  `serverInfo.version`; `uv.lock` follows by one line, and the release
  procedure in the operating manual sets the value from here on.
- The contract change issue form lists all thirteen committed contracts
  in place of three.
- `CLAUDE.md` rule 1 names the mcp resolution `uv.lock` has carried
  since #142, 1.29.1, and D-32 carries a dated correction note saying
  the same; the contributing guide's provenance paragraph names the
  seven committed extracts `docs/sources.md` registers in place of one
  sample.
- `CLAUDE.md` rule 7 names the adapter in force: `materialized_view`
  is not implemented by dbt Core v2's built-in DuckDB adapter (a model
  configured with it parses and fails at run, measured at 2.0.5), as it
  did not exist on dbt-duckdb 1.x; and its conventions carry the
  pure-path rule for tests that assert a path's printed form, which
  the toolchain pull request's first Windows run earned.
- The demo guide scopes the administrator-rights sentence to what is
  true: uv installs per user and nothing after the two installs needs
  elevation, while the Git for Windows installer asks for it, `--scope
  user` included, and the Windows troubleshooting group names the
  portable build for a machine where that approval is not yours to give;
  the Claude Desktop entry says that Settings, Developer, Edit Config
  opens or creates the config file on either platform, and the
  troubleshooting entry for a server that does not appear names where
  Claude Desktop writes its MCP logs.
- The demo guide names the `uv run mm <target>` form for a Linux that
  ships without `make`, with a troubleshooting entry keyed to
  `make: command not found`; a troubleshooting entry keyed to the
  connector registry error names `AIRBYTE_OFFLINE_MODE=1`, the form
  CI lands bronze in (D-27), for a network that cannot reach the
  registry; the Path B notes and the contributing guide say that the
  export rewrites the committed manifest and that `git checkout
  demo/demo.digest.json` restores it before a fetch, with a
  troubleshooting entry keyed to the fetch's refusal; and the listing
  line's expected size reads about 5 KB, as measured, in place of 11.

### Fixed

- The bronze landing gives each of PyAirbyte's temporary files its
  write bit back before PyAirbyte's own cleanup runs, by rebinding
  `as_temp_files` in the two PyAirbyte modules on the landing's path,
  so a Windows landing no longer spends four seconds per file in a
  retry loop that ends in `Failed to remove temporary file` and no
  longer leaves 35 files behind (F-67); the shim installs at the top of
  the landing's `main`, which `mm ingest` and `mm demo` both run, on
  every platform, and refuses a PyAirbyte whose binding it does not
  recognize. Its tests simulate the Windows refusal, so they tell the
  fixed code from the broken code on Linux and macOS too, and they fail
  when a PyAirbyte release moves the helper's binding or adds a call
  site the shim does not cover. The demo
  guide's Microsoft Store entry drops the `TEMP` and `TMP` lines, which
  did nothing for the warning, and keeps the two uv variables.
- The compiler tests' mini repository falls back to a copy of
  `contracts/` where the platform refuses a symlink, so the three
  tests no longer depend on the privilege a per-user Windows account
  lacks and the runners hold (F-65); a unit test makes the symlink
  call raise so the fallback runs on every platform.
- The local-lane test of the served registry declaration reads the
  mapping version from the ownership manifest, what the committed
  emission was generated from, in place of the contract file, which
  is one version ahead for the whole gate-quiet window between a
  mapping bump and its regeneration; the Windows job runs the whole
  suite, so the window was red there (F-21 addendum).
- The preflight's interpreter line, the one FAIL that named no fix:
  on a Python that is not 3.12 (the pre-uv form on a system Python),
  `python` now reads `uv sync provisions it, then make doctor` (`uv run
  mm doctor` on Windows), so every FAIL line names the command that
  fixes it, as the guide and the site say.

## [1.1.3] - 2026-09-11

The first run, on a machine nobody prepared: the front door, the demo
guide, the operator's manual and its companions, and the preflight carry
what a stranger on macOS, Linux, or Windows x64 needs to reach a served
star on the first attempt, and the two exit records the ladder owed
(`docs/verification/evidence/2026-09-06_arc7_exit.md`,
`docs/verification/evidence/2026-09-11_arc8_exit.md`) land. No pin,
contract, model, or demo content changed; code-only, and the committed
manifest keeps naming the v1.1.1 asset.

### Added

- The Arc 7 exit record, prepared as that arc's seventh rung and never
  landed, with the material the F-58 fix added (the four consumers of
  doctor's exit code, the Windows anchor counts, the method lessons);
  the Arc 8 exit record.

### Changed

- The operator's manual, the adding-a-source walkthrough, the
  contributing guide, the serving spec, the bug report form, and the
  docs map carry the Windows text beside the macOS and Linux one: the
  PowerShell twins of the environment lines, the short form, and the
  cold build; the platform paragraph mapping every other `make` target
  to the `uv run ...` line the Makefile shows; the Claude Desktop entry
  for Windows in the spec; `uv run mm doctor` in the form; the
  contributing guide's sentence about restoring a committed artifact
  with `git checkout` gives way to the release-asset truth (Amendment
  S). The docs map gains the four documents it did not list
  (`sources.md`, `sources-explained.md`, `adding-a-source.md`,
  `operating.md`) and its demo row names the release asset. Promised
  for these documents in the v1.1.1 release notes; landing here.
- The demo guide for a stranger on any supported platform: What you need
  names git and uv with the lines that install them (the Windows uv line
  as Astral documents it, with `-ExecutionPolicy ByPass`, and winget
  beside it), PowerShell rather than Command Prompt, a short clone path
  with the measured reason, and no step needing administrator rights;
  `make doctor` (`uv run mm doctor`) sits before the fetch in Path A and
  the pre-uv form is named; every platform-dependent block has its
  Windows twin collapsed beside it (Path A, the Claude Desktop entry with
  both config paths and the Store-build note, Path B with its `$env:`
  line); Path B says what it additionally provisions; the troubleshooting
  section names both forms of every command, the error text Windows
  prints, a proxy entry measured behind one, and a Windows group; the
  artifact sentence names the release the manifest points at. The
  sentence claiming a recording is attached to the latest release is
  gone. The `demo-windows` workflow's comment, which calls its install
  line the documented one verbatim, is true again.
- `make doctor` (`uv run mm doctor` on Windows) runs before uv exists:
  `python3 scripts/doctor.py` on any Python 3.12 answers the platform,
  the interpreter, the trust store, and whether uv is on PATH, and reports
  the locked toolchain and the demo artifact as measured after `uv sync`
  instead of failing on a system Python or raising on the artifact's
  import (measured on a fresh clone: a traceback at `import duckdb` and
  no check printed). A check that raises now records its own FAIL line
  while the others still print. Still eight checks.
- The front door: See it run carries the Windows block collapsed beneath
  the macOS and Linux block, with `make doctor` (`uv run mm doctor`) as
  the step before the fetch; the artifact sentence names the release the
  manifest points at rather than every tagged release; the release line
  and the status paragraph name v1.1.2; the digest sentence names the
  Windows runner as the third machine; the decision count reads
  forty-two; the Toolchain section states the mapping rule for every
  other `make` target. The sentence claiming a recording is attached to
  the latest release is gone: no release since v0.2.0 carries one.

## [1.1.2] - 2026-09-09

### Added

- `certifi` as a declared dependency at a floor (`certifi>=2026.6.17`,
  resolved 2026.6.17 in uv.lock), and `src/metricmine/tls.py`, the one
  place this project builds a TLS verification context. A floor rather
  than a pin, and deliberately outside CLAUDE.md rule 1: certifi ships
  trust anchors rather than an API, so a refreshed bundle is the point
  of the dependency (F-58).
- `make doctor` (`uv run mm doctor` on Windows) reports the interpreter's
  TLS trust store, and warns when nothing is loaded and no capath could
  load one lazily, saying that the demo path carries its own CA bundle
  and runs and that other Python tools on that interpreter may not. The
  capath clause matters in both directions: a capath verifies fine while
  reporting zero anchors, and a cafile aimed at a file that parses to
  nothing does not, so pointing `SSL_CERT_FILE` at the wrong file cannot
  silence the warning. A warning and not a failure because the fix below is what made
  a bare store survivable: doctor's exit code gates the devcontainer's
  `postCreateCommand` and the `demo-windows` preflight, so failing there
  would red a machine whose demo works. The diagnosis prints above the
  demo-artifact line it explains. Eight checks now, seven before.

### Changed

- The demo guide's `CERTIFICATE_VERIFY_FAILED` entry says the project's
  own downloads now carry certifi, and scopes itself to `uv sync`
  building `dbt-core-experimental-parser`, whose source distribution
  fetches its wheel with urllib in uv's own subprocess and is not
  reached by this fix (F-58).

### Fixed

- The three keyless download paths (`scripts/fetch_demo.py`,
  `scripts/fetch_common.py`, `scripts/fetch_sample.py`) called
  `urllib.request.urlopen` with no `context=`, so Python built one from
  `ssl.create_default_context()` and loaded OpenSSL's default verify
  paths and nothing else. A python.org framework CPython on macOS ships
  with those paths empty until `Install Certificates.command` has run,
  so every fetch died with `CERTIFICATE_VERIFY_FAILED` before anything
  built, and the failure read as a broken project rather than as a
  missing CA bundle on the reader's own interpreter. All three now share
  one context that adds certifi's anchors to whatever the machine
  already trusts, rather than replacing them: naming a cafile on
  `create_default_context` skips the branch that loads the Windows
  certificate store, the system bundle on Linux, and any exported
  `SSL_CERT_FILE`, which on one measured machine dropped 54 of its 113
  anchors.
  `scripts/fetch_common.py` is the shared download for all six source
  fetch scripts, so a contributor following `docs/adding-a-source.md`
  hit the same wall. Pre-existing since before v1.1.0, and off the
  Windows path, where the system certificate store supplies the anchors
  (F-58). Discharges the item Arc 6 carried forward.
- The release link references: v1.1.1 shipped without a `[1.1.1]:` line
  and `[Unreleased]` still compared from v1.1.0.
- `CONTRIBUTING.md` said the project runs on macOS or Linux; Windows x64
  joined the supported matrix at v1.1.1 (D-42).

## [1.1.1] - 2026-09-06

### Added

- Decision Record 012: D-42, the supported platforms (macOS, Linux, and
  Windows x64 on Python 3.12) and the task entry point `uv run mm
  <target>` the Makefile delegates to for the demo path, with the
  Windows text rules, the line-ending rule, what stays outside the
  matrix and why, and the desktop step as documented until a person
  confirms it; findings F-54 (the local lint lane on a machine without
  the isolated tool) and F-55 (what a Windows runner proves of the
  desktop step, and what waits on a person). CLAUDE.md rule 19, the
  Toolchain section, and the guard note carry the platform text.
- The task entry point `uv run mm <target>` for the demo path
  (`src/metricmine/tasks.py`, declared under `[project.scripts]`): the
  Makefile's six demo-path targets (`doctor`, `demo-fetch`, `ingest`,
  `demo`, `export-demo`, `demo-manifest`) delegate to it, so one
  implementation serves macOS, Linux, and Windows and `RELEASE=` travels
  as `--release`; `command(target)` names a target in the running
  platform's form for every hint the demo path prints (D-42).
- `.gitattributes`: every text file checks out LF on every platform
  (`* text=auto eol=lf`), the binary classes named, and the captured
  evidence and the committed samples kept byte-verbatim (`-text`), so a
  Windows clone hashes the bytes the Mac and CI hash (D-42).
- `scripts/serve_smoke.py`: the stdio proof of the command the Claude
  Desktop config launches (the venv interpreter with
  `-m metricmine.server`, spawned from outside the repository with the
  SDK's minimal environment); exit 0 on the server name, five tools, and
  three categories (F-55).
- The `demo-windows` workflow: Path A and Path B of the demo guide on a
  fresh `windows-latest` runner in PowerShell 7 and Windows PowerShell
  5.1, with a line-ending census, the stdio smoke, the manifest gate
  against the committed manifest, and the test suite, on every change to
  the demo path and every push to main (D-42).
- The eight recorded live proposals for the aviation family under
  `tests/agents/fixtures/recorded/`, copied verbatim from the September
  4 eval study (claude-sonnet-5, one run per fixture); the recorded
  render and lint tests no longer skip by name.
- Oscar, the repository's resident guide (`.claude/agents/oscar.md`): a
  read-only Claude Code subagent that answers how the system works and
  where a task is done from the repository's own files, cites the file
  and line, and runs the contract-review checklist on request. SDLC-layer
  tooling in the D-37 posture; not a pipeline agent, so the D-10 count is
  unchanged.

### Changed

- `make doctor` (`uv run mm doctor` on Windows) passes Windows x64 as in
  the matrix, names Windows on Arm as outside it with the reason, prints
  the two environment lines in the running shell's form, and names its
  hints in that form too (D-42). Still seven checks.
- Every hint the demo path prints names its remedy in the running
  platform's form: the fetch (`scripts/fetch_demo.py`), the digest check
  (`scripts/check_demo_digest.py`), the exporter, and the serving module's
  fail-closed message, which now names `make demo-fetch` or `make demo`
  (`uv run mm ...` on Windows) in place of the stale committed-artifact
  sentence.
- The read-only contract-reviewer subagent is folded into Oscar; its
  review rules are unchanged, and the `/contract-review` Skill is
  untouched.

### Fixed

- After Path B, `uv run pytest -q` on a machine without the isolated
  `datacontract-cli` failed fifteen local lint tests on a missing
  executable although the demo guide says the demo runs without that
  tool; the module now skips by name with the reason (F-54: 15 failed
  before, 15 skipped after; the gates are CI's).
- `scripts/serve_smoke.py` reads the server's pipes itself, every wait
  bounded, each answer printed with its size and latency as it arrives,
  and the shutdown measured: cycle one of the Windows check hung at the
  smoke for the job's whole hour with nothing printed (F-56, whose cause the
  finding names: DuckDB's lazy pandas import on the first parameterized
  query, stalled on Windows behind the reader's pending stdin read). What the smoke proves is unchanged: the server name, five
  tools, and three categories from the command the desktop config
  launches.
- `src/metricmine/server/__main__.py` imports pandas, numpy, and pyarrow at
  startup, before the stdio transport parks its first read. On Windows
  DuckDB's lazy pandas import on the first parameterized query loads numpy's
  bundled OpenBLAS DLL, whose libgfortran constructor calls `fstat(0)`;
  Windows serializes that behind the SDK reader's pending `ReadFile`, so the
  first tool answer hung until the client sent another line (F-56, numpy
  issue 24290). Loading the modules before the reader starts moves the load
  off the request path; the demo and the smoke need no change.
- The ourairports reader options in `config/default.yaml` declare
  `encoding: utf-8`. The source-file connector reads a CSV in the
  platform's default encoding when the reader options name none, which is
  cp1252 on Windows; `ourairports_airports` carries 1,310 non-ASCII lines
  whose UTF-8 bytes are not valid cp1252, so its check failed on Windows
  and nowhere else (F-57). The earlier file-URI attempt (#188) was wrong
  and is reverted.
- The `online_retail_ii` reader options in `config/default.yaml` declare
  `encoding: utf-8`, the same fix as the ourairports samples. Its pound
  signs are two UTF-8 bytes the Windows cp1252 default read as two wrong
  characters, which the D-33 digest gate caught on the Windows build; the
  demo build now reads every sample as UTF-8 on every platform. A no-op
  off Windows, where UTF-8 was already the default (F-57).

## [1.1.0] - 2026-09-05

The multi-source proof (D-41): a second family of sources through the
same pipeline, one star, one calendar, and the joins measured rather
than assumed. Additive contract semantics; the fact primary key is
unchanged.

### Added

- Decision Record 011: D-41, the multi-source proof and the star trial,
  with its claim (co-location in gold, conformance in silver, service
  through the typed surfaces), its exit criterion written before the
  first source landed, and its verdict appended at the exit; Amendments
  R (the conformed calendar, D-17), S (the demo artifact as a release
  asset with a committed digest manifest, D-03 and D-33), T (committed
  samples plural with pinned, digest-checked fetch scripts, D-15), U
  (the engine fan-in, D-29), V (compiled schema 2.0.0 with conformed
  keys, D-30), and W (the data and expert-context split in the
  registry, the subject and context keys on the category listing, D-30
  and D-31); findings F-36 through F-53. The specs (engine, gold,
  ingestion, serving, agent layer, profiler) and CLAUDE.md rules 9,
  12, and 18 carry the amended text; the non-goal on source types
  reads as one ingestion connector type.
- The aviation family: six committed extracts (nycflights13 flights,
  weather, carriers, and aircraft at a pinned commit, January through
  June 2013; OurAirports airports and runways at a pinned commit),
  each with its README, its digest-checked fetch script, and its
  bronze landing through the one file connector; `docs/sources.md`
  as the register of every extract; the reader options that keep
  code columns as text (F-50).
- Seven silver contracts and models hand-authored from the profiles
  they cite: six cleanup tables (no rows dropped, every clock and
  calendar column typed, the conformed keys declared with their K1
  rules) and two unified tables (`silver_flights`,
  `silver_airport_weather`) settling the joins in human-owned SQL,
  each join declared as structured `joins` with the completeness
  measured at the profile and the floor an error-severity rule
  enforces; their quality rules name the table through `ref()` so the
  sync-generated tests inherit the dependency edge (F-51).
- The engine fan-in: `engine.mapping_contracts` as a list, one
  `Emission` per mapping and a `StarEmission` over them, the shared
  groups and the registry as unions in category-name order, the
  star-global headers, engine 0.5.0; the conformed calendar (the
  timeframe payload `{grain, period_start}` for the whole star); the
  star objects rendered per category by `scripts/render_star_objects.py`
  and held to the render by a pattern gate.
- Gold star 1.5.0 and 1.6.0: `captured_at` required on the
  silver-derived objects, `conformedKeyRules` for `airport_iata`,
  `carrier_code`, and `tail_number`, the `flights` and
  `airport_weather` categories with their fifteen contracted objects,
  and `crossCategoryJoins` declaring the join the typed surfaces
  support (a flight's weather at its origin in its departure hour,
  measured 0.9994, floor 0.99, with a worked example).
- Three gates over the claims: the K1 conformed-key gate
  (`tests/test_conformed_keys.py`), the declared-join gate
  (`tests/test_declared_joins.py`, every silver and cross-category
  join re-measured through the paths their consumers take), and the
  aviation conservation and business-logic gate
  (`tests/test_aviation_conservation.py`: row conservation through
  every plane, the clock arithmetic, the local calendar against the
  UTC hour under DST, the null patterns the contracts explain, the
  vintage effect by name).
- The registry split (Amendment W): every entry carries `data` (the
  typed declarations, derived) and `expert_context` (what the
  contracts' authors wrote, carried unchanged and labeled authored:
  subject, how to read it, limitations, lineage, vintage, joins with
  measured completeness, cross-category joins, decisions, a meaning
  per field), compiled context v0010; `list_fact_categories` names
  each category's subject and its registry keys; the server
  instructions tell an agent to read the context first and to write
  string literals in lowercase.
- The demo question set: seven questions (three join the two categories
  on the typed surfaces, three lean on joins settled in silver, one is
  the retail control), with the SQL that answers each on the typed
  surfaces and the answers measured at the committed samples
  (`tests/fixtures/serving_questions.json`), proven through the serving
  path by `tests/test_serving_questions.py`; the demo guide's "What the
  agent knows" section and the questions to ask.
- The multi-source scale curve in `docs/scale.md`: cold builds of the
  three-category star at 166 thousand to 4 million flights, the
  cross-category latency on marts against views, the incremental path
  with three categories, and the artifact's size by category.
- The family selectors for the proposers: `make propose-silver
  SOURCE=<bronze table>` and `make propose-mapping TABLE=<silver
  table>` (with `TARGET=` and `ORACLE=`), the mapping agreement scorer,
  and eight eval fixtures for the family, each scored against its
  human-authored contract as an n=1 agreement study; the recorded
  render tests skip a fixture by name until its live run lands.
- The demo artifact as a release asset (`make demo-fetch`, the
  committed digest manifest, the CI gate holding the built warehouse
  to it); silver 1.3.0 for the retail table (`captured_at` required,
  F-46 and F-49).
- `docs/adding-a-source.md`: the path every source took, as a
  walkthrough validated by adding a source that is not in the demo
  (the World Bank GDP series) to a fresh clone of v1.1.0: eight files
  by hand, the rest generated and reviewed, a four-category star green
  at every gate; the fetch scripts' unpinned message names the value
  to copy. `docs/sources-explained.md`: what each demo source is, why
  it is here, every decision and every join with its justification,
  and how to read them for your own data. `docs/operating.md`: the
  operator's manual (the daily commands, the procedures, every gate
  and what its failure means, a glossary).

### Changed

- The README states the two source families and three categories, the
  multi-source proof as the second act of the signature test, the data
  and expert-context split at the serving edge, 22 of 31 models
  engine-emitted, and forty-one decisions; the demo guide walks the
  three-category star.
- The serving spec (section 2.1) and the agent-layer spec (sections 4
  and 5) carry Amendment W and the family selectors; the gold spec
  carries `crossCategoryJoins`.
- The compiled context advanced from v0006 to v0012 across the arc's
  contract changes (the star at 1.5.0 and 1.6.0, silver 1.3.0, the
  registry split, the regeneration); the golden fixtures and the
  emitted models follow every mint.

### Fixed

- The local pytest lane at v1.0.0 (F-47): the scan test, two query
  tests, and the server round trip, generalized to any category count.
- Contract prose corrected by measurement before it reached the
  registry: arrival delay and air time are null on 597 flights that
  departed with no arrival record, not only on cancellations; 12
  airport-hours (not 18) have no weather observation; about 84 percent
  of flights resolve an aircraft and about 12 percent of weather rows
  carry no pressure.

## [1.0.0] - 2026-09-02

The stable line begins. From this tag the pipeline, the engine, the
serving layer, the two proposers, and the gates change only through the
decision register; a clone of `main` at any tag gets a working demo.

### Added

- Issue forms for bugs, findings, and contract changes, with the blank
  issue path kept open and the security policy linked.
- The DCO check: a blocking workflow verifying a well-formed
  `Signed-off-by` trailer on every pull request commit, repository
  automation exempt by listed identity; `CONTRIBUTING.md` states the
  enforcement.
- The contracts provenance gate: `tests/test_contract_provenance.py`
  enforces rule 16 and engine spec section 9 on every committed contract,
  with negative fixtures proving each clause discriminates.
- `make doctor`, the keyless preflight for the five-minute path, and the
  walkthrough's pointer to it.
- The demo-artifact gate in CI: `scripts/check_demo_digest.py` proves the
  committed `demo/demo.duckdb` matches what the freshly built warehouse
  serves (object sets, row counts, the D-33 ordered content digest).
- A devcontainer, so a Codespace runs `make demo` keyless in a browser.

### Changed

- The two remaining pre-brand diagrams re-rendered to the published brand
  standard as light and dark pairs with Mermaid twins and 2x PNG exports:
  the agent proposal flow (the D-35 stances, the Amendment I provenance
  keys, the Amendment H amend input) and the gold unified event star flow
  (C1 to C5 at error severity, the typed mart beside the view, D-38 and
  D-39 stated, stale toolchain literals removed). Both specs embed the
  pairs at block level with click-through anchors.
- The README states what the system is: the scale section becomes Local
  by design (the specification ports, the data file is disposable, a
  second adapter is an experiment and not a promise) and points at
  `docs/scale.md`; the status paragraph carries v0.3.0 as the current
  release; the toolchain section states the supported platforms; two
  counts are corrected (five conservation tests, forty decisions); and
  the lead states the agents' credential posture and the approval record
  every contract carries.
- The mcp lock refreshed in range to 1.29.1 (the pin holds at
  `>=1.28,<2`).

### Fixed

- `make doctor` reports the uv that manages the checkout, not the venv's
  locked `uv` package (0.8.24 on every machine).

## [0.3.0] - 2026-09-01

Record 008 part two, the C5 gate, the incremental path, and the scale
posture, plus the documentation and community arc that landed between the
tags.

### Added

- Decision Record 008 part two: D-38 (incremental materialization behind
  `engine.materialization`, table by default, `on_schema_change: fail`,
  F-34), D-39 (batch-scoped gates under `mm_batch_floor` with the
  `make audit-gold` full-table target), and D-40 (`docs/scale.md` and the
  measurement rule), with Amendments O, P, and Q and findings F-34 and
  F-35.
- The C5 field-level reconciliation gate at error severity: gold star
  1.3.0 with mapping 1.1.1, then star 1.4.0 with silver 1.2.0 declaring
  `captured_at` optional-first (F-28); compiled contexts v0005 and v0006;
  engine 0.4.0 with the `is_incremental` blocks inert under table mode;
  the demo content digest held at every export (D-33).
- `docs/scale.md`: the measured curve on two stated environments (the
  sandbox and an Apple M3 Pro), the guidance, the gotcha, the recipes,
  and the honest remains.
- The README overview and runtime workflow diagram pairs at the larger
  type scale, embedded at block level with click-through anchors so the
  dark pair serves.

- Finding F-33: a working-tree guard must allow the tool's own state and
  a runner's action directory; the four false positives the Phase 8
  sitting measured, each pinned by a subprocess test.
- Community files: `CONTRIBUTING.md` with the Developer Certificate of
  Origin sign-off, `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1),
  `SECURITY.md`, and this changelog.
- Two published current-state diagrams with Mermaid twins under
  `docs/diagrams/`: the star ERD and the layer flow, each as a light and
  dark pair with measured counts and embedded subset fonts.
- The README's positioning sections: the governance loop leads, and a
  section states what the human owns, what the machine owns, and the three
  measured trade-offs of the gold layer with links to their findings; the
  name-and-logo note; the contributing pointers.

### Changed

- GitHub Actions pins moved off the Node 20 runtime before its removal
  from hosted runners: `actions/checkout@v7` and the `astral-sh/setup-uv`
  v10.0.1 release commit in both workflows; the required check names are
  unchanged.
- House style applied across the register, the findings, the specs, the
  verification narratives, the workflow step names, and the src and tests
  comments: no em dashes, short declarative sentences. Quoted tool output
  keeps its original punctuation.

### Fixed

- The silver model's header comment cites its contract at v1.1.1.
- `CLAUDE.md` names the project by what it is, carries the brand standards
  pointer, and carries no em dashes.

## [0.2.0] - 2026-08-29

### Added

- The two proposer agents: the silver cleanup proposer (stances cleanup,
  describe, amend) and the gold mapping proposer (stances propose, amend),
  each one structured API call against its proposal schema with a governed
  model policy (D-21 as amended, D-34, D-35). Drafts land in a gitignored
  outbox and reach `contracts/` only through a reviewed pull request.
- The adoption path for an existing hand-written model: the scan with its
  derived review queue, `verify-grain`, `enforce-properties`, and
  `docs/adoption.md` (D-35).
- The `propose-queue` batch driver with an explicit maximum and intent, and
  the golden-profile evaluation lane with a recorded run.
- The first agent-proposed contract amendment on `main`: the
  `silver_invoice_lines` quantity description, landed contract-first at
  v1.1.1 with the compiled-context refresh the freshness gate requires
  (D-08, D-30, F-29).
- The typed surface as a materialized mart beside the view, `engine.marts`
  configurable between table, view, and both, with the serving steer that
  names the typed surface to a client (D-36, Amendments K and L).
- Local enforcement hooks in the SDLC layer (D-37, F-32): the working-tree
  guard, a PreToolUse hook committed in `.claude/settings.json` that keeps
  Claude Code inside the repository, with its subprocess tests in CI; the
  `/contract-review` Skill; the read-only contract-reviewer subagent.
- The Claude Code GitHub Action workflow (`.github/workflows/claude.yml`):
  a maintainer's comment asks it to prepare a pull request for a backlog
  issue; a person opens, reviews, and merges it. Two such pull requests are
  on `main`.
- The repository index rows for the engine's machine-readable companions,
  the proposal schemas, and the evidence directory.
- The demo walkthrough's troubleshooting item for a python.org framework
  CPython on macOS (`CERTIFICATE_VERIFY_FAILED` while building the dbt
  1.12 parser).

### Changed

- The dbt line moved to 1.12: dbt-core 1.12.3 with dbt-duckdb 1.11.0, the
  full gate re-proof recorded, dbt Core v2 still deferred (Amendment N to
  D-05, F-30, F-31).
- The served text posture stated at the serving surface: every value read
  through the star, its projections, and the mart is canonical lowercased
  text (Amendment M to D-18).
- `agents.max_tokens` raised to 16384 for the proposers.
- The README's status paragraph and decision count, and no em dashes in
  the README or the demo walkthrough.

### Fixed

- The residual documentation index drift after Phase 6 (the agent layer
  row, three missing rows).

## [0.1.0] - 2026-08-14

### Added

- The serving spine, end to end on one machine: PyAirbyte ingestion into
  bronze from the committed Online Retail II sample (D-15, D-27); the
  deterministic profiler with versioned, hashed artifacts (D-11, D-23);
  contracted silver enforced at build time (D-06, D-28); the auto-modeling
  engine emitting the unified event star from an approved mapping contract
  under an ownership manifest (D-07, D-09, D-17 to D-19, D-29, D-30); the
  shared read-only query module and the five-tool MCP server (D-31 to
  D-33); the committed demo export `demo/demo.duckdb` (D-03 as amended).
- The three-gate contract CI (lint, build, sync and test) with the gate
  breaks captured as evidence (D-12, D-16, D-20, F-01 to F-25).
- The signature test: a new dimension added by mapping-contract amendment
  and regeneration alone, with conservation held to the digit.
- The decision register, the findings register, the layer specs, and the
  diagrams with their Mermaid twins.

[Unreleased]: https://github.com/metricminellc/metricmine/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/metricminellc/metricmine/compare/v1.1.3...v1.2.0
[1.1.3]: https://github.com/metricminellc/metricmine/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/metricminellc/metricmine/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/metricminellc/metricmine/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/metricminellc/metricmine/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/metricminellc/metricmine/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/metricminellc/metricmine/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/metricminellc/metricmine/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/metricminellc/metricmine/releases/tag/v0.1.0
