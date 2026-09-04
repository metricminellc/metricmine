"""Local conservation and business-logic checks for the aviation family (D-41).

Marked `local`: needs the gitignored warehouse (`make ingest`, then
`dbt build`). The retail conservation test pins one table's dedup
arithmetic; this pins the multi-source family's row conservation through
every plane and the business-logic identities the contracts' prose
asserts, so a claim an agent reads in the expert context is a claim
this lane has measured:

- Bronze to silver: the six cleanup tables drop no rows (the contracts
  say so), and the two unified tables keep every event row of their
  cleanup source (joins add attributes, never rows).
- Silver to gold: each category's fact table and typed mart carry
  exactly the unified table's rows (C1 and C5 hold this per category in
  the contract gate; this is the family view in one place).
- Business logic: the clock arithmetic (HHMM columns against the hour
  and minute columns, the delays against the actual and scheduled
  times), the local calendar against the UTC hour under America/New_York,
  the cancellation and arrival-record null patterns the usage text
  explains, and the vintage effect the limitations name (one destination
  code the 2026 reference has recoded).

The pinned tuples are the regression gate: a new sample window or a new
reference commit changes them deliberately, with the contracts.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest

_WAREHOUSE = Path(__file__).resolve().parents[1] / "warehouse" / "metricmine.duckdb"

pytestmark = pytest.mark.local

CLEANUP = {
    "nyc_flights": "silver_nyc_flights",
    "nyc_weather": "silver_nyc_weather",
    "nyc_airlines": "silver_nyc_airlines",
    "nyc_planes": "silver_nyc_planes",
    "ourairports_airports": "silver_ourairports_airports",
    "ourairports_runways": "silver_ourairports_runways",
}
UNIFIED = {
    "silver_flights": "silver_nyc_flights",
    "silver_airport_weather": "silver_nyc_weather",
}
CATEGORIES = {
    "flights": "silver_flights",
    "airport_weather": "silver_airport_weather",
}
PINNED_ROWS = {
    "silver_nyc_flights": 166158,
    "silver_nyc_weather": 13014,
    "silver_nyc_airlines": 16,
    "silver_nyc_planes": 3322,
    "silver_ourairports_airports": 9057,
    "silver_ourairports_runways": 10760,
}


@pytest.fixture(scope="module")
def con():
    path = Path(os.environ.get("MM_WAREHOUSE_PATH") or _WAREHOUSE)
    if not path.is_file():
        pytest.skip(f"warehouse not built at {path}; run `make ingest` first")
    c = duckdb.connect(str(path), read_only=True)
    yield c
    c.close()


def _count(con, table: str) -> int:
    (n,) = con.execute(f"select count(*) from {table}").fetchone()
    return int(n)


def test_cleanup_tables_drop_no_rows(con):
    for source, silver in CLEANUP.items():
        bronze_rows = _count(con, f"bronze.{source}")
        silver_rows = _count(con, f"silver.{silver}")
        assert bronze_rows == silver_rows == PINNED_ROWS[silver], (source, bronze_rows, silver_rows)


def test_unified_tables_keep_every_event_row(con):
    for unified, source in UNIFIED.items():
        assert _count(con, f"silver.{unified}") == _count(con, f"silver.{source}")


def test_gold_carries_every_unified_row(con):
    for category, unified in CATEGORIES.items():
        rows = _count(con, f"silver.{unified}")
        assert _count(con, f"gold.fact_{category}_values") == rows
        assert _count(con, f"gold.mart_{category}_typed") == rows
        assert _count(con, f"gold.vw_{category}_typed") == rows


def test_clock_arithmetic_holds_on_every_flight(con):
    """HHMM columns agree with the hour and minute columns, and each delay
    is the actual minus the scheduled clock time, modulo the midnight
    wrap (a flight scheduled 23:55 that left 00:10 is 15 minutes late)."""
    checks = {
        "sched_dep_hhmm != sched_dep_hour_local * 100 + sched_dep_minute_local": 0,
        (
            "dep_hhmm is not null and abs(((dep_hhmm // 100) * 60 + dep_hhmm % 100)"
            " - ((sched_dep_hhmm // 100) * 60 + sched_dep_hhmm % 100)"
            " - dep_delay_minutes) not in (0, 1440)"
        ): 0,
        (
            "arr_hhmm is not null and arr_delay_minutes is not null"
            " and abs(((arr_hhmm // 100) * 60 + arr_hhmm % 100)"
            " - ((sched_arr_hhmm // 100) * 60 + sched_arr_hhmm % 100)"
            " - arr_delay_minutes) not in (0, 1440)"
        ): 0,
        "distance_miles <= 0 or air_time_minutes <= 0": 0,
    }
    for where, expected in checks.items():
        (n,) = con.execute(f"select count(*) from silver.silver_flights where {where}").fetchone()
        assert n == expected, where


def test_local_calendar_agrees_with_the_utc_hour(con):
    """The local date and hour columns are the UTC instant rendered in
    America/New_York on every row, DST included (the contracts carry the
    hour half of this as a quality rule; the date half lives here)."""
    for table, date_col, hour_col, utc_col in (
        ("silver_nyc_flights", "flight_date", "sched_dep_hour_local", "departure_hour_utc"),
        ("silver_nyc_weather", "observed_date_local", "observed_hour_local", "observed_hour_utc"),
    ):
        (n,) = con.execute(
            f"select count(*) from silver.{table} where {date_col} !="
            f" cast(({utc_col} at time zone 'UTC' at time zone 'America/New_York') as date)"
            f" or {hour_col} != extract(hour from ({utc_col} at time zone 'UTC' at time zone 'America/New_York'))"
        ).fetchone()
        assert n == 0, table


def test_null_patterns_match_the_usage_text(con):
    """dep_delay_minutes is null exactly when the flight is cancelled;
    arr_delay_minutes and air_time_minutes are null on those plus the
    flights that departed with no arrival record, and on the same rows
    as each other; the pinned counts are the ones the contracts quote."""
    row = con.execute(
        "select sum(case when is_cancelled then 1 else 0 end),"
        " sum(case when dep_delay_minutes is null then 1 else 0 end),"
        " sum(case when is_cancelled and dep_hhmm is not null then 1 else 0 end),"
        " sum(case when arr_delay_minutes is null then 1 else 0 end),"
        " sum(case when arr_delay_minutes is null and not is_cancelled then 1 else 0 end),"
        " sum(case when (arr_delay_minutes is null) != (air_time_minutes is null) then 1 else 0 end),"
        " sum(case when tail_number is null then 1 else 0 end)"
        " from silver.silver_flights"
    ).fetchone()
    cancelled, dep_null, cancelled_with_dep, arr_null, arr_null_flown, arr_air_disagree, no_tail = row
    assert cancelled == dep_null == 4883
    assert cancelled_with_dep == 0
    assert arr_null == 5480 and arr_null_flown == 597
    assert arr_air_disagree == 0
    assert no_tail == 1521


def test_reference_coverage_matches_the_limitations(con):
    """The joins the unified table settled, counted the way the prose
    counts them, and the vintage effect by name: every unresolved
    destination is the one code the 2026 reference recoded."""
    row = con.execute(
        "select sum(case when aircraft_manufacturer is not null then 1 else 0 end),"
        " sum(case when dest_airport_name is not null then 1 else 0 end),"
        " sum(case when carrier_name is null then 1 else 0 end),"
        " sum(case when origin_airport_name is null then 1 else 0 end)"
        " from silver.silver_flights"
    ).fetchone()
    aircraft, dest, carrier_null, origin_null = row
    assert (aircraft, dest, carrier_null, origin_null) == (139502, 162687, 0, 0)
    unresolved = con.execute(
        "select dest_airport, count(*) from silver.silver_flights"
        " where dest_airport_name is null group by 1"
    ).fetchall()
    assert unresolved == [("PBI", 3471)]
    (recoded,) = con.execute(
        "select count(*) from silver.silver_ourairports_airports"
        " where iata_code = 'DJT' and airport_ident = 'KPBI'"
    ).fetchone()
    assert recoded == 1, "the 2026 reference carries Palm Beach under DJT with ident KPBI"


def test_weather_coverage_matches_the_limitations(con):
    """13,014 of the 13,026 airport-hours between the first and last
    observation are present, four missing per airport, and exactly 97
    flights find no weather at their origin in their departure hour."""
    rows = con.execute(
        "with hours as (select unnest(generate_series("
        " (select min(observed_hour_utc) from silver.silver_airport_weather),"
        " (select max(observed_hour_utc) from silver.silver_airport_weather),"
        " interval 1 hour)) as h),"
        " airports as (select distinct airport_code from silver.silver_airport_weather)"
        " select a.airport_code, count(*), count(w.observed_hour_utc)"
        " from airports a cross join hours h"
        " left join silver.silver_airport_weather w"
        " on w.airport_code = a.airport_code and w.observed_hour_utc = h.h"
        " group by 1 order by 1"
    ).fetchall()
    assert rows == [("EWR", 4342, 4338), ("JFK", 4342, 4338), ("LGA", 4342, 4338)]
    (orphans,) = con.execute(
        "select count(*) from silver.silver_flights f where not exists"
        " (select 1 from silver.silver_airport_weather w"
        " where w.airport_code = f.origin_airport and w.observed_hour_utc = f.departure_hour_utc)"
    ).fetchone()
    assert orphans == 97
