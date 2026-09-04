"""Fetch OurAirports runways.csv at the pinned commit and write the extract.

Governing decision: D-15 as amended (Arc 6, D-41).
Source: OurAirports (David Megginson and contributors), runways.csv, public
domain, pinned by commit SHA through the publisher's GitHub channel:
https://raw.githubusercontent.com/davidmegginson/ourairports-data/<COMMIT>/runways.csv

The window: the runways of the airports in the committed airports
extract (data/samples/ourairports_airports/), joined on airport_ident, all
columns as published. Run scripts/fetch_ourairports_airports.py first.
This script takes no arguments.
"""

from __future__ import annotations

import csv
import io

from fetch_common import (
    RAW_ROOT,
    SAMPLES_ROOT,
    download,
    main_guard,
    read_csv,
    verify_raw,
    write_extract,
)

SOURCE = "ourairports_runways"
COMMIT = "d27027ba44140de187960d71a98260de6a94b38e"  # the airports commit
SOURCE_URL = (
    "https://raw.githubusercontent.com/davidmegginson/ourairports-data/"
    f"{COMMIT}/runways.csv"
)
RAW_CSV = RAW_ROOT / SOURCE / f"runways_{COMMIT[:12]}.csv"
RAW_SHA256: str | None = "307a36f63a4a6a471a4b4b53881ee4fe11a3758a78a8804b8203fb2c3fef8b07"
OUT_DIR = SAMPLES_ROOT / SOURCE
AIRPORTS_EXTRACT = (
    SAMPLES_ROOT / "ourairports_airports" / f"ourairports_airports_{COMMIT[:12]}.csv"
)
MAX_BYTES = 10 * 1024 * 1024


def main() -> int:
    if not AIRPORTS_EXTRACT.is_file():
        raise SystemExit(
            f"ERROR: {AIRPORTS_EXTRACT} not found; run"
            " scripts/fetch_ourairports_airports.py first"
        )
    airports_header, airports_rows = read_csv(AIRPORTS_EXTRACT)
    ident_idx = airports_header.index("ident")
    idents = {row[ident_idx] for row in airports_rows}
    download(SOURCE_URL, RAW_CSV)
    verify_raw(RAW_CSV, RAW_SHA256)
    text = RAW_CSV.read_bytes().decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text, newline=""))
    header = next(reader)
    ref_idx = header.index("airport_ident")
    rows = [row for row in reader if row and row[ref_idx] in idents]
    out_csv = OUT_DIR / f"{SOURCE}_{COMMIT[:12]}.csv"
    write_extract(SOURCE, out_csv, header, rows, MAX_BYTES)
    return 0


if __name__ == "__main__":
    main_guard(main)
