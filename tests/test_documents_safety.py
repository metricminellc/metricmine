"""The extractors meet untrusted input safely (D-43), on CPython 3.12's own
zipfile and xml.etree: entity expansion, an external entity, an oversized
part, a zip bomb by ratio, deep nesting, a relationship that escapes the
package, an encrypted member, a corrupt or missing part, binary and
non-UTF-8 text. Every case is a RefusedPackage with a reason, never a
crash or a hang; the states module turns it into `refused_package`.

Every package here is built by code. Keyless, no network.
"""

from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

import pytest

from metricmine.documents.extract import MAX_PART_BYTES, RefusedPackage, extract_bytes
from metricmine.documents.register import Register
from metricmine.documents.states import derive
from documents_fixtures import build_docx, build_pptx, write_zip

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _refused(raw: bytes, fmt: str) -> str:
    started = time.monotonic()
    with pytest.raises(RefusedPackage) as info:
        extract_bytes(raw, fmt, "untrusted")
    assert time.monotonic() - started < 5.0
    return str(info.value)


def test_entity_expansion_is_refused_before_parsing() -> None:
    laughs = (
        '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">'
        '<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">'
        '<!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">]>'
        f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>&lol4;</w:t></w:r></w:p></w:body></w:document>'
    )
    reason = _refused(build_docx(extra_members={"word/document.xml": laughs}), "docx")
    assert "DOCTYPE or an entity" in reason


def test_an_external_entity_is_refused() -> None:
    xxe = (
        '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY xxe SYSTEM "file:///etc/hostname">]>'
        f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>&xxe;</w:t></w:r></w:p></w:body></w:document>'
    )
    assert "DOCTYPE or an entity" in _refused(build_docx(extra_members={"word/document.xml": xxe}), "docx")


def test_an_oversized_part_is_refused_by_its_declared_size() -> None:
    big = b"<a>" + b"x" * (MAX_PART_BYTES + 1) + b"</a>"
    reason = _refused(build_docx(extra_members={"word/document.xml": big}), "docx")
    assert "over the" in reason and "byte limit" in reason


def test_a_zip_bomb_by_ratio_is_refused() -> None:
    # 8 MiB of one byte compresses far past 100 to 1; the part is under the
    # size limit, so the ratio is the check that catches it.
    zeros = b"<a>" + b"\x20" * (8 * 1024 * 1024) + b"</a>"
    reason = _refused(build_docx(extra_members={"word/document.xml": zeros}), "docx")
    assert "compresses more than 100 to 1" in reason


def test_deep_nesting_is_refused_at_the_depth_cap() -> None:
    # Distinct attribute values keep the part under the compression ratio, so
    # the depth cap is the check that fires, not the ratio.
    depth = 5000
    opens = "".join(f'<w:p w:rsidR="{i:08x}{(i * 2654435761) % 2**32:08x}">' for i in range(depth))
    nested = f'<w:document xmlns:w="{W}"><w:body>' + opens + "</w:p>" * depth + "</w:body></w:document>"
    assert "nests deeper than 1000" in _refused(build_docx(extra_members={"word/document.xml": nested}), "docx")


def test_a_relationship_target_that_escapes_the_package_is_refused() -> None:
    raw = build_pptx([{"text": "One.", "notes": "n"}], notes_target_override="../../../etc/passwd")
    assert "escapes the package" in _refused(raw, "pptx")


def test_an_absolute_relationship_target_stays_inside_the_package() -> None:
    raw = build_pptx([{"text": "One.", "notes": "Absolute notes."}], notes_target_override="/ppt/notesSlides/notesSlide1.xml")
    e = extract_bytes(raw, "pptx")
    assert e.contains("Absolute notes.")


