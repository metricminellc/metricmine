"""Fixtures for the E1T instruments' tests: the pinned served file when it
is present (MM_E1T_PINNED, or e1t/served/demo-v1.3.0.duckdb, or the
clone's demo/demo.duckdb when its sha256 is the key's), and the tiny
synthetic gold warehouse of tests/feedback_fixtures.py."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

E1T = Path(__file__).resolve().parents[1]
REPO = E1T.parent
sys.path.insert(0, str(E1T))
sys.path.insert(0, str(REPO / "tests"))

import key  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pinned_path() -> Path | None:
    env = os.environ.get("MM_E1T_PINNED")
    candidates = [Path(env)] if env else []
    candidates += [E1T / "served" / f"demo-{key.SERVED_RELEASE}.duckdb", REPO / "demo" / "demo.duckdb"]
    for cand in candidates:
        if cand.is_file() and cand.stat().st_size == key.SERVED_BYTES and sha256_file(cand) == key.SERVED_SHA256:
            return cand
    return None


@pytest.fixture(scope="session")
def pinned() -> Path:
    p = pinned_path()
    if p is None:
        pytest.skip("the pinned served file is not present (e1t/fetch_pinned.py places it)")
    return p


@pytest.fixture
def synthetic(tmp_path: Path) -> Path:
    from feedback_fixtures import build_gold

    return build_gold(tmp_path / "synthetic.duckdb")
