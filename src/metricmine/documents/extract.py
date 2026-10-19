"""Text extraction for governed documents, on the standard library (D-43).

Four formats in this slice: text, markdown, docx, pptx. A Word or
PowerPoint file is a zip of XML parts, so `zipfile` and
`xml.etree.ElementTree` read it; no document library enters the project.
The extractor reads every part where a bound sentence can hide, which
the common readers miss (measured, F-70): a Word body with its tables
and text boxes, every header and footer, the footnotes and endnotes; a
deck's slides in presentation order with their tables and grouped
shapes, and each slide's notes found through the package's own
relationships. Identity is a digest of the normalized text, never of the
bytes (F-69): NFKC, whitespace collapsed to one space, stripped, and
nothing else normalized.

A Word file with pending tracked changes is two documents in one file.
The standing text keeps every deletion and ignores every insertion; the
accepted text is what the file would say if every change were accepted.
The scan reports `pending_changes` when the two differ and names the
bound claims an acceptance would break.

Untrusted input meets limits, never a crash. The package is read in
memory and never extracted to disk; a part that declares a DOCTYPE or an
entity is refused before it is parsed; a part over MAX_PART_BYTES, a
package over MAX_TOTAL_BYTES, a compression ratio over
MAX_COMPRESSION_RATIO, XML nested deeper than MAX_XML_DEPTH, a
relationship target that escapes the package, a corrupt or encrypted
zip, and a text file that is not UTF-8 are each a `RefusedPackage` that
the scan reports as the state `refused_package` with its reason.

Deterministic by construction: the same bytes give the same parts, the
same text, and the same digest on every platform, and every ordering
below is fixed (document order inside a part; header and footer parts by
number; slides by the presentation's own list).
"""

from __future__ import annotations

import hashlib
import io
import posixpath
import re
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

EXTRACTOR = "metricmine.documents"
EXTRACTOR_VERSION = "1.0.0"
EXTRACTOR_ID = f"{EXTRACTOR}@{EXTRACTOR_VERSION}"
FORMATS = ("text", "markdown", "docx", "pptx")

MAX_PART_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_XML_DEPTH = 1000
MAX_TEXT_BYTES = 64 * 1024 * 1024

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_RID = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NOTES_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"
_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
# A Word-written text box is stored twice, as mc:Choice (the DrawingML form)
# and mc:Fallback (the VML form) under mc:AlternateContent; the fallback is
# skipped in both views so the text is read once.
_SKIP_BOTH = {f"{{{_MC}}}Fallback"}

_WS = re.compile(r"\s+")
_HEADER = re.compile(r"^word/header(\d*)\.xml$")
_FOOTER = re.compile(r"^word/footer(\d*)\.xml$")
# A sentence ends at . ! or ?, optionally followed by a closing bracket or
# quote (Rd markup closes an item with .}), then whitespace.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|(?<=[.!?][)\]}\"'])\s+")


class RefusedPackage(Exception):
    """The input was refused by a safety limit; the reason is the message."""


def normalize(text: str) -> str:
    """NFKC, whitespace collapsed to one space, stripped. Nothing else."""
    return _WS.sub(" ", unicodedata.normalize("NFKC", text)).strip()


def text_digest(text: str) -> str:
    """sha256 over the normalized text, hex."""
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Part:
    """One text-bearing part of a document: its label for people, the
    member name it came from, its normalized paragraphs, and the ordinal
    a person uses to find each one (a line for text, a paragraph for a
    Word part, a paragraph within a slide)."""

    label: str
    name: str
    paragraphs: tuple[str, ...]
    ordinals: tuple[int, ...]
    unit: str  # "line" or "paragraph"


@dataclass(frozen=True)
class Extraction:
    format: str
    parts: tuple[Part, ...]
    accepted_parts: tuple[Part, ...] | None = None
    extractor: str = EXTRACTOR_ID

    @property
    def text(self) -> str:
        return _join(self.parts)

    @property
    def text_sha256(self) -> str:
        return text_digest(self.text)

    @property
    def accepted_text(self) -> str | None:
        return None if self.accepted_parts is None else _join(self.accepted_parts)

    @property
    def has_pending_changes(self) -> bool:
        return self.accepted_text is not None and self.accepted_text != self.text

    def contains(self, anchor: str) -> bool:
        return normalize(anchor) in self.text

    def accepted_contains(self, anchor: str) -> bool:
        accepted = self.accepted_text
        return accepted is not None and normalize(anchor) in accepted

    def locate(self, anchor: str) -> str | None:
        """Where a person finds the anchor: the part and the ordinal of the
        paragraph (or line) where it starts, or None when the anchor is not
        in the text."""
        wanted = normalize(anchor)
        if not wanted:
            return None
        index = self.text.find(wanted)
        if index < 0:
            return None
        for start, part, ordinal, paragraph in _segments(self.parts):
            if start <= index <= start + len(paragraph):
                return f"{part.label}, {part.unit} {ordinal}"
        return None

    def sentences(self, grep: str | None = None) -> list[tuple[str, str]]:
        """(locator, sentence) pairs over the whole text in document order,
        each sentence located where it starts; `grep` keeps the sentences
        that contain it, case-insensitively."""
        needle = normalize(grep).lower() if grep else None
        segments = list(_segments(self.parts))
        text = self.text
        out: list[tuple[str, str]] = []
        position = 0
        for sentence in _SENTENCE_END.split(text):
            start = text.find(sentence, position)
            position = start + len(sentence)
            if not sentence or (needle is not None and needle not in sentence.lower()):
                continue
            locator = "text"
            for seg_start, part, ordinal, paragraph in segments:
                if seg_start <= start <= seg_start + len(paragraph):
                    locator = f"{part.label}, {part.unit} {ordinal}"
                    break
            out.append((locator, sentence))
        return out


