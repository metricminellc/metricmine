Arc 1 gate re-proof at dbt-core 1.12.3 with dbt-duckdb 1.11.0, 2026-08-28 (the Mac)
Repo head at branch cut: 73b76987ede5af91c792daa4046d1b44dbfd8e1b

Environment: macOS 26.2, arm64; uv 0.11.28; CPython 3.12.2 (the python.org framework build at /Library/Frameworks/Python.framework/Versions/3.12); datacontract-cli 1.0.12 as an isolated uv tool with the [duckdb] extra; network open (dbt deps against hub.getdbt.com; the parser wheel from GitHub releases; public.cdn.getdbt.com reachable but not used: section 6 measured the v2 driver as the Homebrew libduckdb 1.5.4 already on this machine). Wall times and byte sizes are per-machine reports; the D-33 digest is the gate. The sandbox record this re-proves: 2026-08-28_arc1_prep_probe_transcript.md.

== 1. The pin and the lock ==
$ uv add --no-sync "dbt-core>=1.12,<1.13" "dbt-duckdb>=1.11,<1.12"
Resolved 210 packages in 599ms
$ git diff --stat
 pyproject.toml |  4 +--
 uv.lock        | 94 ++++++++++++++++++++++++++++++++++++++--------------------
 2 files changed, 64 insertions(+), 34 deletions(-)
$ git diff uv.lock | grep -E '^[-+](name|version) = ' | paste - - | sort | uniq
-name = "dbt-semantic-interfaces"	-version = "0.9.0"
-version = "1.10.1"	+version = "1.11.0"
-version = "1.11.14"	+version = "1.12.3"
-version = "1.24.4"	+version = "1.24.5"
+name = "dbt-core-experimental-parser"	+version = "2.0.0b2"
+name = "metricflow"	+version = "0.212.0"
+name = "sqlglot"	+version = "30.17.0"
+name = "tabulate"	+version = "0.10.0"
$ head -2 uv.lock
version = 1
revision = 3
$ time uv sync --frozen   (first attempt, failed at the parser sdist build)
   Building dbt-core-experimental-parser==2.0.0b2
  × Failed to build `dbt-core-experimental-parser==2.0.0b2`
      RuntimeError: failed to download
      https://github.com/dbt-labs/dbt-core/releases/download/v2.0.0-beta.2/dbt_core_experimental_parser-2.0.0b2-py3-none-macosx_11_0_arm64.whl:
      <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify
      failed: unable to get local issuer certificate (_ssl.c:1000)>
uv sync --frozen  0.31s user 0.25s system 7% cpu 7.536 total
   Machine-bound cause, measured: the framework CPython's OpenSSL default cafile is /Library/Frameworks/Python.framework/Versions/3.12/etc/openssl/cert.pem, which does not exist on this machine (the framework's certificate install step was never run). uv's own downloads use native TLS and succeeded; the parser sdist's build backend fetches its wheel with Python urllib and had no CA bundle. curl reached the same URL with 200. With SSL_CERT_FILE=/etc/ssl/cert.pem (the macOS system bundle) the same urllib fetch returned 200, so that variable was exported for the session. No file in the repository changed for this.
(retry) $ SSL_CERT_FILE=/etc/ssl/cert.pem time uv sync --frozen
   Building dbt-core-experimental-parser==2.0.0b2
      Built dbt-core-experimental-parser==2.0.0b2
Prepared 1 package in 3.36s
Uninstalled 5 packages in 79ms
Installed 8 packages in 15ms
 - dbt-adapters==1.24.4
 + dbt-adapters==1.24.5
 - dbt-core==1.11.14
 + dbt-core==1.12.3
 + dbt-core-experimental-parser==2.0.0b2
 - dbt-duckdb==1.10.1
 + dbt-duckdb==1.11.0
 - dbt-semantic-interfaces==0.9.0
 + metricflow==0.212.0
 ~ metricmine==0.1.0 (from the repository root; the absolute path relativized)
 + sqlglot==30.17.0
 + tabulate==0.10.0
uv sync --frozen  0.40s user 0.29s system 19% cpu 3.496 total
$ uv run dbt --version
Core:
  - installed: 1.12.3
  - latest:    1.12.3 - Up to date!
Plugins:
  - duckdb: 1.11.0 - Up to date!

== 2. The mirror ==
$ uv run dbt parse --project-dir transform --profiles-dir transform 2>&1 | tail -6   (dbt_project.yml still at [">=1.11.0", "<1.12.0"])
    Installed version of dbt: =1.12.3
    Required version of dbt for 'metricmine': ['>=1.11.0', '<1.12.0']
  Check for a different version of the 'metricmine' package, or run dbt again with --no-version-check
Error encountered in transform/dbt_project.yml
Edit: transform/dbt_project.yml require-dbt-version: [">=1.11.0", "<1.12.0"] -> [">=1.12.0", "<1.13.0"]
$ git diff transform/dbt_project.yml | grep -E "^[-+]require"
-require-dbt-version: [">=1.11.0", "<1.12.0"]
+require-dbt-version: [">=1.12.0", "<1.13.0"]