def test_an_encrypted_member_is_refused_not_crashed() -> None:
    raw = bytearray(build_docx(body=["Secret."]))
    name = b"word/document.xml"
    # Set bit 0 (encrypted) of the general purpose flag in the member's local
    # header and its central directory entry; zipfile then raises RuntimeError
    # on read, which the extractor turns into a refusal.
    local = raw.find(b"PK\x03\x04")
    while local >= 0:
        name_len = int.from_bytes(raw[local + 26 : local + 28], "little")
        if raw[local + 30 : local + 30 + name_len] == name:
            raw[local + 6] |= 1
            break
        local = raw.find(b"PK\x03\x04", local + 4)
    central = raw.find(b"PK\x01\x02")
    while central >= 0:
        name_len = int.from_bytes(raw[central + 28 : central + 30], "little")
        if raw[central + 46 : central + 46 + name_len] == name:
            raw[central + 8] |= 1
            break
        central = raw.find(b"PK\x01\x02", central + 4)
    assert local >= 0 and central >= 0
    reason = _refused(bytes(raw), "docx")
    assert "cannot be read" in reason and "encrypted" in reason


def test_not_a_zip_is_refused() -> None:
    assert "not a zip package" in _refused(b"%PDF-1.7 not a package", "docx")


def test_a_missing_main_part_is_refused() -> None:
    assert "word/document.xml is missing" in _refused(write_zip({"other.xml": "<a/>"}), "docx")
    assert "ppt/presentation.xml is missing" in _refused(write_zip({"other.xml": "<a/>"}), "pptx")


def test_malformed_xml_is_refused() -> None:
    assert "not well-formed XML" in _refused(build_docx(extra_members={"word/document.xml": "<w:document><w:body>"}), "docx")


def test_a_corrupt_member_is_refused() -> None:
    raw = bytearray(build_docx(body=["Body."]))
    # Overwrite the start of word/document.xml's compressed stream.
    header = raw.find(b"PK\x03\x04")
    while header >= 0:
        name_len = int.from_bytes(raw[header + 26 : header + 28], "little")
        extra_len = int.from_bytes(raw[header + 28 : header + 30], "little")
        if raw[header + 30 : header + 30 + name_len] == b"word/document.xml":
            start = header + 30 + name_len + extra_len
            raw[start : start + 4] = b"\xff\xff\xff\xff"
            break
        header = raw.find(b"PK\x03\x04", header + 4)
    assert header >= 0
    reason = _refused(bytes(raw), "docx")
    assert "corrupt" in reason or "cannot be read" in reason or "not well-formed" in reason


def test_a_package_over_the_total_limit_is_refused_by_length() -> None:
    from metricmine.documents.extract import MAX_TOTAL_BYTES, _Package

    with pytest.raises(RefusedPackage) as info:
        _Package(b"\x00" * (MAX_TOTAL_BYTES + 1))
    assert "over the" in str(info.value)


def test_binary_and_non_utf8_text_are_refused() -> None:
    assert "NUL byte" in _refused(b"abc\x00def", "text")
    assert "not UTF-8" in _refused(b"caf\xe9", "text")


def test_an_unknown_format_is_refused() -> None:
    assert "no extractor for format" in _refused(b"x", "pdf")


def test_a_refused_package_is_a_state_not_a_crash(tmp_path: Path) -> None:
    (tmp_path / "contracts").mkdir()
    (tmp_path / "contracts" / "x.odcs.yaml").write_text("id: x\nschema: []\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "bad.docx").write_bytes(b"not a package at all")
    register = Register(
        contract=None,  # type: ignore[arg-type]
        standing=[
            {
                "document_id": "bad",
                "title": "Bad",
                "governance": "in_repo",
                "access": "in_repo",
                "location": "docs/bad.docx",
                "format": "docx",
                "text_sha256": "0" * 64,
            }
        ],
        bindings=[],
    )
    from datetime import date

    (report,) = derive(tmp_path, register, date(2026, 10, 17))
    assert report.state == "refused_package"
    assert "not a zip package" in report.detail
    assert report.next_command.startswith("fix or replace the file")


def test_zipfile_in_memory_never_extracts_to_disk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    extract_bytes(build_docx(body=["Nothing lands on disk."]), "docx")
    assert set(tmp_path.iterdir()) == before


def test_a_zip_with_a_traversal_member_name_is_read_in_memory_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    raw = build_docx(body=["Body."], extra_members={"../../escape.txt": "x"})
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        assert "../../escape.txt" in zf.namelist()
    e = extract_bytes(raw, "docx")
    assert e.contains("Body.")
    assert not (tmp_path.parent.parent / "escape.txt").exists()
    assert list(tmp_path.iterdir()) == []
