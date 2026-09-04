"""Fetch the nycflights13 planes table at the pinned commit (whole table).

Governing decision: D-15 as amended (Arc 6, D-41). Origin: the FAA
aircraft registry (the 2014 releasable download), as packaged by
tidyverse/nycflights13 (CC0): plane metadata for the tail numbers found
in the registry among the 2013 NYC flights. `data-raw/planes.csv`, as
published (the "NA" missing markers included).

    uv run python scripts/fetch_nyc_planes.py
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
from fetch_nyc_common import COMMIT, raw_url

SOURCE = "nyc_planes"
SOURCE_URL = raw_url("data-raw/planes.csv")
RAW_CSV = RAW_ROOT / SOURCE / f"planes_{COMMIT[:12]}.csv"
RAW_SHA256: str | None = "778962edec8339f6f6edb1d6506869f61cab573eda03d7e162d2899c76d04c1a"
OUT_DIR = SAMPLES_ROOT / SOURCE
MAX_BYTES = 10 * 1024 * 1024


def main() -> int:
    download(SOURCE_URL, RAW_CSV)
    verify_raw(RAW_CSV, RAW_SHA256)
    text = RAW_CSV.read_bytes().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text, newline=""))
    header = next(reader)
    rows = [row for row in reader if row]
    out_csv = OUT_DIR / f"{SOURCE}_{COMMIT[:12]}.csv"
    write_extract(SOURCE, out_csv, header, rows, MAX_BYTES)
    return 0


if __name__ == "__main__":
    main_guard(main)
