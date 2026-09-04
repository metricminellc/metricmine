# nycflights13 airlines extract

Governing decision: D-15 as amended by Amendment T
(../../../docs/decisions/decision-register.md); the Arc 6 multi-source
proof (D-41).

- Source: the `airlines` table of the nycflights13 R data package
  (Hadley Wickham; Posit Software, PBC). https://nycflights13.tidyverse.org
- Origin, as the package documents it: the BTS carrier code lookup
  (https://www.transtats.bts.gov/DL_SelectFields.asp?Table_ID=236),
  reduced to the sixteen carriers that flew from New York City in 2013.
- Citation: Wickham H (2023). nycflights13, repository
  tidyverse/nycflights13, commit df98ef215aa8216fe0838a0b8ac5bada646d814c
  (main on 2023-11-21), file `data-raw/airlines.csv`.
- License: CC0 (the package's declared license).
- Retrieved: 2026-09-02 from
  https://raw.githubusercontent.com/tidyverse/nycflights13/df98ef215aa8216fe0838a0b8ac5bada646d814c/data-raw/airlines.csv
  (386 bytes, sha256
  162551bd3401a12d63db3d92b7e66af3017d2e40d55919d6a678489323c10609;
  the script refuses to extract from bytes with any other digest).
- Window: the whole table, both columns as published.
- Rows: 16 data rows plus one header row; 386 bytes; extract sha256
  162551bd3401a12d63db3d92b7e66af3017d2e40d55919d6a678489323c10609
  (the published file is already in sorted order, so the extract equals
  the raw bytes).
- Regenerate byte-identically: `uv run python scripts/fetch_nyc_airlines.py`.
