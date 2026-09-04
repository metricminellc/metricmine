"""The declared-join gate: every join a contract claims, measured (D-41 M2).

Two kinds of claim carry a measured completeness into the registry's
expert context (Amendment W), and an agent will read the number as fact:

- A unified silver contract's structured ``joins`` custom property: each
  join the human-owned SQL settled, with the completeness measured at
  the profile the contract cites and the floor its quality rule enforces.
- The star contract's ``crossCategoryJoins``: each join the typed
  surfaces support across categories, on conformed keys and the conformed
  calendar, with its measured completeness and floor.

This test holds the claims to the warehouse through the paths their
consumers take (the probe rule): the silver joins by their definition
(the fraction of rows whose left column resolves in the right table), the
cross-category joins through the typed surfaces the query hint sends an
agent to, and the same join in silver, so gold is shown to preserve the
joinability silver settled. A declared number that drifts from the
measurement fails here by name; the floor is the contract's own gate.

Local lane: needs the built warehouse (make demo, or the dbt build the
runbook lands). Deselected in CI with the rest of the marker.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
CONTRACTS = REPO / "contracts"
STAR = CONTRACTS / "gold_unified_event_star.odcs.yaml"
WAREHOUSE = REPO / "warehouse" / "metricmine.duckdb"
TOLERANCE = 0.0005  # the declarations are rounded to four places

pytestmark = pytest.mark.local


def _custom(doc: dict) -> dict:
    return {p["property"]: p["value"] for p in doc.get("customProperties") or []}


def _silver_joins() -> list[tuple[str, dict]]:
    out = []
    for path in sorted(CONTRACTS.glob("silver_*.odcs.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        joins = _custom(doc).get("joins")
        if isinstance(joins, list):
            out.extend((doc["id"], join) for join in joins)
    return out


def _cross_joins() -> list[dict]:
    doc = yaml.safe_load(STAR.read_text(encoding="utf-8"))
    return list(_custom(doc).get("crossCategoryJoins") or [])


def _mapping_source(category: str) -> str:
    for path in sorted(CONTRACTS.glob("gold_*_mapping.odcs.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        schema = doc["schema"][0]
        if schema["name"] == category:
            return schema["sourceTable"]
    raise AssertionError(f"no mapping contract declares category {category!r}")


@pytest.fixture(scope="module")
def con():
    path = Path(os.environ.get("MM_WAREHOUSE_PATH") or WAREHOUSE)
    if not path.is_file():
        pytest.skip(f"no built warehouse at {path}")
    connection = duckdb.connect(str(path), read_only=True)
    yield connection
    connection.close()


def _rate(con, sql: str) -> float:
    (value,) = con.execute(sql).fetchone()
    return float(value)


@pytest.mark.parametrize("table,join", _silver_joins(), ids=lambda v: v if isinstance(v, str) else v["name"])
def test_silver_join_completeness_is_as_declared(con, table, join):
    """The fraction of rows whose left column resolves in the right table
    equals the declared measurement and clears the declared floor."""
    actual = _rate(
        con,
        f"select avg(case when exists (select 1 from silver.{join['right_table']} r"
        f" where r.{join['right_column']} = l.{join['left_column']}) then 1 else 0 end)"
        f" from silver.{table} l",
    )
    assert actual >= join["floor"], f"{table}.{join['name']}: {actual:.4f} below floor {join['floor']}"
    assert abs(actual - join["measured_completeness"]) < TOLERANCE, (
        f"{table}.{join['name']}: declared {join['measured_completeness']}, measured {actual:.4f};"
        " re-measure and amend the contract, never leave a stale number in the expert context"
    )


@pytest.mark.parametrize("join", _cross_joins(), ids=lambda j: j["name"])
def test_cross_category_join_holds_on_the_typed_surfaces(con, join):
    """The star's declared cross-category join, measured where an agent
    would run it (the two typed marts) and where it was settled (the two
    silver tables): both equal the declaration and clear the floor, and
    they equal each other, so gold preserved the joinability."""
    # The condition names the two categories as its aliases, so an agent
    # pastes it under FROM mart_<left>_typed AS <left> JOIN
    # mart_<right>_typed AS <right> unchanged; the test does the same.
    condition = join["join_condition"]
    left, right = join["left"], join["right"]
    typed = _rate(
        con,
        f"select avg(case when {right}.__hit is not null then 1 else 0 end) from"
        f" gold.mart_{left}_typed as {left}"
        f" left join (select *, 1 as __hit from gold.mart_{right}_typed) as {right}"
        f" on {condition}",
    )
    silver = _rate(
        con,
        f"select avg(case when {right}.__hit is not null then 1 else 0 end) from"
        f" {_mapping_source(left)} as {left}"
        f" left join (select *, 1 as __hit from {_mapping_source(right)}) as {right}"
        f" on {condition}",
    )
    if join.get("example_sql"):
        # The worked example runs as written and returns rows.
        assert con.execute(join["example_sql"]).fetchall(), f"{join['name']}: example_sql returned no rows"
    assert typed >= join["floor"], f"{join['name']}: typed {typed:.4f} below floor {join['floor']}"
    assert abs(typed - join["measured_completeness"]) < TOLERANCE, (
        f"{join['name']}: declared {join['measured_completeness']}, typed surfaces measure {typed:.4f}"
    )
    assert abs(typed - silver) < TOLERANCE, (
        f"{join['name']}: silver {silver:.4f} and gold {typed:.4f} disagree; the star lost rows or keys"
    )


def test_cross_category_join_shares_the_calendar(con):
    """The conformed calendar in numbers: every timeframe row the left
    category minted at the join's grain is a row the right category
    minted too (equal periods at equal grain are one row, Amendment R),
    so the two facts meet on timeframe_hash_id without a calendar join."""
    for join in _cross_joins():
        (left_periods, shared) = con.execute(
            f"select count(distinct l.timeframe_hash_id),"
            f" count(distinct case when r.timeframe_hash_id is not null then l.timeframe_hash_id end)"
            f" from gold.fact_{join['left']}_values l"
            f" left join (select distinct timeframe_hash_id from gold.fact_{join['right']}_values) r"
            f" using (timeframe_hash_id)"
        ).fetchone()
        assert left_periods > 0
        assert shared / left_periods >= join["floor"], (
            f"{join['name']}: {shared} of {left_periods} left periods exist on the right"
        )
