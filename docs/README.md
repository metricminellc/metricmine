# docs/

> Repo path: `docs/README.md`
> Map of the repository's documentation. Everything cited by a commit body,
> a spec, or CLAUDE.md resolves somewhere under this directory.

| Path | What it is |
|---|---|
| [`decisions/decision-register.md`](decisions/decision-register.md) | The authoritative index of project decisions (D-01 to D-19), their status, and the CLAUDE.md rule crosswalk. Every `D-0x` citation in the repo resolves here. |
| [`spec/`](spec/) | Component specifications, the living source of truth for each component. Spec PRs merge before their implementation PRs open. |
| [`spec/gold-unified-event-star.md`](spec/gold-unified-event-star.md) | Gold layer source of truth: the unified event star (D-17, D-18, D-19). |
| [`spec/current-state/data-capture-baseline.md`](spec/current-state/data-capture-baseline.md) | Abridged clean-room baseline of the 2023 capture pipeline. Historical record and provenance artifact; its acquisition machinery is not a rebuild target. |
| [`verification/gate_proof_findings.md`](verification/gate_proof_findings.md) | Empirical findings ([F-01](verification/gate_proof_findings.md#f-01) to [F-07](verification/gate_proof_findings.md#f-07)) from the pre-Phase-1 scratch gate proof of the pinned toolchain. Read before working on contracts, CI, or dbt models. |
| [`diagrams/runtime_workflow_diagram.svg`](diagrams/runtime_workflow_diagram.svg) (+ [`.mmd`](diagrams/runtime_workflow_diagram.mmd)) | End-to-end runtime workflow: the `make demo` path from sources through bronze, silver, the engine, and the unified event star to MCP serving. |
| [`diagrams/gold_unified_event_star_flow.svg`](diagrams/gold_unified_event_star_flow.svg) (+ [`.mmd`](diagrams/gold_unified_event_star_flow.mmd)) | Gold layer target-state flow: modeling plane, star objects, serving posture. Companion to the gold spec. |

Every SVG under `diagrams/` has a machine-readable Mermaid (`.mmd`) twin.

Planned additions (each lands with its component's spec PR):
`spec/ingestion.md`, `spec/profiler.md`, `verification/duckdb_constraint_matrix.md`.

Conventions: specs are written in engineering voice, self-contained, and cite
decisions by `D-0x` anchor into the register. Extended working history lives
in project records outside the repository; no document here depends on them.
