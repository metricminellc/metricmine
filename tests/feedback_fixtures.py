"""A tiny gold-only warehouse for the feedback module's tests, built in
tmp_path so no test needs the built star or the release asset. It has
the shape the serving module reads: a fact table, a typed mart with
ninety negative unflagged rows, and a registry whose entries carry the
category, the role, the subject, the governing contracts, and a meaning
per field. Keyless and offline.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

MEANING_OLD = "Units on the line; negative only on cancellations."
MEANING_NEW = (
    "Units on the line; negative on cancellation lines and on zero-unit-price stock-adjustment lines,"
    " so a negative quantity alone does not mean a cancellation."
)


def build_gold(path: Path, mapping_version: str = "1.1.2", meaning: str = MEANING_NEW, negatives: int = 90) -> Path:
    con = duckdb.connect(str(path))
    con.execute("create schema gold")
    con.execute("create table gold.fact_invoice_lines_values(fact_hash_id varchar)")
    con.execute("insert into gold.fact_invoice_lines_values select 'h' || i from range(200) t(i)")
    con.execute(
        "create table gold.mart_invoice_lines_typed as select 'inv' || i as invoice_id, 'sc' as stock_code,"
        f" case when i < {negatives} then -1 when i < {negatives + 10} then -2 else 3 end as quantity,"
        f" case when i < {negatives} then 0.0 else 1.5 end as unit_price,"
        f" (i >= {negatives} and i < {negatives + 10}) as is_cancellation from range(200) t(i)"
    )
    con.execute("create schema silver")
    con.execute("create table silver.silver_invoice_lines(x integer)")
    gc = {
        "mapping": f"gold_invoice_lines_mapping v{mapping_version}",
        "silver": "silver_invoice_lines v1.3.0",
        "star": "gold_unified_event_star v1.6.0",
    }
    measures = {
        "category": "invoice_lines",
        "role": "measures",
        "manifest": ["quantity", "unit_price"],
        "data": {},
        "expert_context": {
            "subject": "retail lines",
            "governing_contracts": gc,
            "fields": {"quantity": {"meaning": meaning}, "unit_price": {"meaning": "price"}},
        },
    }
    dims = {
        "category": "invoice_lines",
        "role": "dimensions",
        "manifest": ["invoice_id"],
        "data": {},
        "expert_context": {"subject": "retail lines", "governing_contracts": gc, "fields": {"invoice_id": {"meaning": "id"}}},
    }
    con.execute(
        "create table gold.context_registry(schema_key varchar, entity_group varchar, contract_name varchar,"
        " contract_version varchar, compiled_context varchar, loaded_at timestamp)"
    )
    con.execute(
        "insert into gold.context_registry values (?, ?, ?, ?, ?, now())",
        ["k-measures", "invoice_lines", "gold_invoice_lines_mapping", mapping_version, json.dumps(measures)],
    )
    con.execute(
        "insert into gold.context_registry values (?, ?, ?, ?, ?, now())",
        ["k-dims", "invoice_lines", "gold_invoice_lines_mapping", mapping_version, json.dumps(dims)],
    )
    con.close()
    return path
