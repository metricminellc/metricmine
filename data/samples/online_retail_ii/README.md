# Online Retail II sample extract

Governing decision: D-15 (../../../docs/decisions/decision-register.md).

- Source: Online Retail II, UCI Machine Learning Repository.
- Citation: Chen, D. (2012). Online Retail II [Dataset]. UCI Machine
  Learning Repository. https://doi.org/10.24432/C5CG6D
- License: Creative Commons Attribution 4.0 International (CC BY 4.0).
- Retrieved: 2026-07-26 from
  https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip
- Window: December 2009, 2009-12-01 inclusive to 2010-01-01 exclusive,
  sheet "Year 2009-2010", complete invoices within the window.
- Rows: 45,228 data rows plus one header row.
- Columns: as landed from the source workbook header, no renames.
- Normalization, deterministic and documented: datetimes serialized as
  YYYY-MM-DD HH:MM:SS; whole-number floats written as integers (Customer
  ID); rows sorted lexicographically by all columns; UTF-8; LF endings.
- Regenerate byte-identically: `uv run python scripts/fetch_sample.py`
  (downloads the raw workbook to gitignored data/raw/ on first run).
- Mirror note: a Kaggle mirror exists and is acceptable for retrieval;
  UCI is the cited source (D-15).
