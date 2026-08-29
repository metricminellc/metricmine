# MetricMine — Project Instructions for Claude Code

## What this is
A contract-driven medallion pipeline, built as a portfolio reference
implementation. It runs locally, end to end, on one machine with one command.
Bronze, silver, and gold live as three schemas in one local DuckDB file.
Agents propose data contracts; deterministic code and dbt execute them; a human
approves every contract.

## Hard rules (do not violate)
1. Pinned versions only: dbt-core 1.12.x (resolved 1.12.3; D-05 as amended
   by Amendment N, which also names the two dependencies the 1.12 line
   brings, dbt-core-experimental-parser at a lock-pinned pre-release and
   metricflow, neither a project dependency), dbt-duckdb 1.11.x (resolved
   1.11.0), datacontract-cli 1.0.12, airbyte (PyAirbyte) >=0.53,<0.54
   (resolved in uv.lock), duckdb==1.4.3 (explicit runtime dependency as of
   the profiler PR, matching PyAirbyte's pin), and the connector
   airbyte-source-file==0.3.15 with numpy<2 on uv-provisioned CPython 3.10
   (Makefile), the dbt package dbt_utils ==1.3.3 (transform/packages.yml
   with the committed transform/package-lock.yml), and mcp >=1.28,<2
   (resolved 1.29.0 in uv.lock; the serving dependency, D-32 as amended.
   mcp 2.x cannot resolve here: PyAirbyte requires fastmcp >=3.0, which
   caps mcp <2.0, finding F-22), and anthropic >=1.0,<1.1 (resolved
   1.0.0 in uv.lock; the proposer SDK, D-21 as amended by Amendment F;
   recorded fallback >=0.125,<1, exercised only on a documented live
   failure).
   Never upgrade to `latest`,
   and never upgrade any of these
   without an amendment to docs/decisions/decision-register.md in its own
   documentation PR.
2. dbt Core v2 is deliberately deferred. Do not upgrade to it. The 1.12
   `--use-v2-parser` flag is a parse-only probe here: the delegated build
   fails on every contract-enforced model (F-31), so never build, gate, or
   ship through it. The deferral lifts only by register amendment on a
   verified GA (D-05 as amended).
3. Profiling is standalone Python and carries no contract. Contracted transforms
   are SQL dbt models with `contract: enforced: true`.
4. Contracts are all-or-nothing: every column declares `name` and `data_type`.
5. Only `not_null` may be trusted as an enforced constraint. Uniqueness and
   referential integrity live in generated tests, never in trusted constraints.
6. Never weaken a contract to make a failing build pass. Contract changes and
   transform changes are separate pull requests, and a contract change requires
   a version bump.
7. `materialized_view` does not exist on dbt-duckdb. Use `table`, then
   `incremental`. Never design around materialized views.
8. Never edit a generated file whose ownership-manifest checksum has diverged
   from its baseline. Flag the drift instead.
9. The auto-modeling engine emits dbt model files; it does not execute DDL
   directly. Mapping contract in, gold model files out; dbt builds them.
   Mapping contracts live flat in contracts/ beside table contracts
   (physicalType: mapping is the discriminator). A mapping contract's
   category name must never equal a dbt model name: gate 3 fails loudly on
   the collision (F-12). Mapping contracts carry no quality rules — gate 3
   skips unmatched schema objects entirely (F-12), so such rules are dead
   letters; enforcement belongs to the gold star contract. Input schema
   and emission rules: docs/spec/engine.md.
10. Gate three runs as: `uv run datacontract dbt sync ...` then
    `uv run datacontract dbt test ...`. The `uv run` prefix is mandatory:
    the isolated tool cannot find dbt on PATH by itself. The TOP-LEVEL
    `datacontract test` command (no `dbt`) is a different, unsupported path
    against DuckDB (server type unsupported at 1.0.12) — never use it. The
    gate's `datacontract dbt test` subcommand is required and is not the
    same command.
11. dbt properties files are hand-authored. Treat `datacontract export
    dbt-models` output and sync-generated tests as proposals requiring
    review, never auto-merged. Known sync bug at 1.0.12: duplicateValues
    quality rules mistranslate into accepted_values tests (severity warn).
    Delete such tests on sight; keep uniqueness as a data_test.
    Scope (D-16 Amendment C): hand-authored governs the human-owned silver
    plane. Engine-owned gold models are the designed exception: the engine
    emits their properties files at the sync fixed point
    (docs/spec/engine.md §6), and they are reviewed as generated code in
    regeneration PRs under the ownership manifest. Every review obligation
    in this rule applies to them unchanged. At adoption (D-35), sync may
    CREATE the silver properties file from an approved contract (F-27) and
    `make enforce-properties` adds only contract.enforced and the not_null
    constraints the contract implies (D-16 Amendment J); the file stays
    human-owned and is reviewed in the model PR.
12. Gold is the unified event star per docs/spec/gold-unified-event-star.md:
    content-addressed values/columns dimensions, category-parameterized fact
    tables, context_registry, and a typed surface per category. Star tables
    and the registry materialize as `table` (contract enforcement requires
    it). The typed surface follows engine.marts (D-36): the materialized
    mart mart_<category>_typed (a table, lean, typed columns plus
    fact_hash_id, ordered by the time column) by default, with the
    projection view vw_<category>_typed kept beside it. Both are
    engine-emitted, uncontracted, and carry a derivative header. Never
    propose a typed surface the engine does not emit, a fourth schema, or a
    view materialization for any contracted gold object.

13. Hash keys use canonical_key v2 and nothing else. Payloads: parse, compact
    serialization with sorted keys, lowercase everything, SHA-256, hex.
    Scalars/manifests: text, lowercase, strip whitespace, KEEP hyphens;
    manifests are compact JSON arrays in declared order. Hashed payloads carry
    deterministic content only; audit stamps (loaded_at) stay outside
    payloads. Never put run timestamps or build ids inside a hashed payload.

14. Context binds by content address: schema_key rows in context_registry
    point to contract name + version and compiled context. Never embed
    contract text or context prose inside value payloads. The fact primary
    key is (fact, source, timeframe, dim) hashes; run_hash_id is a non-key
    attribute. Grain is declared in the mapping contract (aggregated with
    _row_count, or transaction with a degenerate id); never emit a fact model
    without a declared grain.

15. The two proposer agents are each ONE structured API call through the
    anthropic SDK at its pinned line (rule 1): model claude-sonnet-5 by
    default (a pinned snapshot ID; never latest), GA structured outputs
    (output_config.format json_schema) against the proposer's PROPOSAL
    schema under docs/spec/agent-layer/, never the frozen
    mapping-contract schema, which validates the rendered output instead
    (F-26), effort explicit (output_config.effort), max_tokens capped. The
    model may be swapped per run only to an allow-listed ID (D-34:
    claude-sonnet-5, claude-opus-5, claude-fable-5) via --model or
    MM_PROPOSER_MODEL; the model actually used is recorded in the proposal
    record and stamped as modelId in provenance; an unlisted ID fails
    closed before any call; adding a model is a register amendment. No
    tools, no MCP, no loops at proposer runtime. A proposer reads one
    profile artifact and writes ONLY to the gitignored proposals/ outbox,
    never to contracts/, transform/, or the warehouse. Validation
    failures retry at most twice, then fail closed with nothing written.
    A proposer runs in a governed stance (D-35: cleanup, describe, amend
    for silver; propose, amend for mapping); a stance is a mode, never a
    third agent. Its inputs are a fixed, configured list of governed,
    hashed artifacts (the profile; for amend, the committed contract and
    the operator's intent), never anything retrieved (D-23 Amendment H).
    The adoption scan (make scan) and the batch driver (make
    propose-queue) are deterministic code, never agents.

16. Agent prompts are versioned artifacts in src/metricmine/agents/prompts/
    with semver headers; change them only via pull request. Every proposed
    contract carries provenance customProperties (proposedBy,
    proposerVersion, promptVersion, modelId, profileHash, proposedAt,
    proposerStance; amendments also amendsContract as
    <id>@<version>#sha256:<hash>, D-22 Amendment I); hand-written
    contracts use the same keys with proposedBy: human and no stance.
    Never strip or fabricate provenance. Hand-written contracts not
    derived from a profile artifact (the pattern-derived gold star
    contract) carry profileHash ABSENT plus a provenanceNote stating why:
    absence-with-rationale is honest provenance, a fabricated hash never
    is (docs/spec/engine.md §9).

17. Agent drafts become contracts only through the human flow: review, copy
    into contracts/ on a branch, version bump, contract-only PR (rule 6
    holds). Never auto-merge a proposal, never write an agent draft
    directly into contracts/, and never let an agent weaken a contract to
    pass a gate. make demo must always run with no API key. An amendment
    never relaxes a contract without --allow-relaxation, a major bump,
    and the printed rule-6 warning (D-35); required additions enter
    optional and tighten after the model lands (F-28). On a fail-closed
    exit, report and stop; never re-invoke a proposer unattended (D-10
    Amendment G).

18. Serving is read-only, three layers deep, through one module. All gold
    access goes through src/metricmine/query.py; the MCP server is a thin
    adapter over it and never opens DuckDB itself. Serving connections
    open read_only=True, then set enable_external_access=false and
    lock_configuration=true before any client statement. The query tool
    accepts exactly one statement that parses as SELECT and leads with
    select/with/from: ATTACH, COPY, PRAGMA, SHOW, DESCRIBE, SUMMARIZE,
    EXPLAIN, SET, CALL, INSTALL, LOAD, EXPORT, all DDL, all DML, and
    multi-statement input all refuse, naming the failed check. Every
    query result is row-capped (default 100, hard cap 500) and carries an
    explicit truncated flag: a truncated result must announce itself. The
    served database resolves MM_SERVE_DB, then demo/demo.duckdb; a
    missing file fails closed at startup. list_fact_categories names the
    typed surface per category (typed_table, typed_columns, query_hint;
    D-31/D-32 as amended): analytical questions belong to that surface,
    and the star tables stay the provenance layer. Exactly five tools;
    never add a sixth without amending the register. Server code never prints to
    stdout (stdio carries JSON-RPC); diagnostics go to stderr. Spec:
    docs/spec/serving.md.

## Architecture boundaries
- Exactly two agents exist in the pipeline: a silver cleanup proposer and a
  gold mapping proposer. Both emit ODCS contracts. Neither writes
  code, touches data, or runs transformations. The count is of named
  proposers; stances are modes of those two (D-35), and the adoption
  scan, verify-grain, enforce-properties, and the batch driver are
  deterministic code, never agents (D-10 Amendment G).
- The auto-modeling engine (src/metricmine/engine/) is deterministic code,
  not an agent: approved contracts in, emitted gold dbt models out, per
  docs/spec/engine.md. It never runs at proposer runtime, never executes
  DDL, and never writes outside transform/models/gold/ plus its ownership
  manifest.
- The context compiler (src/metricmine/context/) is deterministic code,
  not an agent: approved contracts in, the committed compiled-context
  artifact out (context/compiled/vNNNN.json + meta sidecar, D-30). It
  writes nowhere else and never reads the warehouse; the engine carries
  its newest artifact into the emitted context_registry model as SQL
  VALUES literals, fail-closed if the artifact is missing or stale.
- All query, schema, and context-retrieval logic lives in one shared module
  (`src/metricmine/query.py`). The MCP server and the hosted app both import it.
  Neither reimplements it.
- The MCP server (`src/metricmine/server/`) is a thin stdio adapter over
  the shared module: exactly the five spec tools, each a delegation. It
  holds no SQL, no connection logic, and no fallback paths of its own.
- The demo exporter (`src/metricmine/export_demo.py`) writes exactly one
  artifact, `demo/demo.duckdb`, and nothing else. The working warehouse
  stays gitignored (D-03); export claims are content equality by query,
  never byte equality (D-33).
- Portability is delegated to dbt profiles. Do not build a parallel warehouse
  abstraction for the transform layer.

## Non-goals (never propose or build these)
Multi-tenancy, auth, billing, any UI beyond the optional read-only demo,
streaming, Redshift, orchestration platforms, autonomous multi-step agents,
more than one or two source types, petabyte or throughput claims, and
production SLAs.

## Toolchain
Python 3.12, uv for packaging, ruff for linting, pytest for tests. dbt Core with
the dbt-duckdb adapter for transforms. ODCS v3.1.0 for contracts, executed via
datacontract-cli 1.0.12, installed as an isolated tool with
`uv tool install --python 3.12 "datacontract-cli[duckdb]==1.0.12"` — never added to
pyproject.toml as a project dependency. GitHub Actions for CI.

The MCP server runs on the official mcp SDK over stdio, pinned to the 1.x
maintenance line (D-32 as amended; mcp 2.x cannot co-resolve with
PyAirbyte, F-22). The served database resolves MM_SERVE_DB, then
demo/demo.duckdb (F-25).

The proposer agents call the Anthropic Messages API through the official
anthropic SDK on the 1.0.x line (D-21 Amendment F) with ANTHROPIC_API_KEY
from the environment. make demo, the pytest lane, and CI never need a
key; the live lane is opt-in (make eval-agents).

Toolchain behavior was verified empirically before Phase 1 exit. Before
working on contracts, CI, or dbt models, read
`docs/verification/gate_proof_findings.md`. Before working on gold models,
the engine, or the context compiler, read
`docs/spec/gold-unified-event-star.md` and `docs/spec/engine.md`. Before
working on the profiler or
the read-only warehouse protocol, read `docs/spec/profiler.md`. Before
working on the serving layer — the query module, the MCP server, or the
demo export — read `docs/spec/serving.md`. Before
working on the agent layer —
the proposers, their prompts, or the proposal validator — read
`docs/spec/agent-layer.md`. Before adopting an existing model into the
contract gates, or working on the adoption scan and its helpers, read
`docs/adoption.md`. Decisions cited anywhere as D-0x resolve in
`docs/decisions/decision-register.md`.

## Conventions
- Small, reviewed pull requests with meaningful commit messages.
- Use plan mode for any multi-file change; show the plan before editing.
- Prefer editing existing files over creating new ones.
- Never read or write paths outside the repository working tree.
  External inputs are staged into the repo by Justin before a session
  needs them. The working-tree guard enforces this rule (D-37): a
  PreToolUse hook in .claude/settings.json runs
  .claude/hooks/working_tree_guard.py before every Bash, Read, Edit,
  Write, NotebookEdit, Glob, and Grep call and denies any path that
  resolves outside the project root, naming the path. The guard reads
  command text, never a subprocess, so this rule stays in force where
  the guard cannot see. Hooks are local to Claude Code; CI is the gate
  of record and no check migrates out of it.

### Commit and PR conventions
Every commit and PR follows these:

- **Commit subject:** a Conventional Commits prefix, then a concise summary.
  Allowed prefixes: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`,
  `build`. Example:
  `docs: pin datacontract-cli 1.0.12 and add isolated-tool guardrail`.
- **Commit body:** explain WHY the change was made, not just what changed. The
  diff already shows what. State the reasoning, the decision it implements
  (cite the D-0x number when one applies; every D-0x resolves in
  docs/decisions/decision-register.md), or the problem it solves.
- **PR description:** three sections, in this order:
  - **Summary** — one or two sentences on the intent.
  - **What changed** — the concrete edits, as a short list.
  - **Why** — the reasoning or the decision/phase this advances.
- Keep it honest and specific. Do not pad. A one-line chore does not need a
  three-paragraph body; match the depth to the change.