def _segments(parts: tuple[Part, ...]):
    """(start offset in the joined text, part, ordinal, paragraph) for every
    non-empty paragraph, in document order; the joined text is these
    paragraphs separated by one space, so the offsets are exact."""
    offset = 0
    for part in parts:
        for paragraph, ordinal in zip(part.paragraphs, part.ordinals):
            if not paragraph:
                continue
            yield offset, part, ordinal, paragraph
            offset += len(paragraph) + 1


def _join(parts: tuple[Part, ...]) -> str:
    return " ".join(paragraph for _, _, _, paragraph in _segments(parts))


# ---------------------------------------------------------------- entry points


def extract_bytes(raw: bytes, fmt: str, name: str = "document") -> Extraction:
    """Extract from bytes already in memory; `fmt` is one of FORMATS."""
    if fmt in ("text", "markdown"):
        return _extract_text(raw, fmt, name)
    if fmt == "docx":
        return _extract_docx(raw)
    if fmt == "pptx":
        return _extract_pptx(raw)
    raise RefusedPackage(f"no extractor for format {fmt!r} in this slice")


def extract_path(path: Path, fmt: str) -> Extraction:
    """Extract from a file the caller has already resolved and vetted (the
    states module decides what may be opened; this function opens it)."""
    size = path.stat().st_size
    if size > MAX_TEXT_BYTES:
        raise RefusedPackage(f"file is {size} bytes, over the {MAX_TEXT_BYTES}-byte limit")
    return extract_bytes(path.read_bytes(), fmt, path.name)


# ---------------------------------------------------------------- text


def _extract_text(raw: bytes, fmt: str, name: str) -> Extraction:
    if len(raw) > MAX_TEXT_BYTES:
        raise RefusedPackage(f"text is {len(raw)} bytes, over the {MAX_TEXT_BYTES}-byte limit")
    if b"\x00" in raw:
        raise RefusedPackage("text contains a NUL byte; not a text document")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RefusedPackage(f"text is not UTF-8 ({exc.reason} at byte {exc.start})") from exc
    if text.startswith("﻿"):
        text = text[1:]
    paragraphs: list[str] = []
    ordinals: list[int] = []
    for number, line in enumerate(text.splitlines(), 1):
        normalized = normalize(line)
        if normalized:
            paragraphs.append(normalized)
            ordinals.append(number)
    part = Part(label="text", name=name, paragraphs=tuple(paragraphs), ordinals=tuple(ordinals), unit="line")
    return Extraction(format=fmt, parts=(part,))


# ---------------------------------------------------------------- packages


class _Package:
    """A zip package read in memory under the safety limits."""

    def __init__(self, raw: bytes):
        if len(raw) > MAX_TOTAL_BYTES:
            raise RefusedPackage(f"package is {len(raw)} bytes, over the {MAX_TOTAL_BYTES}-byte limit")
        try:
            self.zip = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile as exc:
            raise RefusedPackage(f"not a zip package ({exc})") from exc
        self.names = set(self.zip.namelist())
        self.total = 0

    def read(self, name: str) -> bytes:
        if name not in self.names:
            raise RefusedPackage(f"package has no part {name}")
        info = self.zip.getinfo(name)
        if info.file_size > MAX_PART_BYTES:
            raise RefusedPackage(f"part {name} is {info.file_size} bytes, over the {MAX_PART_BYTES}-byte limit")
        if info.file_size and (info.compress_size == 0 or info.file_size / info.compress_size > MAX_COMPRESSION_RATIO):
            raise RefusedPackage(f"part {name} compresses more than {MAX_COMPRESSION_RATIO} to 1")
        self.total += info.file_size
        if self.total > MAX_TOTAL_BYTES:
            raise RefusedPackage(f"package parts exceed {MAX_TOTAL_BYTES} bytes uncompressed")
        try:
            data = self.zip.read(name)
        except RuntimeError as exc:  # an encrypted member
            raise RefusedPackage(f"part {name} cannot be read ({exc})") from exc
        except (zipfile.BadZipFile, zipfile.LargeZipFile, zlib.error, EOFError, OSError, ValueError) as exc:
            raise RefusedPackage(f"part {name} is corrupt ({exc})") from exc
        if len(data) != info.file_size:
            raise RefusedPackage(f"part {name} declares {info.file_size} bytes and holds {len(data)}")
        if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
            raise RefusedPackage(f"part {name} declares a DOCTYPE or an entity")
        return data


