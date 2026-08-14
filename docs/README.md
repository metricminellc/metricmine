# docs/

> Repo path: `docs/README.md`
> Map of the repository's documentation. Everything cited by a commit body,
> a spec, or CLAUDE.md resolves somewhere under this directory.

| Path | What it is |
|---|---|
| [`demo.md`](demo.md) | The ten-minute demo walkthrough: serve the committed `demo/demo.duckdb` keyless, wire Claude Desktop, then the full replay from raw data to a fresh export, with troubleshooting. |
| [`decisions/decision-register.md`](decisions/decision-register.md) | The authoritative index of project decisions, their status, and the CLAUDE.md rule crosswalk. Every `D-0x` citation in the repo resolves here. |
| [`spec/`](spec/) | Component specifications, the living source of truth for each component. Spec PRs merge before their implementation PRs open. |
| [`spec/ingestion.md`](spec/ingestion.md) | Phase 2 ingestion: PyAirbyte lands the committed Online Retail II sample through the `source-file` connector into bronze; `source-faker` stays the keyless synthetic path. Verified connector config, bronze conventions, PyAirbyte runtime, and Phase 2 exit criteria (D-15, D-04, D-03). |
| [`spec/profiler.md`](spec/profiler.md) | Phase 3 profiler: deterministic bronze profiling into a committed, versioned JSON artifact — authority boundary (observable facts vs human judgment), canonical serialization and determinism rules, token-budget caps, artifact versioning, and the read-only warehouse protocol (D-11, D-23, D-04, D-03, D-25). |
| [`spec/gold-unified-event-star.md`](spec/gold-unified-event-star.md) | Gold layer source of truth: the unified event star (D-17, D-18, D-19). |
| [`spec/engine.md`](spec/engine.md) | Phase 4 auto-modeling engine: first-class mapping-contract elements and their frozen JSON Schema, canonical_key v2 dual implementation with golden vectors, deterministic emission at the sync fixed point under the ownership manifest, and conservation severity routing (D-29, D-30, D-07, D-09, D-18). |
| [`spec/serving.md`](spec/serving.md) | Phase 5 serving: the shared query module (`src/metricmine/query.py`), the five-tool MCP server, and the `make export-demo` artifact — the three-layer read-only posture, the statement gate, row caps with truncation flags, database resolution, and the content-equality-by-query export claim (D-31, D-32, D-33, over D-03, D-11, D-17, D-24). |
| [`spec/agent-layer.md`](spec/agent-layer.md) | The two proposer agents: invocation (one structured API call, pinned model, structured outputs), prompt governance and provenance, grounding without retrieval, the propose/review/approve CLI flow, and the golden-profile evaluation set (D-21 to D-25). Implements in Phase 6. |
| [`spec/current-state/data-capture-baseline.md`](spec/current-state/data-capture-baseline.md) | Abridged clean-room baseline of the 2023 capture pipeline. Historical record and provenance artifact; its acquisition machinery is not a rebuild target. |
| [`verification/gate_proof_findings.md`](verification/gate_proof_findings.md) | Empirical findings (canonical IDs `F-nn`) from the scratch gate proof and every verification rung since: toolchain behavior observed live, never inferred. Read before working on contracts, CI, or dbt models. |
| [`verification/duckdb_constraint_matrix.md`](verification/duckdb_constraint_matrix.md) | The full Session A evidence behind [F-06](verification/gate_proof_findings.md#f-06): which declared constraints enforce at the pinned DuckDB engine, which record only, and how each was measured. |
| [`verification/signature-test.md`](verification/signature-test.md) | Phase 4 exit evidence: the signature property (D-17) demonstrated end to end — a new dimension added by mapping-contract amendment and regeneration alone, with the staleness-guard and ownership-drift refusals captured live. |
| [`diagrams/runtime_workflow_diagram.svg`](diagrams/runtime_workflow_diagram.svg) (+ [`.mmd`](diagrams/runtime_workflow_diagram.mmd)) | End-to-end runtime workflow: the `make demo` path from sources through bronze, silver, the engine, and the unified event star to MCP serving. |
| [`diagrams/agent_proposal_flow.svg`](diagrams/agent_proposal_flow.svg) (+ [`.mmd`](diagrams/agent_proposal_flow.mmd)) | The proposer runtime: propose, validate, approve. Zoom-in companion to the runtime workflow diagram, which is unchanged. |
| [`diagrams/gold_unified_event_star_flow.svg`](diagrams/gold_unified_event_star_flow.svg) (+ [`.mmd`](diagrams/gold_unified_event_star_flow.mmd)) | Gold layer target-state flow: modeling plane, star objects, serving posture. Companion to the gold spec. |
| [`assets/`](assets/) | Brand and README assets: the MetricMine logo pair (served per color scheme by the README's picture element) and the dark-canvas workflow overview graphic (rendered PNG plus hand-authored SVG source). |

Every SVG under `diagrams/` has a machine-readable Mermaid (`.mmd`) twin.

Conventions: specs are written in engineering voice, self-contained, and cite
decisions by `D-0x` anchor into the register. Extended working history lives
in project records outside the repository; no document here depends on them.
