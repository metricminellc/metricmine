# nycflights13 flights extract

Governing decision: D-15 as amended by Amendment T
(../../../docs/decisions/decision-register.md); the Arc 6 multi-source
proof (D-41).

- Source: the `flights` table of the nycflights13 R data package
  (Hadley Wickham; Posit Software, PBC). https://nycflights13.tidyverse.org
- Origin, as the package documents it: RITA, Bureau of Transportation
  Statistics, Reporting Carrier On-Time Performance, all 2013 flights that
  departed New York City (JFK, LGA, EWR).
- Citation: Wickham H (2023). nycflights13: Flights that Departed NYC in
  2013. R package version 1.0.2.9000, repository tidyverse/nycflights13,
  commit df98ef215aa8216fe0838a0b8ac5bada646d814c (main on 2023-11-21).
- License: CC0 (the package's declared license).
- Retrieved: 2026-09-02 from
  https://raw.githubusercontent.com/tidyverse/nycflights13/df98ef215aa8216fe0838a0b8ac5bada646d814c/data/flights.rda
  (4,299,947 bytes, sha256
  30252b3d787e832c1f7c9cb5adf270ea595f54e5dcb1d96778463a58ff79e714;
  the script refuses to extract from bytes with any other digest).
- Window: January through June 2013 (the `month` column), every
  departure from the three airports, all nineteen columns as published.
  Half a year keeps the extract under the 20 MB event-source budget; the
  full year is 336,776 rows and 31 MB, and the window is code.
- Rows: 166,158 data rows plus one header row; 15,215,202 bytes; extract
  sha256 ea3bce0babe2b330db58b7b16ef8a2c1fa346d71c7f37da2ead495260b7bef18.
- Serialization, deterministic and documented: the R data file is read
  with pyreadr 0.5.3; whole-number columns land as integers (dep_time,
  arr_time, dep_delay, arr_delay, air_time, distance, hour, minute);
  missing values are empty fields (a cancelled flight has no dep_time);
  `time_hour` is the scheduled departure hour as an instant in UTC with a
  Z suffix (the package's own weather.csv convention; the package builds
  it in America/New_York); rows sorted lexicographically by every
  column; UTF-8; LF endings; no value edits.
- Semantics carried into the silver contract: dep_time and arr_time are
  local clock times in HHMM form; delays are minutes with negative values
  early; hour and minute are the local scheduled departure split; distance
  is miles; air_time is minutes; carrier is the two-letter code the
  airlines lookup resolves; tailnum resolves in the planes table where
  the FAA registry knows it (American and Envoy reported fleet numbers).
- Regenerate byte-identically: `uv run --with "pyreadr==0.5.3" python scripts/fetch_nyc_flights.py`
  (downloads the raw file to gitignored data/raw/ on first run).
