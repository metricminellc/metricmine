"""The auto-modeling engine (docs/spec/engine.md; D-29).

Deterministic code, not an agent: approved contracts in, emitted gold dbt
models out. It never executes DDL, never reads the warehouse, and never
writes outside transform/models/gold/ plus its ownership manifest (D-07,
D-09).
"""

ENGINE_VERSION = "0.4.0"
