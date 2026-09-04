"""CI-lane tests for the demo digest manifest and the asset fetch path.

D-03 and D-33 as amended by Amendment S (Arc 6): the demo artifact is a
release asset; `demo/demo.digest.json` is the committed statement of its
content and its bytes. These tests need no warehouse: a tiny gold-shaped
DuckDB file stands in for the artifact, the manifest is built from it,
and the fetch script is driven over a file:// URL so the download,
sha256, size, and content checks run without the network.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import duckdb
import pytest

from metricmine.export_demo import (
    DEFAULT_MANIFEST,
    build_manifest,
    compare_content,
    content_manifest,
    file_sha256,
    read_manifest,
    write_manifest,
)

REPO = Path(__file__).resolve().parents[1]


def _load_fetch_demo():
    """scripts/ is not a package; load the fetch script by path."""
    spec = importlib.util.spec_from_file_location(
        "fetch_demo", REPO / "scripts" / "fetch_demo.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch_demo = _load_fetch_demo()


def _tiny_gold(path: Path, rows: int = 3, registry: bool = False, context: str = "{}") -> Path:
    con = duckdb.connect(str(path))
    try:
        con.execute("create schema gold")
        con.execute(
            "create table gold.fact_probe_values as"
            f" select i as fact_hash_id, i * 2 as v from range({rows}) t(i)"
        )
        con.execute(
            "create view gold.vw_probe_typed as"
            " select fact_hash_id, v from gold.fact_probe_values"
        )
        if registry:
            # The registry's shape (D-30): five deterministic columns plus
            # the loaded_at build stamp the digest must never see (F-39).
            con.execute(
                "create table gold.context_registry as select 'k1' as schema_key,"
                " 'probe' as entity_group, 'gold_probe_mapping' as contract_name,"
                f" '1.0.0' as contract_version, '{context}' as compiled_context,"
                " current_localtimestamp() as loaded_at"
            )
        con.execute("checkpoint")
    finally:
        con.close()
    return path


def test_content_manifest_measures_tables_and_views(tmp_path) -> None:
    artifact = _tiny_gold(tmp_path / "demo.duckdb")
    content = content_manifest(artifact)
    assert content["tables"] == {"fact_probe_values": {"rows": 3}}
    assert content["views"]["vw_probe_typed"]["rows"] == 3
    assert len(content["views"]["vw_probe_typed"]["digest"]) == 32
    assert content["registry"] is None  # no registry in the probe file


def test_registry_digest_sees_content_and_never_the_build_stamp(tmp_path) -> None:
    """Equal row counts, different compiled context: the manifest gate
    must notice (the registry is the address of meaning); two builds of
    the same content with different loaded_at stamps must agree."""
    first = _tiny_gold(tmp_path / "first.duckdb", registry=True, context='{"a": 1}')
    again = _tiny_gold(tmp_path / "again.duckdb", registry=True, context='{"a": 1}')
    changed = _tiny_gold(tmp_path / "changed.duckdb", registry=True, context='{"a": 2}')
    one, two, three = (content_manifest(p)["registry"] for p in (first, again, changed))
    assert one["rows"] == two["rows"] == three["rows"] == 1
    assert one == two
    assert one["digest"] != three["digest"]
    manifest = build_manifest(first, None)
    assert compare_content(again, manifest) == []
    problems = compare_content(changed, manifest)
    assert len(problems) == 1 and problems[0].startswith("registry:")


def test_manifest_round_trips_and_pins_the_artifact(tmp_path) -> None:
    artifact = _tiny_gold(tmp_path / "demo.duckdb")
    manifest = build_manifest(artifact, "v9.9.9")
    assert manifest["artifact"] == {
        "name": "demo.duckdb",
        "release": "v9.9.9",
        "sha256": file_sha256(artifact),
        "bytes": artifact.stat().st_size,
    }
    out = tmp_path / "demo.digest.json"
    write_manifest(manifest, out)
    assert read_manifest(out) == manifest
    assert out.read_text(encoding="utf-8").endswith("}\n")


def test_compare_content_names_every_difference(tmp_path) -> None:
    artifact = _tiny_gold(tmp_path / "demo.duckdb")
    manifest = build_manifest(artifact, None)
    assert compare_content(artifact, manifest) == []
    other = _tiny_gold(tmp_path / "other.duckdb", rows=4)
    problems = compare_content(other, manifest)
    assert any(p.startswith("table fact_probe_values: 4 rows") for p in problems)
    assert any(p.startswith("view vw_probe_typed: 4 rows") for p in problems)


def test_committed_manifest_is_well_formed() -> None:
    """The committed manifest names the artifact, its content, and the
    schema version; its release is a tag name or null (unpublished)."""
    manifest = read_manifest(DEFAULT_MANIFEST)
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["artifact"]["name"] == "demo.duckdb"
    assert manifest["artifact"]["release"] is None or manifest["artifact"][
        "release"
    ].startswith("v")
    assert len(manifest["artifact"]["sha256"]) == 64
    assert manifest["content"]["tables"] and manifest["content"]["views"]
    assert "context_registry" in manifest["content"]["tables"]
    assert len(manifest["content"]["registry"]["digest"]) == 32
    assert manifest["content"]["registry"]["rows"] > 0


def test_fetch_verifies_bytes_and_content_over_a_file_url(tmp_path, monkeypatch, capsys) -> None:
    published = _tiny_gold(tmp_path / "published.duckdb")
    manifest = build_manifest(published, "v9.9.9")
    manifest_path = tmp_path / "demo.digest.json"
    write_manifest(manifest, manifest_path)
    dest = tmp_path / "demo" / "demo.duckdb"
    monkeypatch.setattr(fetch_demo, "DEFAULT_MANIFEST", manifest_path)
    monkeypatch.setattr(fetch_demo, "DEFAULT_DEST", dest)
    monkeypatch.setattr(fetch_demo, "asset_url", lambda release, name: published.as_uri())
    assert fetch_demo.main() == 0
    assert file_sha256(dest) == manifest["artifact"]["sha256"]
    out = capsys.readouterr().out
    assert "verified: 1 tables and 1 views match the manifest (release v9.9.9)" in out
    # A second run finds the file already matching and does not download.
    assert fetch_demo.main() == 0
    assert "already matches the manifest" in capsys.readouterr().out


def test_fetch_refuses_a_mismatched_asset(tmp_path, monkeypatch, capsys) -> None:
    published = _tiny_gold(tmp_path / "published.duckdb")
    tampered = _tiny_gold(tmp_path / "tampered.duckdb", rows=4)
    manifest = build_manifest(published, "v9.9.9")
    manifest_path = tmp_path / "demo.digest.json"
    write_manifest(manifest, manifest_path)
    dest = tmp_path / "demo" / "demo.duckdb"
    monkeypatch.setattr(fetch_demo, "DEFAULT_MANIFEST", manifest_path)
    monkeypatch.setattr(fetch_demo, "DEFAULT_DEST", dest)
    monkeypatch.setattr(fetch_demo, "asset_url", lambda release, name: tampered.as_uri())
    assert fetch_demo.main() == 1
    assert not dest.exists(), "nothing is kept from a mismatched download"
    assert "does not match the manifest" in capsys.readouterr().out


def test_fetch_declines_an_unpublished_tree(tmp_path, monkeypatch, capsys) -> None:
    published = _tiny_gold(tmp_path / "published.duckdb")
    manifest_path = tmp_path / "demo.digest.json"
    write_manifest(build_manifest(published, None), manifest_path)
    monkeypatch.setattr(fetch_demo, "DEFAULT_MANIFEST", manifest_path)
    assert fetch_demo.main() == 2
    assert "no published demo artifact" in capsys.readouterr().out


@pytest.mark.parametrize("field", ["artifact", "content", "schema_version"])
def test_manifest_fields_are_present(field) -> None:
    assert field in json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
