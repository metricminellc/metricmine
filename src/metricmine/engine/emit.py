"""Emission entry point: ``uv run python -m metricmine.engine.emit``.

Config-driven from the engine: block of config/default.yaml, no CLI
arguments (the ingest and profile posture). ``build_emission_set`` is the
pure surface the unit tests pin: contracts in, the full emission set out,
no writes. ``main`` adds the write discipline (spec §5): drift-check
before writing, write-if-changed per file with temp-then-rename, manifest
last, nothing written on any failure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

from metricmine.engine.emitters import (
    StarEmission,
    emit_extended_models,
    emit_models,
    registry_declared,
)
from metricmine.engine.manifest import (
    MANIFEST_NAME,
    build_manifest,
    drifted_files,
    read_manifest,
    serialize_manifest,
)
from metricmine.engine.reader import (
    EngineContractError,
    load_compiled_context,
    load_inputs,
    validate_inputs,
)

MARTS_MODES = ("table", "view", "both")
MATERIALIZATION_MODES = ("table", "incremental")

REPO_ROOT = Path(__file__).resolve().parents[3]


def build_emission_set(repo_root: Path) -> dict[str, str]:
    """The full emission set, keyed by bare filename. Pure; no writes."""
    inputs = load_inputs(repo_root)
    validate_inputs(inputs)
    cfg = _config(repo_root)
    # Materialization for the engine-emitted models (D-38): `table` is the
    # committed default (the keyless demo path); `incremental` arms the
    # emitted is_incremental() blocks. A missing key reads as the default
    # and an unknown value fails closed before anything emits.
    materialization = cfg.get("materialization", "table")
    if materialization not in MATERIALIZATION_MODES:
        raise EngineContractError(
            "engine.materialization must be one of"
            f" {MATERIALIZATION_MODES}, not {materialization!r}"
        )
    # One StarEmission over every mapping contract (D-29 as amended): the
    # per-category sets plus the star-global objects, in category order.
    star = StarEmission(inputs.mappings, inputs.star, materialization)
    files = emit_models(star)
    # Extended-star activation (spec §5): the registry and the typed
    # projection join the set only once the gold contract declares
    # context_registry; the star set alone emits before the amendment.
    extended = registry_declared(inputs.star)
    if extended:
        # The typed surface follows engine.marts (D-36): the materialized
        # mart by default, the view kept beside it; a missing key reads as
        # the default and an unknown value fails closed before anything
        # emits.
        marts = cfg.get("marts", "both")
        if marts not in MARTS_MODES:
            raise EngineContractError(
                f"engine.marts must be one of {MARTS_MODES}, not {marts!r}"
            )
        context_version, compiled = load_compiled_context(repo_root)
        files.update(emit_extended_models(star, compiled, marts))
    manifest = build_manifest(
        files, star.mappings, inputs.star, cfg["output_dir"]
    )
    if extended:
        manifest["sources"]["compiled_context"] = {"version": context_version}
    files[MANIFEST_NAME] = serialize_manifest(manifest)
    return files


def _config(repo_root: Path) -> dict:
    config_path = Path(repo_root) / "config" / "default.yaml"
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))["engine"]


def _replace_bytes(path: Path, data: bytes) -> None:
    # Temp-then-rename in the same directory (the established writer
    # discipline): a crash mid-write leaves a stray .tmp, never a
    # truncated emitted file.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def main() -> int:
    try:
        files = build_emission_set(REPO_ROOT)
    except Exception as exc:  # fail-closed: nothing written on any failure
        print(f"ERROR: {exc}")
        return 1

    cfg = _config(REPO_ROOT)
    output_path = REPO_ROOT / cfg["output_dir"]
    drifted = drifted_files(REPO_ROOT, read_manifest(output_path))
    if drifted:
        print(
            "ERROR: refusing to overwrite human-owned files whose bytes"
            " diverged from the ownership-manifest baseline (rule 8):"
        )
        for rel_path in drifted:
            print(f"  {rel_path}")
        print("Nothing written.")
        return 1

    output_path.mkdir(parents=True, exist_ok=True)
    landed = unchanged = 0
    # Manifest last: every content file lands before the manifest that
    # attests to it.
    ordered = sorted(files, key=lambda name: name == MANIFEST_NAME)
    for name in ordered:
        target = output_path / name
        data = files[name].encode("utf-8")
        if target.is_file() and target.read_bytes() == data:
            unchanged += 1
            continue
        _replace_bytes(target, data)
        landed += 1
    print(
        f"Emission complete: {landed} file(s) landed,"
        f" {unchanged} unchanged, {len(files)} total."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
