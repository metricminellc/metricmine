Arc 1 prep probes, August 28, 2026 - the 1.11.14 lock refresh, the dbt 1.12.3 co-resolution and full gate re-proof, the v2 parser gate, and the dbt Core 2.0.0-beta.2 smoke
Repo head: 0708240924fc2eaa1ca66e6eefe85574aa4af026 (main, the #102 squash)

Environment (the Architect's sandbox, stated because every number below is a measurement, never a claim):
Linux x86_64 container; uv 0.8.17; CPython 3.12.11 (uv-managed); datacontract-cli 1.0.12 as an isolated uv tool with the [duckdb] extra; dbt_utils 1.3.3 vendored by git clone of its tag (hub.getdbt.com is unreachable from this sandbox; the Mac and CI use dbt deps); AIRBYTE_OFFLINE_MODE=1 for every ingest; no API key present and none needed. Byte sizes and wall times are per-machine reports; the D-33 digest is the gate.

== 0. Head reproduction at 0708240 (every lane at its recorded value) ==
$ uv sync --frozen                       -> dbt-core 1.11.12, dbt-duckdb 1.10.1, dbt-adapters 1.24.4, dbt-common 1.38.0, duckdb 1.4.3, airbyte 0.53.2, anthropic 1.0.0, mcp 1.29.0
$ uv run ruff check .                    -> All checks passed!
$ uv run pytest -m "not local" -q        -> 411 passed, 52 deselected, 13 warnings in 29.06s
$ uv run pytest tests/agents -q          -> 240 passed in 13.90s
$ uv run pytest tests/agents -m local -q -> 8 passed, 232 deselected in 8.73s
$ make ingest                            -> landed {'online_retail_ii': 45228} into bronze of warehouse/metricmine.duckdb
$ uv run dbt build --project-dir transform --profiles-dir transform --target local
                                         -> Finished running 12 table models, 96 data tests, 1 view model in 0 hours 0 minutes and 6.58 seconds
                                         -> Done. PASS=109 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=109
$ uv run pytest tests/test_adoption_scan.py -q -> 11 passed in 1.98s
$ make scan (twice)                      -> models scanned: 13; skip_engine_owned 12; in_sync 1; The queue: Empty. Every model is in sync or skipped by decision.
                                         -> plan_hash sha256:968c5994f7a48bf0540332291016eee0d9bbfc406c07515a0941c873f6f31670 on both runs
$ datacontract lint contracts/*.odcs.yaml (each) -> 3 x "data contract is valid. Run 1 checks."
$ DBT_PROFILES_DIR=<abs>/transform MM_WAREHOUSE_PATH=<abs>/warehouse/metricmine.duckdb uv run datacontract dbt sync contracts/*.odcs.yaml --project-dir transform --target local
                                         -> gold_invoice_lines_mapping: Synced 0 models: updated 0 YAML files. gold_unified_event_star: Synced 10 models: updated 0 YAML files. silver_invoice_lines: Synced 1 model: updated 0 YAML files. Tree clean after sync.
$ ... uv run datacontract dbt test contracts/*.odcs.yaml --project-dir transform --target local
                                         -> gold_unified_event_star@1.2.0: dbt tests passed. Ran 85 tests. silver_invoice_lines@1.1.1: dbt tests passed. Ran 11 tests. gold_invoice_lines_mapping@1.1.0: no tests. Tested 3 contract(s): 1 no tests, 2 passed.
$ make export-demo                       -> view vw_invoice_lines_typed: 44721 rows, digest match (08eca7be30707e2aa0b48c3d19ddeea4); artifact size: 12857344 bytes; demo/demo.duckdb restored with git checkout.

== 1. Release facts (verified by search and by the package index on August 28, 2026) ==
dbt-core on PyPI: 1.12.3 (Aug 21, 2026) is the latest; 1.12.2 and 1.12.1 (Aug 12); 1.12.0 (Jul 16, 2026, a full release on its GitHub tag, not a pre-release); 1.11.14 (Aug 20); 1.11.13 (Aug 12); 1.11.12 (Jul 1). Pre-releases: 2.0.0b2 (Aug 18), 2.0.0b1 (Aug 10), 2.0.0a5 (Jul 20).
dbt Core version support (docs.getdbt.com/docs/dbt-versions/core): 1.12 released Jul 16, 2026, active support to July 15, 2027; 1.11 released Dec 19, 2025, critical support to Dec 18, 2026; 2.0 in beta, dates TBD.
dbt-core 1.12.3 requires: dbt-adapters>=1.24.5,<2.0; dbt-common>=1.37.5,<2.0; dbt-core-experimental-parser>=2.0.0b1,<3; metricflow>=0.211.0,<1.0; opentelemetry-api>=1.26,<2.0; python>=3.10. dbt-semantic-interfaces is no longer a direct dependency.
dbt-core 1.11.14 requires: dbt-adapters>=1.15.5,<2.0; dbt-common>=1.37.3,<2.0; python>=3.10.
dbt-duckdb on PyPI: 1.11.0 (Aug 7, 2026) is the latest; 1.10.1 (Feb 17, 2026). 1.11.0 declares dbt-core>=1.8.0, dbt-adapters>=1,<2, dbt-common>=1,<2, duckdb>=1.0.0, python>=3.10 (no upper cap on dbt-core). Its tag 1.11.0 (commit 161970c, Aug 6, 2026) pins dbt-core>=1.12.0,<2 in dev-requirements.txt, so the 1.11.0 line is developed and tested against dbt-core 1.12. Its macros carry no materialized_view materialization (grep of the tag), so CLAUDE.md rule 7 stands.
datacontract-cli on PyPI: 1.1.2 (Aug 26, 2026) is the latest; the pinned 1.0.12 (Jul 10, 2026) stands (D-06 unchanged). The 1.0.12 tool environment carries no dbt-core at all: `datacontract dbt test` shells out to whatever `dbt` is on PATH (datacontract/integration/dbt_sync.py, run_dbt_test with `dbt test --project-dir ... --select config.meta.<ns>.include_in_tests:true ...`) and reads target/run_results.json, so the gate-3 path under 1.12 is the project's own dbt (F-04, F-09 unchanged).
dbt-core-experimental-parser on PyPI: 2.0.0b2 (Aug 18, 2026), source distribution only (4,472 bytes), python>=3.9, no declared dependencies. Its PEP 517 backend (_dbt_sa_build) downloads the platform wheel from https://github.com/dbt-labs/dbt-core/releases/download/v2.0.0-beta.2/ at build time and verifies it against the sha256 embedded in the sdist's assets.json; wheels exist for macosx_11_0_arm64, macosx_10_12_x86_64, manylinux_2_28_x86_64, manylinux_2_28_aarch64, win_amd64. The manylinux x86_64 wheel is 49,898,627 bytes and installs a 149,714,784-byte binary at .venv/bin/dbt-core-experimental-parser.
dbt-core 2.0.0b2 on PyPI: the same download-at-install shape (sdist 4,455 bytes; the Linux x86_64 wheel is 61,275,997 bytes). dbt Labs' v2 announcement (docs/roadmap/2026-06-announcing-v2.md) and the 1.12 GA post describe --use-v2-parser as the opt-in Rust parser inside 1.12 and v2 as the Rust rewrite with no GA date. The 1.12 upgrade guide states the v2 parser is beta and its manifest may differ from the Python parser's in edge cases that affect downstream behavior.

== 2. The 1.11.x lock refresh (branch probe/lock-refresh) ==
$ uv lock --upgrade-package dbt-core     -> Resolved 207 packages in 2.05s. Updated dbt-core v1.11.12 -> v1.11.14
$ git diff --stat                        -> uv.lock | 8 +++++--- (1 file changed, 5 insertions(+), 3 deletions(-))
   The eight lines: the dbt-core version, sdist, and wheel entries (1.11.12 -> 1.11.14), plus two greenlet 3.5.3 wheel entries (manylinux s390x and riscv64) the index now lists. No other package moves.
$ uv sync --frozen                       -> - dbt-core==1.11.12 + dbt-core==1.11.14
$ uv run dbt --version                   -> installed: 1.11.14; latest: 1.12.3
$ uv run ruff check .                    -> All checks passed!
$ uv run pytest -m "not local" -q        -> 411 passed, 52 deselected, 13 warnings in 18.13s
$ uv run pytest tests/agents -q          -> 240 passed in 13.63s
$ uv run pytest tests/agents -m local -q -> 8 passed, 232 deselected in 7.99s
$ make ingest; dbt build                 -> landed 45228; Done. PASS=109 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=109 (5.06s)
$ scan module; make scan (twice)         -> 11 passed; 13 models, 12 skip_engine_owned, 1 in_sync, queue Empty; plan_hash sha256:968c5994... identical to head (same repo head line)
$ gates 1 and 3 (F-09 exports)           -> 3 valid; sync 0/10/1 models, 0 YAML updated; test 85 + 11 passed, Tested 3 contract(s): 1 no tests, 2 passed
$ make export-demo                       -> digest match (08eca7be30707e2aa0b48c3d19ddeea4); artifact size: 12333056 bytes (per-machine); artifact restored

== 3. The dbt 1.12 co-resolution (branch probe/dbt-1.12, from the refreshed lock; the P1 pattern, resolve without syncing) ==
$ uv add --no-sync "dbt-core>=1.12,<1.13" "dbt-duckdb>=1.11,<1.12"
                                         -> Resolved 210 packages in 300ms (regenerated once more later: identical package set, 94 lock lines, 65 insertions, 35 deletions)
   pyproject.toml: dbt-core>=1.11,<1.12 -> >=1.12,<1.13; dbt-duckdb>=1.10,<1.11 -> >=1.11,<1.12
   uv.lock moves: dbt-core 1.11.14 -> 1.12.3; dbt-duckdb 1.10.1 -> 1.11.0; dbt-adapters 1.24.4 -> 1.24.5; NEW dbt-core-experimental-parser 2.0.0b2 (sdist only), metricflow 0.212.0, sqlglot 30.17.0, tabulate 0.10.0; REMOVED dbt-semantic-interfaces 0.9.0; airbyte 0.53.2, anthropic 1.0.0, mcp 1.29.0, duckdb 1.4.3, dbt-common 1.38.0 unchanged.
$ uv sync --frozen                       -> builds the parser sdist by downloading its wheel from GitHub releases (hash-verified), installs dbt-core 1.12.3, dbt-duckdb 1.11.0, dbt-adapters 1.24.5, dbt-core-experimental-parser 2.0.0b2, metricflow 0.212.0, sqlglot, tabulate; removes dbt-semantic-interfaces. Cold sync with an empty uv cache: 2.8 s here (the 49.9 MB wheel download is the variable part on another machine).
$ uv run dbt --version                   -> installed: 1.12.3 (Up to date!); Plugins: duckdb: 1.11.0

== 4. The require-dbt-version mirror refuses first (measured, then edited) ==
$ uv run dbt build --project-dir transform --profiles-dir transform --target local   (dbt_project.yml still at [">=1.11.0", "<1.12.0"])
   Runtime Error
     This version of dbt is not supported with the 'metricmine' package.
       Installed version of dbt: =1.12.3
       Required version of dbt for 'metricmine': ['>=1.11.0', '<1.12.0']
     Check for a different version of the 'metricmine' package, or run dbt again with --no-version-check
   Error encountered in transform/dbt_project.yml
Edit: transform/dbt_project.yml require-dbt-version: [">=1.11.0", "<1.12.0"] -> [">=1.12.0", "<1.13.0"] (the file's own comment calls it the mirror of the D-05 pin).

== 5. The full gate re-proof at dbt-core 1.12.3, dbt-duckdb 1.11.0 (single pass on the committed probe branch) ==
$ uv run ruff check .                    -> All checks passed!
$ uv run pytest -m "not local" -q        -> 411 passed, 52 deselected, 13 warnings in 26.37s
$ uv run pytest tests/agents -q          -> 240 passed in 14.16s
$ uv run pytest tests/agents -m local -q -> 8 passed, 232 deselected in 8.38s
$ make ingest                            -> landed {'online_retail_ii': 45228}
$ uv run dbt build --project-dir transform --profiles-dir transform --target local
                                         -> Running with dbt=1.12.3; Registered adapter: duckdb=1.11.0; Found 13 models, 96 data tests, 1 source, 617 macros
                                         -> Done. PASS=109 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=109
   (the Done line gains a REUSED=0 field at 1.12; the first run after the version change logs "Unable to do partial parsing because of a version mismatch", informational)
$ uv run pytest tests/test_adoption_scan.py -q -> 11 passed in 1.85s
$ make scan (twice)                      -> 13 models; skip_engine_owned 12; in_sync 1; queue Empty; plan_hash identical across the pair (sha256:e714b7e9... at the probe head; the plan body diffed against the head-of-main plan is identical apart from the "repo head" line, so the hash moves with the commit and not with dbt)
$ datacontract lint (each contract)      -> 3 x valid
$ gate 3 sync (F-09 exports)             -> Synced 0 / 10 / 1 models, updated 0 YAML files; tree clean after sync
$ gate 3 test                            -> dbt tests passed. Ran 85 tests. / dbt tests passed. Ran 11 tests. / Tested 3 contract(s): 1 no tests, 2 passed.
$ uv run dbt parse --project-dir transform --show-all-deprecations -> 0 deprecation lines
$ make export-demo                       -> digest match (08eca7be30707e2aa0b48c3d19ddeea4); artifact size: 12333056 bytes; artifact restored
Repo-wide grep for the Done line pattern: only evidence transcripts quote it; no test, script, or Makefile target couples to its shape.

== 6. The v2 parser gate at 1.12.3 (dbt-core-experimental-parser 2.0.0b2, the flag --use-v2-parser) ==
First attempt, packages.yml as committed:
$ uv run dbt parse --use-v2-parser --project-dir transform
   Delegating parse to v2 parser: dbt-core-experimental-parser parse
   dbt-core 2.0.0-beta.2 ... Failed [ 6.37s] resolving packages from packages.yml (error: Failed to get index from https://hub.getdbt.com/api/v1/index.json; status: Request failed after 3 retries)
   v2 parser failed after 6.81s (FusionParserError, exit_code=1)
   The delegated parser resolves packages.yml itself and consults the hub even with dbt_packages/ vendored; the hub is unreachable from this sandbox only. For the measurement below, packages.yml pointed at a local git clone of dbt-utils at tag 1.3.3 and package-lock.yml was set aside; both restored afterwards. The Mac and CI reach the hub and need no such step.
Second attempt, local package source:
$ uv run dbt parse --use-v2-parser --project-dir transform
   [0m16:51:59  Running with dbt=1.12.3
   [0m16:52:00  Delegating parse to v2 parser: dbt-core-experimental-parser parse
     dbt-core 2.0.0-beta.2
      Loading profiles.yml
      Started resolving packages from packages.yml
     Finished [  0.08s] resolving packages from packages.yml (1 items)
   ==================== Execution Summary =====================
   Finished 'parse' successfully for target 'local' [834ms]
   [0m16:52:01  v2 parser completed in 1.04s
   exit 0; no warnings. target/manifest.json written with dbt_version 2.0.0-beta.2, schema v12, 109 nodes, 1 source, 638 macros.
$ uv run dbt build --use-v2-parser --project-dir transform --target local
   Delegating parse to v2 parser ... v2 parser completed in 0.89s; Found 13 models, 96 data tests, 1 source, 613 macros
   1 of 109 ERROR creating sql table model gold.context_registry
   ... every contract-enforced model errors the same way (context_registry, dim_invoice_lines_columns, dim_run_columns, dim_run_values, dim_source_columns, dim_source_values, dim_timeframe_columns, silver_invoice_lines):
     Runtime Error in model silver_invoice_lines (models/silver/silver_invoice_lines.sql)
       Could not parse constraint: {'type': 'not_null', 'warn_unenforced': None, 'warn_unsupported': None, 'to_columns': []}
   Done. PASS=2 WARN=0 ERROR=8 SKIP=99 NO-OP=0 REUSED=0 TOTAL=109; exit 1
   Mechanism: the delegated manifest serializes every column constraint with warn_unenforced and warn_unsupported as null (read back from target/manifest.json: {'type': 'not_null', 'expression': None, 'name': None, 'to': None, 'to_columns': [], 'warn_unsupported': None, 'warn_unenforced': None}); dbt-adapters' constraint parser (dbt/adapters/base/impl.py, "Could not parse constraint") requires booleans. Every contracted MetricMine model carries not_null constraints (rule 5), so the delegated build cannot pass at this pairing. dbt-core issue #16010 (opened Aug 20, 2026, closed, fixed on the 1.latest branch) records the same family: the v2-parser path copies the parser's manifest instead of re-serializing it.

== 7. The dbt Core 2.0.0-beta.2 smoke (isolated venv, never the project environment) ==
$ uv venv --python 3.12 v2venv; uv pip install --python v2venv/bin/python "dbt-core==2.0.0b2"
                                         -> Building dbt-core==2.0.0b2 ... Installed 1 package (the sdist backend downloads dbt_core-2.0.0b2-cp311-abi3-manylinux_2_28_x86_64.whl from GitHub releases; the installed Python surface is a 185,370,000-byte dbt/_core.abi3.so)
$ v2venv/bin/dbt --version               -> ModuleNotFoundError: No module named 'msgpack' (dbt/runner.py imports msgpack; the wheel's METADATA declares Requires-Dist: mashumaro[msgpack]>=3.14 but the PyPI sdist declares no dependencies, so the installer never sees it)
$ uv pip install --python v2venv/bin/python "mashumaro[msgpack]>=3.14" -> mashumaro 3.22, msgpack 1.2.2, typing-extensions 4.16.0
$ v2venv/bin/dbt --version               -> dbt-core 2.0.0-beta.2
$ MM_WAREHOUSE_PATH=/tmp/v2smoke.duckdb (a scratch copy of the built warehouse) DBT_PROFILES_DIR=<abs>/transform v2venv/bin/dbt parse --project-dir transform --target local --target-path /tmp/v2target
                                         -> Finished 'parse' successfully for target 'local' [711ms]
$ ... v2venv/bin/dbt build --project-dir transform --target local --target-path /tmp/v2target   (first attempt)
   [error] [DbDriverFailed (dbt1308)]: Failed to create schema 'gold' in database 'v2smoke' in remote for model.metricmine.vw_invoice_lines_typed: Failed to load `duckdb` driver from name, then failed to load it from the CDN.
   First error: NotFound: Driver not found: duckdb ... Second error: IO: HTTP error: CONNECT proxy failed: proxy server responded 403/403
   The v2 engine loads warehouse drivers through the ADBC driver manager and fetches them from public.cdn.getdbt.com on first use (`dbt system install-drivers` pre-caches them and fails the same way here); the sandbox proxy refuses that host. The binary's own driver table names duckdb at 1.5.4, unverified as behavior. The Mac reaches the CDN; the smoke there stays on a scratch copy of the warehouse for that reason.
$ ADBC_DRIVER_PATH=/tmp/adbc_drivers (duckdb.toml: entrypoint duckdb_adbc_init, linux_amd64 = the pinned duckdb 1.4.3 wheel's _duckdb.cpython-312-x86_64-linux-gnu.so, which exports the ADBC surface and is what adbc_driver_duckdb loads) ... v2venv/bin/dbt build --project-dir transform --target local --target-path /tmp/v2target   (second attempt)
   ==================== Execution Summary =====================
   Finished 'build' successfully for target 'local' [3.8s]
   Processed: 13 models | 96 tests
   Summary: 109 total | 109 success
$ MM_WAREHOUSE_PATH=/tmp/v2smoke.duckdb uv run python -m metricmine.export_demo   (the project's 1.12 environment reading the v2-built scratch warehouse)
                                         -> view vw_invoice_lines_typed: 44721 rows, digest match (08eca7be30707e2aa0b48c3d19ddeea4); demo/demo.duckdb restored with git checkout
$ MM_WAREHOUSE_PATH=/tmp/v2smoke.duckdb ... uv run datacontract dbt test contracts/*.odcs.yaml --project-dir transform --target local   (dbt 1.12.3 and datacontract-cli 1.0.12 over the v2-built relations)
                                         -> dbt tests passed. Ran 85 tests. / Ran 11 tests. / Tested 3 contract(s): 1 no tests, 2 passed.
Not claimed: the adoption scan is repo-anchored to warehouse/metricmine.duckdb and did not read the v2 scratch copy; the require-dbt-version range [">=1.12.0", "<1.13.0"] was accepted by both the delegated parser and the 2.0.0-beta.2 engine (observed, cause not investigated).

== 8. What the probes settle ==
1. dbt 1.12 is GA (Jul 16, 2026) at 1.12.3; dbt-duckdb 1.11.0 is its adapter line; both co-resolve with every other pin untouched; datacontract-cli 1.0.12 is unaffected on the gate-3 path. The full gate re-proof at 1.12.3 lands every lane, gate, and the D-33 digest at its head value with zero deprecations.
2. The 1.12 line adds a dependency surface the register must name: dbt-core-experimental-parser (a pre-release Rust binary, pinned by the lock to its sdist hash and by that sdist to its wheel sha256, fetched from GitHub releases at install time) and metricflow.
3. The --use-v2-parser gate is a parse-only probe for this project: parse passes clean; the delegated build fails on every contract-enforced model at parser 2.0.0b2 with core 1.12.3.
4. dbt Core 2.0.0-beta.2 parses and builds the emitted project unchanged (109 of 109) and its warehouse reproduces the D-33 digest, measured with the pinned duckdb 1.4.3 as the ADBC driver; the beta's install needs a hand-added mashumaro[msgpack] and its default driver path needs the CDN. The v2 deferral (D-05, D-06) stands, now demonstrated rather than assumed.
