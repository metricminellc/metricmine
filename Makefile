# Local entry points. Since the bronze-in-CI change (D-27), CI also runs
# `make ingest` (offline mode) so the gates build silver from real bronze;
# pytest still covers only the unit surface (docs/spec/ingestion.md §4).

# PyPI's airbyte-source-file (0.3.15) pins pandas==1.4.3, which only has
# wheels up to Python 3.10 — so the connector venv is pre-provisioned there.
# PyAirbyte's ensure_installation() sees the executable and skips its own
# installer.
CONNECTOR_VENV := .venv-source-file
CONNECTOR_PYTHON := 3.10

$(CONNECTOR_VENV)/bin/source-file:
	uv venv --python $(CONNECTOR_PYTHON) $(CONNECTOR_VENV)
# pandas 1.4.3 wheels are built against the numpy 1.x ABI; cap numpy<2.
	uv pip install --python $(CONNECTOR_VENV)/bin/python "airbyte-source-file==0.3.15" "numpy<2"

.PHONY: ingest
ingest: $(CONNECTOR_VENV)/bin/source-file
	uv run python -m metricmine.ingest.land_sample

.PHONY: profile
profile:
	uv run python -m metricmine.profiling.run

.PHONY: regen
regen:
	uv run python -m metricmine.engine.emit

.PHONY: context
context:
	uv run python -m metricmine.context.compile

.PHONY: export-demo
export-demo:
	uv run python -m metricmine.export_demo

# Proposer agents per docs/spec/agent-layer.md §4 (D-24, D-34, D-35): one
# structured call per target, writing a draft contract plus its record to
# the gitignored proposals/ outbox; merge is approval. ANTHROPIC_API_KEY
# must be present in the shell that runs these targets; nothing here reads
# or prints it. The model swaps within the D-34 allow-list either through
# MM_PROPOSER_MODEL or per run: `make propose-silver MODEL=claude-opus-5`.
MODEL ?=
MODEL_FLAG := $(if $(MODEL),--model $(MODEL),)

.PHONY: propose-silver
propose-silver:
	uv run python -m metricmine.agents propose silver $(MODEL_FLAG)

.PHONY: propose-mapping
propose-mapping:
	uv run python -m metricmine.agents propose mapping $(MODEL_FLAG)

# The keyless replay (D-24; docs/demo.md path B in one command): land the
# committed sample into bronze, build the contracted models, export the
# demo artifact. No API key, no account, no network beyond the package hub.
.PHONY: demo
demo: ingest
	uv run dbt deps --project-dir transform --profiles-dir transform
	uv run dbt build --project-dir transform --profiles-dir transform --target local
	$(MAKE) export-demo

# The live regenerate path chains the two proposers in pipeline order
# (D-24). Drafts land in the outbox; nothing under contracts/ moves.
.PHONY: regenerate
regenerate: propose-silver propose-mapping

# The describe stance (D-35): adopt an EXISTING silver table by drafting the
# contract that would enforce it from its own profile artifact. Refuses when
# contracts/<TABLE>.odcs.yaml already exists; ORACLE=path bypasses the
# refusal for the recorded n=1 agreement study (D-25). Needs the key.
ORACLE ?=
ORACLE_FLAG := $(if $(ORACLE),--oracle $(ORACLE),)

.PHONY: propose-describe
propose-describe:
	uv run python -m metricmine.agents propose describe --table "$(TABLE)" $(MODEL_FLAG) $(ORACLE_FLAG)

# The amend stance (D-35): evolve a COMMITTED contract by a declared change
# set applied as a patch; the diff is the declared set by construction.
# Requires TABLE and a non-empty INTENT (recorded verbatim, D-22 Amendment I).
# A narrowing change set is refused unless ALLOW_RELAXATION=1 is passed; it
# then renders at a major bump with the printed rule-6 warning. Needs the key.
ALLOW_RELAXATION ?=
RELAX_FLAG := $(if $(ALLOW_RELAXATION),--allow-relaxation,)

.PHONY: propose-amend
propose-amend:
	uv run python -m metricmine.agents propose amend --table "$(TABLE)" --intent "$(INTENT)" $(MODEL_FLAG) $(RELAX_FLAG)

# Deterministic adoption tools (D-35): never agents, keyless by construction.
# The scan derives the review queue from the tree and the read-only warehouse
# on every run and writes it to the gitignored outbox; nothing is stored.
.PHONY: scan
scan:
	uv run python -m metricmine.adoption scan

.PHONY: verify-grain
verify-grain:
	uv run python -m metricmine.adoption verify-grain --table "$(TABLE)" --keys "$(KEYS)"

.PHONY: enforce-properties
enforce-properties:
	uv run python -m metricmine.adoption enforce-properties --table "$(TABLE)"

# The live eval lane over the golden-profile set (D-25): first-attempt lint
# and groundedness pass rates with token and cost actuals; honors the D-34
# override the same way. Needs the key; never runs in CI.
.PHONY: eval-agents
eval-agents:
	uv run python -m metricmine.agents eval $(MODEL_FLAG)