def _resolve_target(base_dir: str, target: str, name: str) -> str:
    """A relationship target resolved against its part's folder, held
    inside the package (no escape above the root, no absolute path)."""
    if target.startswith("/"):
        resolved = posixpath.normpath(target.lstrip("/"))
    else:
        resolved = posixpath.normpath(posixpath.join(base_dir, target))
    if resolved.startswith("../") or resolved == ".." or resolved.startswith("/"):
        raise RefusedPackage(f"relationship target {target!r} in {name} escapes the package")
    return resolved


def _walk(data: bytes, name: str, text_tags: dict[str, str], paragraph_tag: str, break_tags: set[str],
          skip_standing: set[str] = frozenset(), skip_accepted: set[str] = frozenset(),
          skip_both: set[str] = frozenset()) -> tuple[list[str], list[str]]:
    """Stream one XML part and return (standing paragraphs, accepted
    paragraphs), normalized, in document order. `text_tags` maps a text
    element's tag to 'both', 'standing', or 'accepted'; an element in
    `skip_standing` hides its subtree from the standing view, one in
    `skip_accepted` from the accepted view, and one in `skip_both` from
    both (the markup-compatibility fallback copy; a deck's field text).
    Depth is bounded; memory is kept flat by clearing finished elements."""
    standing_out: list[str] = []
    accepted_out: list[str] = []
    standing_stack: list[list[str]] = []
    accepted_stack: list[list[str]] = []
    depth = 0
    hide_standing = 0
    hide_accepted = 0
    skip_standing = set(skip_standing) | set(skip_both)
    skip_accepted = set(skip_accepted) | set(skip_both)
    try:
        for event, elem in ET.iterparse(io.BytesIO(data), events=("start", "end")):
            tag = elem.tag
            if event == "start":
                depth += 1
                if depth > MAX_XML_DEPTH:
                    raise RefusedPackage(f"part {name} nests deeper than {MAX_XML_DEPTH}")
                if tag in skip_standing:
                    hide_standing += 1
                if tag in skip_accepted:
                    hide_accepted += 1
                if tag == paragraph_tag:
                    standing_stack.append([])
                    accepted_stack.append([])
                continue
            depth -= 1
            if tag in text_tags and standing_stack:
                view = text_tags[tag]
                piece = elem.text or ""
                if view in ("both", "standing") and not hide_standing:
                    standing_stack[-1].append(piece)
                if view in ("both", "accepted") and not hide_accepted:
                    accepted_stack[-1].append(piece)
            elif tag in break_tags and standing_stack:
                if not hide_standing:
                    standing_stack[-1].append(" ")
                if not hide_accepted:
                    accepted_stack[-1].append(" ")
            elif tag == paragraph_tag:
                standing_out.append(normalize("".join(standing_stack.pop())))
                accepted_out.append(normalize("".join(accepted_stack.pop())))
            if tag in skip_standing:
                hide_standing -= 1
            if tag in skip_accepted:
                hide_accepted -= 1
            elem.clear()
    except ET.ParseError as exc:
        raise RefusedPackage(f"part {name} is not well-formed XML ({exc})") from exc
    return standing_out, accepted_out


def _part(label: str, name: str, paragraphs: list[str]) -> Part:
    kept = [(i, p) for i, p in enumerate(paragraphs, 1) if p]
    return Part(
        label=label,
        name=name,
        paragraphs=tuple(p for _, p in kept),
        ordinals=tuple(i for i, _ in kept),
        unit="paragraph",
    )


# ---------------------------------------------------------------- docx

_W_TEXT = {f"{{{_W}}}t": "both", f"{{{_W}}}delText": "standing"}
_W_BREAKS = {f"{{{_W}}}tab", f"{{{_W}}}br", f"{{{_W}}}cr"}
_W_P = f"{{{_W}}}p"
_W_SKIP_STANDING = {f"{{{_W}}}ins", f"{{{_W}}}moveTo"}
_W_SKIP_ACCEPTED = {f"{{{_W}}}del", f"{{{_W}}}moveFrom"}


