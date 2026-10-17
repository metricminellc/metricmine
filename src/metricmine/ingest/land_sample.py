"""Land the committed sample extracts into bronze via PyAirbyte.

Spec: docs/spec/ingestion.md. Governing decisions: D-15 (committed
samples), D-03 (gitignored working warehouse), D-41 (the multi-source
proof: one connector type, many files).

The Airbyte source-file connector reads each committed CSV and
full-refresh replaces its bronze table in the working DuckDB warehouse,
one stream per source, all through the same connector venv. Bronze is
evidence: no renames, no casts, no transforms; _airbyte_* columns land
as-is. Configuration comes from the ingestion block of
config/default.yaml, whose ``sources`` list carries one entry per
committed extract; this script takes no arguments, the same posture as
scripts/fetch_sample.py.

``main`` first installs the temp-file shim (F-67): PyAirbyte 0.53 leaves
its temporary files read-only and then retries their deletion for four
seconds each on Windows, so the landing gives each file its write bit
back before PyAirbyte's cleanup runs. tasks.py's ingest step runs this
module for both ``mm ingest`` and ``mm demo``, so the shim covers both.
"""

from __future__ import annotations

import contextlib
import stat
import sys
from pathlib import Path

import airbyte as ab
import airbyte._connector_base as _ab_connector_base
import airbyte._util.temp_files as _ab_temp_files
import airbyte.sources.base as _ab_sources_base
import yaml
from airbyte.caches import DuckDBCache

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "config" / "default.yaml"

# PyAirbyte 0.53 writes the connector's config, catalog, and state to
# temporary files through ``airbyte._util.temp_files.as_temp_files``, makes
# each one read-only, and on exit retries the unlink five times with a
# one-second sleep between attempts before warning ``Failed to remove
# temporary file``. Windows refuses to delete a read-only file, so every
# temp file there costs four seconds and stays in the temp folder: five
# files per source, 35 per landing, about 140 seconds (F-67). The helper is
# bound by name at import time in each module that calls it, so the landing
# rebinds it in the two modules on its path (check in ``_connector_base``,
# discover and read in ``sources.base``);
# ``destinations.base`` carries the same binding and the landing never
# uses a destination. Each module is imported by alias, because ``main``
# below has a local named ``sources``. A PyAirbyte pin move revisits this
# (the install refuses a module whose binding it does not recognize).
TEMP_FILE_REBIND_TARGETS = (_ab_sources_base, _ab_connector_base)


def writable_before_cleanup(as_temp_files):
    """Wrap PyAirbyte's ``as_temp_files`` so each temporary file gets its
    owner write bit back before PyAirbyte's own cleanup unlinks it.

    The wrapper's ``finally`` runs before the wrapped context manager's,
    so the chmod lands between the caller's block and the unlink loop. On
    POSIX the unlink succeeds either way and the chmod changes nothing
    observable; on Windows it turns a four-second retry loop and a warning
    into one successful delete. A chmod that fails is left to the loop.
    """

    @contextlib.contextmanager
    def writable_temp_files(files_contents):
        with as_temp_files(files_contents) as paths:
            try:
                yield paths
            finally:
                for name in paths:
                    path = Path(name)
                    with contextlib.suppress(OSError):
                        path.chmod(path.stat().st_mode | stat.S_IWUSR)

    writable_temp_files.wraps_as_temp_files = as_temp_files
    return writable_temp_files


def install_temp_file_shim() -> None:
    """Rebind ``as_temp_files`` in every module of TEMP_FILE_REBIND_TARGETS
    to the writable-before-cleanup wrapper (F-67). Idempotent. Refuses a
    module whose binding is not PyAirbyte's own helper, so a pin move that
    changes the binding fails here, loudly, instead of silently restoring
    the Windows cost."""
    original = _ab_temp_files.as_temp_files
    for module in TEMP_FILE_REBIND_TARGETS:
        bound = getattr(module, "as_temp_files", None)
        if getattr(bound, "wraps_as_temp_files", None) is original:
            continue
        if bound is not original:
            raise RuntimeError(
                f"{module.__name__}.as_temp_files is not"
                " airbyte._util.temp_files.as_temp_files; the PyAirbyte pin"
                " moved its binding, so revisit the temp-file shim (F-67)"
            )
        module.as_temp_files = writable_before_cleanup(original)


def build_source_config(cfg: dict, csv_path: Path) -> dict:
    """Build the source-file connector config from one sources entry.

    Config keys verified against connector docs v0.6.0 (spec §2). PyAirbyte
    runs the connector in a local venv, so a plain absolute path is used;
    the Docker-era "/local/" prefix from the platform docs does not apply.
    """
    source_config = {
        "dataset_name": cfg["dataset_name"],
        "format": "csv",
        "url": str(csv_path),
        "provider": {"storage": "local"},
    }
    if cfg.get("reader_options"):
        # JSON string of pandas read_csv options, passed through as-is.
        source_config["reader_options"] = cfg["reader_options"]
    return source_config


def ingestion_sources(cfg: dict) -> list[dict]:
    """The ordered source list of the ingestion block, fail-closed.

    ``sources`` is the form since the multi-source fan-in (D-41); a block
    that still carries the single-source keys (``dataset_name`` and
    ``sample_csv`` at the top level) reads as a one-entry list so a
    pre-fan-in config keeps working. Both forms at once is an error, and
    every entry names a distinct dataset.
    """
    sources = cfg.get("sources")
    legacy = "dataset_name" in cfg or "sample_csv" in cfg
    if sources is not None and legacy:
        raise ValueError(
            "ingestion block names both sources and the single-source keys;"
            " keep the list only"
        )
    if sources is None:
        if not legacy:
            raise ValueError("ingestion block names no sources")
        sources = [
            {
                key: cfg[key]
                for key in ("dataset_name", "sample_csv", "reader_options")
                if key in cfg
            }
        ]
    if not isinstance(sources, list) or not sources:
        raise ValueError("ingestion.sources must be a non-empty list")
    names = [entry["dataset_name"] for entry in sources]
    if len(set(names)) != len(names):
        raise ValueError(f"ingestion.sources dataset names must be unique: {names}")
    return sources


def main() -> int:
    install_temp_file_shim()
    cfg = yaml.safe_load(CONFIG_PATH.read_text())["ingestion"]
    warehouse_path = (REPO_ROOT / cfg["warehouse_path"]).resolve()
    sources = ingestion_sources(cfg)
    csv_paths = {}
    for entry in sources:
        csv_path = (REPO_ROOT / entry["sample_csv"]).resolve()
        if not csv_path.is_file():
            print(
                f"ERROR: sample CSV for {entry['dataset_name']} not found at"
                f" {csv_path}; run its fetch script under scripts/"
            )
            return 1
        csv_paths[entry["dataset_name"]] = csv_path
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    for entry in sources:
        source = ab.get_source(
            "source-file",
            config=build_source_config(entry, csv_paths[entry["dataset_name"]]),
        )
        source.check()
        source.select_all_streams()
        result = source.read(
            cache=DuckDBCache(
                db_path=str(warehouse_path), schema_name=cfg["schema"]
            ),
            write_strategy="replace",
            force_full_refresh=True,
        )
        for name, dataset in result.streams.items():
            counts[name] = len(dataset)

    print(f"landed {counts} into {cfg['schema']} of {warehouse_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
