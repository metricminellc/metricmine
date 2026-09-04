"""The committed samples honor D-15 as amended (Amendment T, Arc 6).

Keyless, network-free. For every extract directory under data/samples/:
a README that cites the source and states the extract's sha256, and
committed bytes whose digest is the one the README states, so a silent
re-extract cannot land. For every source fetch script under scripts/:
the raw download's sha256 is pinned (a mismatch refuses to extract) and
the per-source budget is at or under the D-15 caps (20 MB for the one
event source, 10 MB for every other). The retail sample predates the
amendment and keeps its own README shape; its bytes are held by its own
fetch script's determinism, so it is exempt from the digest line.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SAMPLES = REPO / "data" / "samples"
SCRIPTS = REPO / "scripts"

EVENT_SOURCE_CAP = 20 * 1024 * 1024
OTHER_SOURCE_CAP = 10 * 1024 * 1024
EVENT_SOURCES = {"bts_ontime"}
PRE_AMENDMENT = {"online_retail_ii"}

SHA256_LINE = re.compile(r"sha256\s+([0-9a-f]{64})")
PINNED = re.compile(r'^RAW_SHA256[^=]*=\s*"([0-9a-f]{64})"', re.M)
PINNED_MAP = re.compile(r'"([A-Z0-9]+)":\s*"([0-9a-f]{64})"')
BUDGET = re.compile(r"^MAX_BYTES\s*=\s*(\d+)\s*\*\s*1024\s*\*\s*1024", re.M)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sample_dirs() -> list[Path]:
    return sorted(p for p in SAMPLES.iterdir() if p.is_dir())


@pytest.mark.parametrize("sample_dir", _sample_dirs(), ids=lambda p: p.name)
def test_every_sample_has_a_readme_that_cites_and_pins(sample_dir: Path) -> None:
    readme = sample_dir / "README.md"
    assert readme.is_file(), f"{sample_dir.name}: no README (D-15)"
    text = readme.read_text(encoding="utf-8")
    assert "License" in text and "Source" in text, f"{sample_dir.name}: cite the source and its license"
    extracts = sorted(p for p in sample_dir.iterdir() if p.suffix == ".csv")
    assert len(extracts) == 1, f"{sample_dir.name}: exactly one committed extract"
    cap = EVENT_SOURCE_CAP if sample_dir.name in EVENT_SOURCES else OTHER_SOURCE_CAP
    assert extracts[0].stat().st_size <= cap, f"{sample_dir.name}: over the D-15 budget"
    if sample_dir.name in PRE_AMENDMENT:
        return
    stated = SHA256_LINE.findall(text)
    assert stated, f"{sample_dir.name}: the README states no sha256"
    assert _sha256(extracts[0]) in stated, (
        f"{sample_dir.name}: the committed extract's sha256 is not the one the README states"
    )


def _source_scripts() -> list[Path]:
    exempt = {"fetch_common.py", "fetch_demo.py", "fetch_sample.py"}
    return sorted(p for p in SCRIPTS.glob("fetch_*.py") if p.name not in exempt)


@pytest.mark.parametrize("script", _source_scripts(), ids=lambda p: p.name)
def test_every_fetch_script_pins_its_raw_bytes_and_its_budget(script: Path) -> None:
    text = script.read_text(encoding="utf-8")
    pinned = PINNED.findall(text) or PINNED_MAP.findall(text)
    assert pinned, f"{script.name}: RAW_SHA256 is not pinned (Amendment T)"
    budget = BUDGET.findall(text)
    assert budget, f"{script.name}: declare MAX_BYTES as <n> * 1024 * 1024"
    cap = EVENT_SOURCE_CAP if "ontime" in script.name else OTHER_SOURCE_CAP
    assert int(budget[0]) * 1024 * 1024 <= cap, f"{script.name}: budget over the D-15 cap"
