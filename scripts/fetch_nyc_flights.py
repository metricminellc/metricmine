"""Fetch the nycflights13 flights table at the pinned commit; extract H1 2013.

Governing decision: D-15 as amended (Arc 6, D-41). Origin: BTS Reporting
Carrier On-Time Performance, 2013, flights departing JFK, LGA, and EWR,
as packaged by tidyverse/nycflights13 (CC0). The publisher ships the
table as `data/flights.rda` (an R data file, bzip2); this script reads it
with pyreadr and writes the window as a deterministic CSV:

    uv run --with "pyreadr==0.5.3" python scripts/fetch_nyc_flights.py

Serialization, documented and deterministic: whole-number columns land
as integers (dep_time, arr_time, dep_delay, arr_delay, air_time,
distance, hour, minute), missing values as empty fields, `time_hour` as
UTC in ISO form with a Z suffix (the package's own weather.csv
convention; the package builds it in America/New_York and the R data
carries the instant). Rows sort lexicographically by every column.
"""

from __future__ import annotations

from fetch_common import (
    RAW_ROOT,
    SAMPLES_ROOT,
    download,
    main_guard,
    verify_raw,
    write_extract,
)
from fetch_nyc_common import COMMIT, WINDOW_MONTHS, WINDOW_TAG, raw_url

SOURCE = "nyc_flights"
SOURCE_URL = raw_url("data/flights.rda")
RAW_FILE = RAW_ROOT / SOURCE / f"flights_{COMMIT[:12]}.rda"
RAW_SHA256: str | None = "30252b3d787e832c1f7c9cb5adf270ea595f54e5dcb1d96778463a58ff79e714"
OUT_DIR = SAMPLES_ROOT / SOURCE
MAX_BYTES = 20 * 1024 * 1024
INTEGER_COLUMNS = (
    "dep_time",
    "arr_time",
    "dep_delay",
    "arr_delay",
    "air_time",
    "distance",
    "hour",
    "minute",
)


def main() -> int:
    try:
        import pyreadr
    except ImportError:
        raise SystemExit(
            "ERROR: pyreadr is not installed in this environment. Run:\n"
            '  uv run --with "pyreadr==0.5.3" python scripts/fetch_nyc_flights.py'
        )
    download(SOURCE_URL, RAW_FILE)
    verify_raw(RAW_FILE, RAW_SHA256)
    frame = pyreadr.read_r(str(RAW_FILE))["flights"]
    frame = frame[frame["month"].isin(WINDOW_MONTHS)].copy()
    for column in INTEGER_COLUMNS:
        frame[column] = frame[column].astype("Int64")
    frame["time_hour"] = frame["time_hour"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    header = list(frame.columns)
    rows = []
    for record in frame.itertuples(index=False, name=None):
        rows.append(["" if _missing(value) else str(value) for value in record])
    out_csv = OUT_DIR / f"{SOURCE}_{WINDOW_TAG}.csv"
    write_extract(SOURCE, out_csv, header, rows, MAX_BYTES)
    return 0


def _missing(value) -> bool:
    if value is None:
        return True
    try:
        import pandas as pd

        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


if __name__ == "__main__":
    main_guard(main)
