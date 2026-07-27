# Local entry points. CI covers the unit surface only; the end-to-end landing
# stays a local target per docs/spec/ingestion.md §4.

.PHONY: ingest
ingest:
	uv run python -m metricmine.ingest.land_sample
