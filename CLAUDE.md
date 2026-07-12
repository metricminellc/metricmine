# MetricMine — Project Instructions for Claude Code

## What this is
A contract-driven medallion pipeline, built as a portfolio reference
implementation. It runs locally, end to end, on one machine with one command.
Bronze, silver, and gold live as three schemas in one local DuckDB file.
Agents propose data contracts; deterministic code and dbt execute them; a human
approves every contract.

## Hard rules (do not violate)
1. Pinned versions only: dbt-core 1.11.x (resolved 1.11.12), dbt-duckdb 1.10.x
   (resolved 1.10.1), datacontract-cli 1.0.12. Never upgrade to `latest`, and
   never upgrade any of these without a Decision Record amendment.
2. dbt Core v2 and dbt Core 1.12 are deliberately deferred. Do not upgrade to
   them.
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

## Architecture boundaries
- Exactly two agents exist in the pipeline: a silver cleanup proposer and a
  fact-and-dimension mapping proposer. Both emit ODCS contracts. Neither writes
  code, touches data, or runs transformations.
- All query, schema, and context-retrieval logic lives in one shared module
  (`src/metricmine/query.py`). The MCP server and the hosted app both import it.
  Neither reimplements it.
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
`uv tool install --python 3.12 "datacontract-cli[duckdb]"` — never added to
pyproject.toml as a project dependency. GitHub Actions for CI.

Toolchain behavior was verified empirically before Phase 1 exit. Before
working on contracts, CI, or dbt models, read
`docs/verification/gate_proof_findings.md`.

## Conventions
- Small, reviewed pull requests with meaningful commit messages.
- Use plan mode for any multi-file change; show the plan before editing.
- Prefer editing existing files over creating new ones.

### Commit and PR conventions
Every commit and PR follows these:

- **Commit subject:** a Conventional Commits prefix, then a concise summary.
  Allowed prefixes: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`,
  `build`. Example:
  `docs: pin datacontract-cli 1.0.12 and add isolated-tool guardrail`.
- **Commit body:** explain WHY the change was made, not just what changed. The
  diff already shows what. State the reasoning, the decision it implements (cite
  the D-0x number when one applies), or the problem it solves.
- **PR description:** three sections, in this order:
  - **Summary** — one or two sentences on the intent.
  - **What changed** — the concrete edits, as a short list.
  - **Why** — the reasoning or the decision/phase this advances.
- Keep it honest and specific. Do not pad. A one-line chore does not need a
  three-paragraph body; match the depth to the change.
