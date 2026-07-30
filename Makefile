# Local entry points. CI covers the unit surface only; the end-to-end landing
# stays a local target per docs/spec/ingestion.md §4.

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
