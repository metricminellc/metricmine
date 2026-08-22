# The Agent Layer: Propose, Validate, Approve

**Status:** adopted design, July 12, 2026. Implements in Phase 6.
**Decisions:** D-21 through D-25, condensed in [the decision register](../decisions/decision-register.md).
**Diagram:** [`docs/diagrams/agent_proposal_flow.mmd`](../diagrams/agent_proposal_flow.mmd).
**Source document:** Agent Layer Design 001 (July 12, 2026), of which this file is the in-repo transcription.

The pipeline has exactly two agents (D-10): the **silver cleanup proposer** (bronze profile in, ODCS cleanup contract out) and the **gold mapping proposer** (silver profile in, ODCS mapping contract out). Neither touches data, writes code, nor runs transformations. Agents propose, code executes, a human approves. This document fixes how the two proposers are built, governed, and used.

## 1. Invocation architecture (D-21)

Each proposer is **one structured call** to the Anthropic Messages API through the official Python SDK (`anthropic>=1.0,<1.1`, resolved 1.0.0, a normal locked dependency from the Phase 6 harness PR onward; upgrades are deliberate, by pull request; D-21 Amendment F).

- **Model:** `claude-sonnet-5` by default. Model IDs of this generation are fixed snapshots, so the string is the pin. Never `latest`. An operator may swap the model for a run to an allow-listed ID (`claude-sonnet-5`, `claude-opus-5`, `claude-fable-5`) via `--model` or `MM_PROPOSER_MODEL`, in that precedence; an unlisted ID fails closed before any call; the model used is recorded and stamped in provenance (D-34).
- **Structured outputs:** the request sets `output_config.format` to the proposer's **proposal schema**, a structured-outputs-compatible projection of the contract shape kept at `docs/spec/agent-layer/gold-mapping-proposal.schema.json` and `docs/spec/agent-layer/silver-cleanup-proposal.schema.json` (flat; every property required; every enum typed; variants flattened into a discriminator plus sibling arrays the validator holds consistent). Constrained decoding guarantees the response parses against it. The model cannot emit prose or a malformed proposal. The frozen mapping-contract schema is never sent to the API; it validates the rendered contract instead ([F-26](../verification/gate_proof_findings.md#f-26)). Each schema file is paired with an example proposal beside it.
- **Parameters:** effort set explicitly, `max_tokens` capped, all request parameters recorded per run.
- **Serialization boundary:** the model emits a structured proposal; deterministic glue renders canonical ODCS YAML with stable key order. Judgment proposes; code serializes.
- **Failure containment:** post-parse validation failures retry at most twice with errors fed back, then **fail closed**: exit nonzero, nothing written, raw response preserved for inspection. Writes are atomic (temp file, rename). Loops are impossible by construction.
- **Least privilege:** the call carries no tools and no MCP connection. A proposer reads one profile artifact and writes only to the outbox. `ANTHROPIC_API_KEY` comes from the environment, never the repo. `make demo` requires no key.

The mid-pipeline agents do not use MCP. The MCP server exists at the serving layer (Phase 5) and is out of scope here.

## 2. Prompt governance and lineage (D-22)

- Prompts live at `src/metricmine/agents/prompts/`, one file per proposer, sharing a documented template anatomy, each with a **semver-and-changelog header** read at runtime.
- Prompt changes travel **only by pull request** under the standing commit conventions (D-14) and roll back by revert. Git is the prompt platform.
- Every proposed contract stamps provenance into ODCS `customProperties`: `proposedBy`, `proposerVersion`, `promptVersion`, `modelId`, `profileHash`, `proposedAt`. Hand-written contracts carry the same keys with `proposedBy: human` from the first Phase 3 contract onward, so the schema is uniform.
- The full request record (parameters, token counts, cost, response ID, validation outcomes, disposition) is a JSON sidecar in the gitignored outbox.
- **Injection posture:** profile sample values are untrusted because they derive from source data. Defense is layered: the prompt delimits the payload as data; structured outputs leave no free-text channel; the validator and `datacontract lint` gate the shape; a human reviews every contract; and the contract is declarative YAML never executed as code. The residual risk is a subtly wrong proposal, which the approval gate exists to catch.
- Exact prompt text is authored in Phase 6, after the spine has proven the contract shapes.

## 3. Grounding without retrieval (D-23)

The proposers use **no RAG**: no vector store, no embeddings, no similarity search. The versioned profile artifact is the sole context, injected complete into the call. Deterministic full-context injection is a stronger guarantee than retrieval at this scale, and that is the claim made.

**The profiler owes the agents** (discharged by [the profiler spec](profiler.md)):

- deterministic serialization with stable ordering,
- a `schema_version` field,
- a content hash over the canonical serialization,
- token-budget caps on sample values, distinct-value lists, and string lengths (versioned profiler constants),
- per-column name, inferred type, null rate, cardinality, samples; per-table row count and duplicate-row rate (grain evidence for the mapping proposer).

**The deterministic validator** gates every proposal before anything is written:

1. **Groundedness:** every column the proposal references must exist in the profile. The hallucinated-column rate is enforced to zero, not measured.
2. **Staleness:** the proposal is bound to the profile hash it consumed; if the profile has been regenerated since, validation fails.
3. **Completeness:** mapping proposals declare grain per category (aggregated or transaction); cleanup proposals must be lint-clean.
4. **Lint:** `datacontract lint` runs as the final step, the same check CI runs, so first-attempt lint pass is observable at propose time.

## 4. UX: the propose, review, approve flow (D-24)

The interaction surface is the CLI, the editor, and the pull request. Nothing else.

```
make propose-silver     # bronze profile -> draft cleanup contract
make propose-mapping    # silver profile -> draft mapping contract
```

1. **Propose.** The target selects the latest profile (or `--profile PATH`), runs the call, validates, and writes the draft contract plus its proposal record to `proposals/`, a **gitignored outbox**. Nothing under `contracts/` is touched. The terminal prints a rationale summary citing profile evidence, and a unified diff against the current committed contract on regeneration.
2. **Review.** Open the draft in the editor and edit freely; the draft is the reviewer's to change. Business context added during review lands in the contract fields the context compiler already harvests (D-19).
3. **Approve.** Copy the reviewed contract into `contracts/` on a branch with the version bump D-08 requires, and open the contract-only pull request. The three gates run. **Merge is approval.** Rejected drafts never leave the outbox.

`make demo` replays committed contracts and models, keyless and deterministic, unchanged. A regenerate path chains the propose targets live. Determinism belongs to replay; the human gate contains live variance.

## 5. Evaluation: the golden-profile set (D-25)

- **Fixtures:** two or three committed profile artifacts under `tests/agents/` (Online Retail II per D-15, the faker path, optionally one pathological case).
- **Offline, every CI run, keyless:** the render path is tested against recorded proposals and the validator against constructed inputs, in the existing pytest lane.
- **Live, manual:** `make eval-agents` runs both proposers against the fixtures when a key is present and reports **first-attempt lint pass rate** and **first-attempt groundedness pass rate**, with token and cost actuals. It honors the D-34 model override, so a model comparison is one command; comparing is enabled, not performed.
- **Deferred by intent:** LLM-as-judge scoring, automated A/B optimization, drift dashboards.

Phase 6 exits with fixtures committed, offline assertions green, and one recorded live run.

## 6. Cost posture

A bounding case (profile near the 30k-input-token cap, contract near 5k output tokens) prices under roughly twenty cents at standard rates; typical profiles run far smaller, so a routine regeneration stays under a dime. Token caps bound the worst case; tokens and computed cost land in every proposal record. Enforced budget infrastructure is deliberately not built at this scale.

## 7. What this layer never does

No third runtime agent; the generate-and-verify authoring loop stays in the SDLC layer as Claude Code pull requests (D-10). No autonomous multi-step agents (a standing non-goal, now backed structurally: one call, no loop, no tools). No MCP at proposer runtime. No writes to `contracts/`, `transform/`, or the warehouse. No API key in the replay path.

## Appendix A: Proposal record fields

`agent` (name, version) · `prompt_version` · `prompt_path` · `model_id` · `model_source` (`default` | `env` | `flag`) · `rates` (input_per_mtok, output_per_mtok) · `sdk_version` · `request_params` (effort, max_tokens) · `profile_path` · `profile_hash` · `profile_schema_version` · `created_at` · `response_id` · `stop_reason` · `usage` (input_tokens, output_tokens, summed over attempts) · `cost_usd_estimate` · `validation` (schema_pass, groundedness_pass, completeness_pass, staleness_pass, lint_pass, attempts, errors) · `disposition` (`draft_written` | `failed_closed`) · `draft_path`

## Appendix B: Contract provenance keys (ODCS customProperties)

`proposedBy` (`human` | `silver-cleanup-proposer` | `gold-mapping-proposer`) · `proposerVersion` (absent for human: it versions the proposer harness, which does not exist for a human author) · `promptVersion` (absent for human) · `modelId` (absent for human) · `profileHash` (absent, with a
`provenanceNote` stating why, for hand-written contracts not derived from
a profile artifact — the pattern-derived gold star contract; never
fabricated) · `proposedAt`

## Appendix C: Layout delta (lands in Phase 6)

```
src/metricmine/agents/
├── __main__.py         # CLI: propose silver | propose mapping; --profile, --model
├── harness.py          # shared call: structured outputs, retry budget, record writing
├── models.py           # D-34: default model, allow-list with rate rows, resolver
├── validate.py         # groundedness, completeness, staleness, lint
├── render.py           # proposal JSON -> canonical ODCS YAML
├── silver_proposer.py  # thin: schema + prompt binding
├── mapping_proposer.py # thin: schema + prompt binding
└── prompts/            # versioned prompt artifacts (semver front matter)
    ├── README.md       # template anatomy, versioning rules
    ├── silver_cleanup.md
    └── gold_mapping.md
docs/spec/agent-layer/  # proposal schemas (the API-facing projection) + examples
proposals/              # gitignored outbox: drafts + records
tests/agents/           # golden fixtures + offline assertions
```
