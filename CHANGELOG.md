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

### Changed

- The README names v1.0.0 as the current release and the start of the
  stable line; CLAUDE.md states the stability rule as hard rule 19.

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

[Unreleased]: https://github.com/metricminellc/metricmine/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/metricminellc/metricmine/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/metricminellc/metricmine/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/metricminellc/metricmine/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/metricminellc/metricmine/releases/tag/v0.1.0
