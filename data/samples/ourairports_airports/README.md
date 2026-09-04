# OurAirports airports extract

Governing decision: D-15 as amended by Amendment T
(../../../docs/decisions/decision-register.md); the Arc 6 multi-source
proof (D-41).

- Source: OurAirports, airports.csv (David Megginson and contributors).
  https://ourairports.com/data/
- Citation: OurAirports. airports.csv, repository
  davidmegginson/ourairports-data, commit
  d27027ba44140de187960d71a98260de6a94b38e (main on 2026-09-02).
- License: public domain, as released by the publisher ("OurAirports
  data is in the Public Domain").
- Retrieved: 2026-09-02 from
  https://raw.githubusercontent.com/davidmegginson/ourairports-data/d27027ba44140de187960d71a98260de6a94b38e/airports.csv
  (12,715,871 bytes, sha256
  857af826fe9b46ed85c16ac46c177e81cf71148ff7fc08195f0997161560b570;
  the script refuses to extract from bytes with any other digest).
- Window: every airport carrying a non-empty iata_code, all columns as
  published, no renames.
- Rows: 9,057 data rows plus one header row; 1,664,615 bytes; extract
  sha256 34bbc6719ee42e42be6f5fb4480129c8ab33951005ff8995e14f604df98b3f91.
- Normalization, deterministic and documented: rows sorted
  lexicographically by every column; UTF-8; LF endings; no value edits.
- Landing note (F-50): the continent code for North America and the
  country code for Namibia are the text "NA", which pandas reads as
  missing by default; the landing pins keep_default_na false so every
  code arrives as text.
- Regenerate byte-identically: `uv run python scripts/fetch_ourairports_airports.py`
  (downloads the raw file to gitignored data/raw/ on first run).