def _docx_part_names(names: set[str]) -> list[tuple[str, str]]:
    """(label, member) in the fixed order: body, headers by number,
    footers by number, footnotes, endnotes."""
    if "word/document.xml" not in names:
        raise RefusedPackage("not a Word package: word/document.xml is missing")
    out = [("body", "word/document.xml")]

    def numbered(pattern: re.Pattern[str], label: str) -> list[tuple[str, str]]:
        found = []
        for member in names:
            match = pattern.match(member)
            if match:
                found.append((int(match.group(1) or 0), member))
        return [(f"{label} {n}" if n else label, member) for n, member in sorted(found)]

    out += numbered(_HEADER, "header")
    out += numbered(_FOOTER, "footer")
    if "word/footnotes.xml" in names:
        out.append(("footnotes", "word/footnotes.xml"))
    if "word/endnotes.xml" in names:
        out.append(("endnotes", "word/endnotes.xml"))
    return out


def _extract_docx(raw: bytes) -> Extraction:
    package = _Package(raw)
    standing_parts: list[Part] = []
    accepted_parts: list[Part] = []
    for label, member in _docx_part_names(package.names):
        standing, accepted = _walk(
            package.read(member), member, _W_TEXT, _W_P, _W_BREAKS, _W_SKIP_STANDING, _W_SKIP_ACCEPTED, _SKIP_BOTH
        )
        standing_parts.append(_part(label, member, standing))
        accepted_parts.append(_part(label, member, accepted))
    extraction = Extraction(format="docx", parts=tuple(standing_parts), accepted_parts=tuple(accepted_parts))
    if extraction.accepted_text == extraction.text:
        return Extraction(format="docx", parts=tuple(standing_parts), accepted_parts=None)
    return extraction


# ---------------------------------------------------------------- pptx

_A_TEXT = {f"{{{_A}}}t": "both"}
_A_BREAKS = {f"{{{_A}}}br"}
# A field's cached text (a slide number, an auto-updating date) is not the
# deck's words: it moves on a re-save, so it stays out of the text.
_A_SKIP = {f"{{{_A}}}fld"} | _SKIP_BOTH
_A_P = f"{{{_A}}}p"


def _relationships(package: _Package, member: str) -> list[tuple[str, str, str]]:
    """(Id, Type, Target) of a .rels part, or an empty list when absent."""
    if member not in package.names:
        return []
    out = []
    try:
        for rel in ET.fromstring(package.read(member)).iter(f"{{{_REL}}}Relationship"):
            out.append((rel.get("Id", ""), rel.get("Type", ""), rel.get("Target", "")))
    except ET.ParseError as exc:
        raise RefusedPackage(f"part {member} is not well-formed XML ({exc})") from exc
    return out


def _slide_members(package: _Package) -> list[str]:
    """Slide parts in presentation order, through presentation.xml's
    sldIdLst and the presentation's own relationships."""
    if "ppt/presentation.xml" not in package.names:
        raise RefusedPackage("not a PowerPoint package: ppt/presentation.xml is missing")
    rels = {rid: target for rid, _, target in _relationships(package, "ppt/_rels/presentation.xml.rels")}
    try:
        root = ET.fromstring(package.read("ppt/presentation.xml"))
    except ET.ParseError as exc:
        raise RefusedPackage(f"part ppt/presentation.xml is not well-formed XML ({exc})") from exc
    members = []
    for sld in root.iter(f"{{{_P}}}sldId"):
        rid = sld.get(f"{{{_RID}}}id", "")
        target = rels.get(rid)
        if target is None:
            raise RefusedPackage(f"slide relationship {rid!r} has no target")
        members.append(_resolve_target("ppt", target, "ppt/_rels/presentation.xml.rels"))
    return members


def _notes_member(package: _Package, slide_member: str) -> str | None:
    folder, base = posixpath.split(slide_member)
    rels_member = f"{folder}/_rels/{base}.rels"
    for _, rtype, target in _relationships(package, rels_member):
        if rtype == _NOTES_TYPE:
            return _resolve_target(folder, target, rels_member)
    return None


def _extract_pptx(raw: bytes) -> Extraction:
    package = _Package(raw)
    parts: list[Part] = []
    for number, member in enumerate(_slide_members(package), 1):
        standing, _ = _walk(package.read(member), member, _A_TEXT, _A_P, _A_BREAKS, skip_both=_A_SKIP)
        parts.append(_part(f"slide {number}", member, standing))
        notes = _notes_member(package, member)
        if notes is not None and notes in package.names:
            standing, _ = _walk(package.read(notes), notes, _A_TEXT, _A_P, _A_BREAKS, skip_both=_A_SKIP)
            parts.append(_part(f"slide {number} notes", notes, standing))
    return Extraction(format="pptx", parts=tuple(parts))
