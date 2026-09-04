# nycflights13 weather extract

Governing decision: D-15 as amended by Amendment T
(../../../docs/decisions/decision-register.md); the Arc 6 multi-source
proof (D-41).

- Source: the `weather` table of the nycflights13 R data package
  (Hadley Wickham; Posit Software, PBC). https://nycflights13.tidyverse.org
- Origin, as the package documents it: hourly ASOS observations at the
  three New York City airports (EWR, JFK, LGA) for 2013, downloaded from
  the Iowa Environmental Mesonet; the package converts wind speeds to
  mph, keeps one row per airport per hour (the maximum of the records
  before the minute-51 precipitation reset), and reports local
  year, month, day, and hour beside the UTC instant.
- Citation: Wickham H (2023). nycflights13, repository
  tidyverse/nycflights13, commit df98ef215aa8216fe0838a0b8ac5bada646d814c
  (main on 2023-11-21), file `data-raw/weather.csv`.
- License: CC0 (the package's declared license).
- Retrieved: 2026-09-02 from
  https://raw.githubusercontent.com/tidyverse/nycflights13/df98ef215aa8216fe0838a0b8ac5bada646d814c/data-raw/weather.csv
  (2,294,215 bytes, sha256
  5d1ea2548a3941eac0b4a9ca70805daa9fa49bbb711a0c7557b2bba0bd7c3f64;
  the script refuses to extract from bytes with any other digest).
- Window: January through June 2013 (the local `month` column), all
  fifteen columns as published, including the "NA" missing markers the
  publisher writes (here "NA" means missing, so the landing keeps
  pandas' default reading of it; compare the OurAirports note, F-50).
- Rows: 13,014 data rows plus one header row; 1,149,905 bytes; extract
  sha256 4092d00f522d3860122c0e41b3cfa96931e660366273f13567b84c9a7342fe77.
- Normalization, deterministic and documented: rows sorted
  lexicographically by every column; UTF-8; LF endings; no value edits.
- Semantics carried into the silver contract: temp and dewp in degrees
  Fahrenheit; humid relative humidity in percent; wind_dir in degrees,
  wind_speed and wind_gust in mph; precip in inches; pressure sea-level
  millibars; visib in miles; `time_hour` the observation hour as a UTC
  instant, the key that joins to flights.
- Regenerate byte-identically: `uv run python scripts/fetch_nyc_weather.py`.
