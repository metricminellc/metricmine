"""Fetch OurAirports airports.csv at a pinned commit and write the extract.

Governing decision: D-15 as amended (Arc 6, D-41).
Source: OurAirports (David Megginson and contributors), airports.csv.
Released to the public domain by its publisher. The publisher's own
download channel is the GitHub repository davidmegginson/ourairports-data,
so the artifact is pinned by commit SHA and cannot move:
https://raw.githubusercontent.com/davidmegginson/ourairports-data/<COMMIT>/airports.csv

The window: every airport carrying an IATA code (the code the flights
source joins on), all columns as published. This script takes no
arguments. The commit SHA is the pin; RAW_SHA256 double-checks the bytes.
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

SOURCE = "ourairports_airports"
COMMIT = "d27027ba44140de187960d71a98260de6a94b38e"  # main on 2026-09-02
SOURCE_URL = (
    "https://raw.githubusercontent.com/davidmegginson/ourairports-data/"
    f"{COMMIT}/airports.csv"
)
RAW_CSV = RAW_ROOT / SOURCE / f"airports_{COMMIT[:12]}.csv"
RAW_SHA256: str | None = "857af826fe9b46ed85c16ac46c177e81cf71148ff7fc08195f0997161560b570"
OUT_DIR = SAMPLES_ROOT / SOURCE
MAX_BYTES = 10 * 1024 * 1024


def main() -> int:
    download(SOURCE_URL, RAW_CSV)
    verify_raw(RAW_CSV, RAW_SHA256)
    text = RAW_CSV.read_bytes().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text, newline=""))
    header = next(reader)
    if "iata_code" not in header:
        raise SystemExit(f"ERROR: no iata_code column in {header}")
    iata_idx = header.index("iata_code")
    rows = [row for row in reader if row and row[iata_idx].strip()]
    out_csv = OUT_DIR / f"{SOURCE}_{COMMIT[:12]}.csv"
    write_extract(SOURCE, out_csv, header, rows, MAX_BYTES)
    return 0


if __name__ == "__main__":
    main_guard(main)
