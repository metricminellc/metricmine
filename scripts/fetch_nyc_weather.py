"""Fetch the nycflights13 weather table at the pinned commit; extract H1 2013.

Governing decision: D-15 as amended (Arc 6, D-41). Origin: hourly ASOS
observations at the three NYC airports (EWR, JFK, LGA) for 2013 from the
Iowa Environmental Mesonet, as cleaned and packaged by
tidyverse/nycflights13 (CC0): wind speeds converted to mph, one row per
airport per hour, precipitation taken as the hourly maximum before the
minute-51 reset. The publisher ships `data-raw/weather.csv`; this script
windows it to January through June 2013 by the local month column and
writes the rows as published (the "NA" missing markers included).

    uv run python scripts/fetch_nyc_weather.py
"""

from __future__ import annotations

import csv
import io

from fetch_common import (
    RAW_ROOT,
    SAMPLES_ROOT,
    download,
    main_guard,
    verify_raw,
    write_extract,
)
from fetch_nyc_common import COMMIT, WINDOW_MONTHS, WINDOW_TAG, raw_url

SOURCE = "nyc_weather"
SOURCE_URL = raw_url("data-raw/weather.csv")
RAW_CSV = RAW_ROOT / SOURCE / f"weather_{COMMIT[:12]}.csv"
RAW_SHA256: str | None = "5d1ea2548a3941eac0b4a9ca70805daa9fa49bbb711a0c7557b2bba0bd7c3f64"
OUT_DIR = SAMPLES_ROOT / SOURCE
MAX_BYTES = 10 * 1024 * 1024


def main() -> int:
    download(SOURCE_URL, RAW_CSV)
    verify_raw(RAW_CSV, RAW_SHA256)
    text = RAW_CSV.read_bytes().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text, newline=""))
    header = next(reader)
    month_idx = header.index("month")
    wanted = {str(m) for m in WINDOW_MONTHS}
    rows = [row for row in reader if row and row[month_idx] in wanted]
    out_csv = OUT_DIR / f"{SOURCE}_{WINDOW_TAG}.csv"
    write_extract(SOURCE, out_csv, header, rows, MAX_BYTES)
    return 0


if __name__ == "__main__":
    main_guard(main)
