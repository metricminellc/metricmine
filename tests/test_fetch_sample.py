"""Unit tests for the D-15 fetch script's deterministic serialization.

fmt() is the single source of the sample's byte-stability guarantee, so it
is worth pinning independently of the network fetch. The module is loaded
by path (scripts/ is not a package) via importlib, which also keeps the
import off the top of this file; sys.path juggling would trip ruff E402.
"""

import importlib.util
from datetime import datetime
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fetch_sample.py"
_spec = importlib.util.spec_from_file_location("fetch_sample", _SCRIPT)
fetch_sample = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_sample)

fmt = fetch_sample.fmt


def test_none_becomes_empty_string():
    assert fmt(None) == ""


def test_datetime_uses_fixed_format():
    assert fmt(datetime(2009, 12, 1, 8, 26)) == "2009-12-01 08:26:00"


def test_integer_float_drops_decimal():
    # openpyxl reads whole numbers (e.g. Customer ID) as floats.
    assert fmt(12.0) == "12"


def test_non_integer_float_is_preserved():
    assert fmt(12.5) == "12.5"


def test_text_passes_through():
    assert fmt("ABC") == "ABC"
