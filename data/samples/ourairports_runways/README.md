# OurAirports runways extract

Governing decision: D-15 as amended by Amendment T
(../../../docs/decisions/decision-register.md); the Arc 6 multi-source
proof (D-41).

- Source: OurAirports, runways.csv (David Megginson and contributors).
  https://ourairports.com/data/
- Citation: OurAirports. runways.csv, repository
  davidmegginson/ourairports-data, commit
  d27027ba44140de187960d71a98260de6a94b38e (the airports extract's commit).
- License: public domain, as released by the publisher ("OurAirports
  data is in the Public Domain").
- Retrieved: 2026-09-02 from
  https://raw.githubusercontent.com/davidmegginson/ourairports-data/d27027ba44140de187960d71a98260de6a94b38e/runways.csv
  (3,962,925 bytes, sha256
  307a36f63a4a6a471a4b4b53881ee4fe11a3758a78a8804b8203fb2c3fef8b07;
  the script refuses to extract from bytes with any other digest).
- Window: the runways whose airport_ident is in the committed airports
  extract (the airports carrying an IATA code), all columns as published,
  no renames. Many runways to one airport.
- Rows: 10,760 data rows plus one header row; 1,144,263 bytes; extract
  sha256 de59705512170f8733ee30caaab4833912a7bb8319604eb12e75cde519dfd52b.
- Normalization, deterministic and documented: rows sorted
  lexicographically by every column; UTF-8; LF endings; no value edits.
- Regenerate byte-identically: `uv run python scripts/fetch_ourairports_runways.py`
  (reads the committed airports extract; downloads the raw file to
  gitignored data/raw/ on first run).