== 3. The lanes ==
$ uv run ruff check .                    -> All checks passed!
$ uv run pytest -m "not local" -q        -> 411 passed, 52 deselected, 13 warnings in 6.65s
$ uv run pytest tests/agents -q          -> 240 passed in 4.90s
$ uv run pytest tests/agents -m local -q -> 8 passed, 232 deselected in 2.97s

== 4. The build, the scan, the gates, the digest ==
$ make ingest                            -> landed {'online_retail_ii': 45228} into bronze of warehouse/metricmine.duckdb
$ uv run dbt build --project-dir transform --profiles-dir transform --target local
20:16:51  Running with dbt=1.12.3
20:16:51  Registered adapter: duckdb=1.11.0
20:16:51  Unable to do partial parsing because of a version mismatch
20:16:52  Found 13 models, 96 data tests, 1 source, 617 macros
20:16:53  Done. PASS=109 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=109
$ uv run pytest tests/test_adoption_scan.py -q -> 11 passed in 0.65s
$ make scan (first)                      -> plan_hash (over the body above, this line excluded): `sha256:aaef72f8330623e48fb062be37d6edce27e85b55fa241e1a5f8d1bc6163134da`
$ make scan (second)                     -> plan_hash (over the body above, this line excluded): `sha256:aaef72f8330623e48fb062be37d6edce27e85b55fa241e1a5f8d1bc6163134da`
$ plan.md summary
- models scanned: 13
| `skip_engine_owned` | 12 |
| `in_sync` | 1 |
Empty. Every model is in sync or skipped by decision.
$ datacontract lint (each contract)
contracts/gold_invoice_lines_mapping.odcs.yaml: 🟢 data contract is valid. Run 1 checks. Took 0.078515 seconds.
contracts/gold_unified_event_star.odcs.yaml: 🟢 data contract is valid. Run 1 checks. Took 0.089574 seconds.
contracts/silver_invoice_lines.odcs.yaml: 🟢 data contract is valid. Run 1 checks. Took 0.079644 seconds.
$ export DBT_PROFILES_DIR="$PWD/transform"; export MM_WAREHOUSE_PATH="$PWD/warehouse/metricmine.duckdb"
$ uv run datacontract dbt sync contracts/*.odcs.yaml --project-dir transform --target local
gold_invoice_lines_mapping.odcs.yaml: Synced 0 models: updated 0 YAML files.
gold_unified_event_star.odcs.yaml: Synced 10 models: updated 0 YAML files.
silver_invoice_lines.odcs.yaml: Synced 1 model: updated 0 YAML files.
$ git status --porcelain (after sync)
 M pyproject.toml
 M transform/dbt_project.yml
 M uv.lock
?? prep-a1/
$ uv run datacontract dbt test contracts/*.odcs.yaml --project-dir transform --target local
🟢 dbt tests passed. Ran 85 tests. Took 0.005504 seconds.
🟢 dbt tests passed. Ran 11 tests. Took 0.00547 seconds.
Tested 3 contract(s): 1 no tests · 2 passed.
$ uv run dbt parse --project-dir transform --show-all-deprecations 2>&1 | grep -ci deprecat -> 0
$ unset MM_WAREHOUSE_PATH
$ make export-demo
view vw_invoice_lines_typed: 44721 rows, digest match (08eca7be30707e2aa0b48c3d19ddeea4)
artifact size: 12070912 bytes
$ git checkout -- demo/demo.duckdb
$ git status --porcelain (after restore)
 M pyproject.toml
 M transform/dbt_project.yml
 M uv.lock
?? prep-a1/

== 5. The v2 parser gate ==
$ uv run dbt parse --use-v2-parser --project-dir transform --profiles-dir transform
20:17:17  Running with dbt=1.12.3
20:17:17  Delegating parse to v2 parser: dbt-core-experimental-parser parse
  dbt-core 2.0.0-beta.2
   Loading profiles.yml
   Started resolving packages from packages.yml
  Finished [  0.32s] resolving packages from packages.yml (1 items)
==================== Execution Summary =====================
Finished 'parse' successfully for target 'local' [506ms]
20:17:19  v2 parser completed in 2.01s
20:17:19  Registered adapter: duckdb=1.11.0
   (the hub answered from this machine; packages.yml as committed, no local package source needed)
$ uv run dbt build --use-v2-parser --project-dir transform --profiles-dir transform --target local
20:17:21  Delegating parse to v2 parser: dbt-core-experimental-parser parse
20:17:21  v2 parser completed in 0.42s
20:17:21  Found 13 models, 96 data tests, 1 source, 613 macros
20:17:22  1 of 109 ERROR creating sql table model gold.context_registry .................. [ERROR in 0.05s]
  Could not parse constraint: {'type': 'not_null', 'warn_unenforced': None, 'warn_unsupported': None, 'to_columns': []}
   (the same error on dim_invoice_lines_columns, dim_run_columns, dim_run_values, dim_source_columns, dim_source_values, dim_timeframe_columns, and silver_invoice_lines; eight in all)
20:17:22  Done. PASS=2 WARN=0 ERROR=8 SKIP=99 NO-OP=0 REUSED=0 TOTAL=109
$ uv run dbt build --project-dir transform --profiles-dir transform --target local   (the restoring build)
20:17:25  Done. PASS=109 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=109

== 6. The dbt Core 2.0.0-beta.2 smoke (prep-a1/v2venv, a scratch copy of the warehouse) ==
$ uv venv --python 3.12 prep-a1/v2venv
Using CPython 3.12.2 interpreter at: /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12
$ uv pip install --python prep-a1/v2venv/bin/python "dbt-core==2.0.0b2" "mashumaro[msgpack]>=3.14"   (SSL_CERT_FILE=/etc/ssl/cert.pem still exported, for the same GitHub fetch as section 1)
 + dbt-core==2.0.0b2
 + mashumaro==3.22
 + msgpack==1.2.2
 + typing-extensions==4.16.0
$ prep-a1/v2venv/bin/dbt --version       -> dbt-core 2.0.0-beta.2
$ cp warehouse/metricmine.duckdb prep-a1/v2smoke.duckdb
$ export MM_WAREHOUSE_PATH="$PWD/prep-a1/v2smoke.duckdb"; export DBT_PROFILES_DIR="$PWD/transform"
$ prep-a1/v2venv/bin/dbt parse --project-dir transform --target local --target-path prep-a1/v2target
  dbt-core 2.0.0-beta.2
  Finished [  0.19s] resolving packages from packages.yml (1 items)
Finished 'parse' successfully for target 'local' [371ms]
$ prep-a1/v2venv/bin/dbt build --project-dir transform --target local --target-path prep-a1/v2target   (first attempt)
==================== Execution Summary =====================
Finished 'build' successfully for target 'local' [2.1s]
Processed: 13 models | 96 tests
Summary: 109 total | 109 success
$ uv run python -m metricmine.export_demo   (the project's 1.12 environment reading the v2-built scratch copy)
view vw_invoice_lines_typed: 44721 rows, digest match (08eca7be30707e2aa0b48c3d19ddeea4)
artifact size: 12857344 bytes
$ git checkout -- demo/demo.duckdb
$ uv run datacontract dbt test contracts/*.odcs.yaml --project-dir transform --target local   (dbt 1.12.3 and datacontract-cli 1.0.12 over the v2-built relations)
🟢 dbt tests passed. Ran 85 tests. Took 0.005838 seconds.
🟢 dbt tests passed. Ran 11 tests. Took 0.005689 seconds.
Tested 3 contract(s): 1 no tests · 2 passed.
$ unset MM_WAREHOUSE_PATH
$ git status --porcelain                 -> M pyproject.toml, M transform/dbt_project.yml, M uv.lock, ?? prep-a1/ (unchanged)
Driver path, measured after the smoke with a dyld trace of a repeat scratch build:
$ DYLD_PRINT_LIBRARIES=1 prep-a1/v2venv/bin/dbt build --project-dir transform --target local --target-path prep-a1/v2target 2>&1 | grep -iE "duckdb|adbc"
dyld[14258]: <EE49FFBF-99C9-3A7E-93B1-5C3409F871C8> /opt/homebrew/Cellar/duckdb/1.5.4/lib/libduckdb.dylib
   The engine loaded the Homebrew DuckDB 1.5.4 library from the system library path. Neither the CDN download nor the ADBC_DRIVER_PATH fallback was exercised on this machine; no install-drivers retry was needed. The sandbox transcript noted the binary's own driver table names duckdb at 1.5.4, and that is the library that executed the SQL here. The scratch copy was written by DuckDB 1.5.4 and read back by the project's pinned duckdb 1.4.3 for the export and the gate-3 tests, both green.

== 7. Read ==
The lock resolves the exact set Amendment N names, 210 packages and 94 lock lines, with dbt-core at 1.12.3 and the parser at 2.0.0b2. Every lane, the build (PASS=109, REUSED=0), the scan pair, gates 1 through 3, the deprecation count, and the D-33 digest match the sandbox record; F-30 holds on this machine as written. The parser gate fell exactly as F-31 records: the delegated parse passes against the live hub, the delegated build fails on all eight contract-enforced models with the same constraint error, and the beta engine builds the project 109 of 109 and reproduces the digest. Two machine-bound differences: the parser sdist's install-time fetch needed SSL_CERT_FILE because this framework CPython carries no CA bundle, which is the install-time source F-30 says a pin amendment must name, seen from the other side; and the beta engine's DuckDB driver came from Homebrew's libduckdb 1.5.4 rather than the CDN, a third driver path the sandbox could not observe. Artifact byte sizes (12070912 and 12857344) differ from the sandbox's, as D-33 expects.
