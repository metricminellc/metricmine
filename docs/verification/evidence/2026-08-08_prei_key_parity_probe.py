"""Pre-I rehearsal, Objective 1: dbt-path key semantics (F-16 deferred half).

Proves the SQL path of canonical-key-v2 over REAL silver produces
line_identity values matching the Python reference (src/metricmine/keys.py)
on every one of the 44,721 grain tuples. Raw-SQL half here; the dbt-built
half is compared by probe_key_parity_dbt.py after the temp model builds.
"""

import sys

sys.path.insert(0, "/home/claude/metricmine/src")

import duckdb  # noqa: E402
import pandas as pd  # noqa: E402
from metricmine.keys import payload_key  # noqa: E402

WAREHOUSE = "/home/claude/metricmine/warehouse/metricmine.duckdb"

LINE_IDENTITY_SQL = """
sha256(lower(to_json(struct_pack(
    invoice_id := CAST(invoice_id AS VARCHAR),
    quantity   := CAST(quantity   AS VARCHAR),
    stock_code := CAST(stock_code AS VARCHAR),
    unit_price := CAST(unit_price AS VARCHAR)
))))
"""

con = duckdb.connect(WAREHOUSE, read_only=True)

rows = con.execute(
    "SELECT invoice_id, stock_code, quantity, unit_price"
    " FROM silver.silver_invoice_lines"
).fetchall()
print(f"silver grain tuples fetched: {len(rows)}")

py = [
    (
        inv,
        sc,
        q,
        up,
        payload_key(
            {
                "invoice_id": inv,
                "stock_code": sc,
                "quantity": q,
                "unit_price": up,
            }
        ),
    )
    for inv, sc, q, up in rows
]
py_df = pd.DataFrame(
    py, columns=["invoice_id", "stock_code", "quantity", "unit_price", "py_key"]
)
# Join on the canonical VARCHAR rendering of unit_price: registering raw
# Decimal objects lets duckdb infer a too-narrow DECIMAL(5,2) from a sample.
py_df["unit_price"] = py_df["unit_price"].map(str)
con.register("py_keys", py_df)

# Case-collision probe: lowercasing must not merge distinct grain tuples.
raw_distinct, low_distinct = con.execute(
    "SELECT COUNT(DISTINCT (invoice_id, stock_code, quantity, unit_price)),"
    "       COUNT(DISTINCT (lower(invoice_id), lower(stock_code), quantity, unit_price))"
    " FROM silver.silver_invoice_lines"
).fetchone()
print(f"distinct grain tuples raw={raw_distinct} lowercased={low_distinct}")

sql_vs_py = con.execute(
    f"""
    WITH sql_keys AS (
        SELECT invoice_id, stock_code, quantity, unit_price,
               {LINE_IDENTITY_SQL} AS sql_key
        FROM silver.silver_invoice_lines
    )
    SELECT
        COUNT(*)                                        AS joined,
        SUM(CASE WHEN s.sql_key = p.py_key THEN 1 ELSE 0 END) AS matched,
        SUM(CASE WHEN s.sql_key <> p.py_key THEN 1 ELSE 0 END) AS mismatched,
        COUNT(DISTINCT s.sql_key)                       AS distinct_sql_keys
    FROM sql_keys s
    JOIN py_keys p
      ON s.invoice_id = p.invoice_id
     AND s.stock_code = p.stock_code
     AND s.quantity   = p.quantity
     AND CAST(s.unit_price AS VARCHAR) = p.unit_price
    """
).fetchone()
joined, matched, mismatched, distinct_keys = sql_vs_py
print(
    f"raw-SQL vs Python: joined={joined} matched={matched}"
    f" mismatched={mismatched} distinct_sql_keys={distinct_keys}"
)

sample = con.execute(
    f"""
    SELECT invoice_id, stock_code, quantity, unit_price, {LINE_IDENTITY_SQL} AS k
    FROM silver.silver_invoice_lines ORDER BY invoice_id, stock_code LIMIT 2
    """
).fetchall()
for r in sample:
    print("sample:", r)

py_df.to_parquet("/home/claude/rehearsal/py_keys.parquet", index=False)

assert joined == len(rows) == 44721, "join coverage failure"
assert mismatched == 0, "PARITY FAILURE raw-SQL vs Python"
assert raw_distinct == low_distinct == distinct_keys == 44721, "collision"
print("OBJECTIVE 1 (raw-SQL half): PASS")
