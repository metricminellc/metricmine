# nycflights13 planes extract

Governing decision: D-15 as amended by Amendment T
(../../../docs/decisions/decision-register.md); the Arc 6 multi-source
proof (D-41).

- Source: the `planes` table of the nycflights13 R data package
  (Hadley Wickham; Posit Software, PBC). https://nycflights13.tidyverse.org
- Origin, as the package documents it: the FAA aircraft registry
  (the releasable aircraft download, 2014 release), reduced to the tail
  numbers found in the registry among the 2013 NYC flights; American
  Airlines and Envoy Air reported fleet numbers rather than tail numbers,
  so their aircraft do not match.
- Citation: Wickham H (2023). nycflights13, repository
  tidyverse/nycflights13, commit df98ef215aa8216fe0838a0b8ac5bada646d814c
  (main on 2023-11-21), file `data-raw/planes.csv`.
- License: CC0 (the package's declared license).
- Retrieved: 2026-09-02 from
  https://raw.githubusercontent.com/tidyverse/nycflights13/df98ef215aa8216fe0838a0b8ac5bada646d814c/data-raw/planes.csv
  (247,198 bytes, sha256
  778962edec8339f6f6edb1d6506869f61cab573eda03d7e162d2899c76d04c1a;
  the script refuses to extract from bytes with any other digest).
- Window: the whole table, all nine columns as published, including the
  "NA" missing markers (year of manufacture and speed are missing for
  some aircraft; "NA" means missing here).
- Rows: 3,322 data rows plus one header row; 247,198 bytes; extract
  sha256 778962edec8339f6f6edb1d6506869f61cab573eda03d7e162d2899c76d04c1a
  (the published file is already in sorted order, so the extract equals
  the raw bytes).
- Semantics carried into the silver contract: year is the year of
  manufacture; engines and seats are counts; speed is average cruising
  speed in mph; type and engine are the registry's classifications.
- Regenerate byte-identically: `uv run python scripts/fetch_nyc_planes.py`.
