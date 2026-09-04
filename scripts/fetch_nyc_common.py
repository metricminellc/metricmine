"""The nycflights13 family: one pinned publisher artifact set (D-15 as amended).

Source: the tidyverse nycflights13 R data package (Hadley Wickham; Posit
Software, PBC), released under CC0, on GitHub at
tidyverse/nycflights13. Its `data/` and `data-raw/` files are the
publisher's canonical artifacts, pinned by commit SHA so they cannot
move; the package documents each table's origin (BTS on-time
performance for the 2013 NYC departures, the Iowa Environmental
Mesonet ASOS feed for the airport weather, the FAA aircraft registry
for the planes, the BTS carrier lookup for the airlines).

Every script in the family shares the commit, the raw-file URL form, and
the window (January to June 2013 for the two dated tables: half a year
keeps the event extract under the 20 MB budget, and the window is code).
"""

from __future__ import annotations

COMMIT = "df98ef215aa8216fe0838a0b8ac5bada646d814c"  # main on 2023-11-21
RAW_BASE = f"https://raw.githubusercontent.com/tidyverse/nycflights13/{COMMIT}/"
WINDOW_MONTHS = (1, 2, 3, 4, 5, 6)
WINDOW_TAG = "2013-01_2013-06"


def raw_url(path: str) -> str:
    return RAW_BASE + path
