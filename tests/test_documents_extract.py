"""The text extractors (D-43; S37 14.1): every part of a package is read,
identity is the extracted text and never the bytes, normalization is NFKC
and whitespace only, redlines give a Word file two views, and PowerPoint
notes are found through the package's relationships.

Every Word and PowerPoint package here is built by tests/documents_fixtures.py
on the standard library; no binary file of unknown provenance is read.
Keyless, no network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from metricmine.documents import extract
from metricmine.documents.extract import EXTRACTOR_ID, Extraction, extract_bytes, extract_path, normalize, text_digest
from documents_fixtures import build_docx, build_pptx, w_paragraph, w_run, w_textbox_alternate

REPO = Path(__file__).resolve().parents[1]
RD = REPO / "documents" / "sources" / "nycflights13" / "flights.Rd"
ANCHOR = "Departure and arrival delays, in minutes. Negative times represent early departures/arrivals."
# Measured in the sandbox on October 17, 2026, twice: the text digest of the
# committed copy of man/flights.Rd at df98ef21 under metricmine.documents@1.0.0.
RD_TEXT_SHA256 = "8b96d6ed2a14856d377b5e47b2afc94555a00df3f9de90981920b2bcb3891e09"


# ---------------------------------------------------------------- normalization and identity


def test_normalize_is_nfkc_and_whitespace_only() -> None:
    assert normalize("  a \t\n b  ") == "a b"
    assert normalize("ﬁle") == "file"  # the fi ligature folds under NFKC
    assert normalize("Straße") == "Straße"  # case and letters are never touched
    assert normalize("“quoted”") == "“quoted”"  # curly quotes are not folded


def test_text_digest_is_over_the_normalized_text() -> None:
    assert text_digest("a  b") == text_digest("a\nb") == text_digest(" a b ")
    assert text_digest("a b") != text_digest("a c")


# ---------------------------------------------------------------- text and markdown


def test_text_lines_become_paragraphs_with_line_ordinals() -> None:
    e = extract_bytes(b"first\n\n  second line  \nthird", "text", "t.txt")
    (part,) = e.parts
    assert part.unit == "line"
    assert part.paragraphs == ("first", "second line", "third")
    assert part.ordinals == (1, 3, 4)
    assert e.text == "first second line third"
    assert e.accepted_parts is None and not e.has_pending_changes


def test_a_utf8_bom_is_stripped_and_markdown_reads_as_text() -> None:
    assert extract_bytes("﻿# Title\n\nBody.".encode("utf-8"), "markdown", "m.md").text == "# Title Body."


def test_the_committed_rd_anchor_spans_a_line_break_and_matches_after_normalization() -> None:
    raw = RD.read_text(encoding="utf-8")
    assert ANCHOR not in raw  # the quote crosses lines 13 and 14 in the file
    e = extract_path(RD, "text")
    assert e.contains(ANCHOR)
    assert e.locate(ANCHOR) == "text, line 13"
    assert e.text_sha256 == RD_TEXT_SHA256
    assert e.extractor == EXTRACTOR_ID == "metricmine.documents@1.0.0"


def test_sentences_split_over_the_joined_text_with_locators() -> None:
    e = extract_path(RD, "text")
    hits = e.sentences("delay")
    assert hits == [("text, line 13", "\\item{dep_delay, arr_delay}{Departure and arrival delays, in minutes.")]
    everything = e.sentences()
    assert len(everything) == 20
    assert everything[0][0] == "text, line 1"
    # a closing brace after the period still ends a sentence (Rd's `.}`)
    assert any(sentence.endswith("arrivals.}") for _, sentence in everything)


# ---------------------------------------------------------------- Word: every part


def _docx_everything() -> Extraction:
    return extract_bytes(
        build_docx(
            body=["Body sentence one.", "Body sentence two."],
            table=["Term", "Delays are measured in minutes."],
            header="Header text here.",
            footer="Footer text here.",
            footnote="A footnote sentence.",
            endnote="An endnote sentence.",
            textbox="A text box sentence.",
            split_runs=["Split ", "across ", "runs."],
        ),
        "docx",
    )


@pytest.mark.parametrize(
    ("quote", "locator"),
    [
        ("Body sentence two.", "body, paragraph 2"),
        ("Delays are measured in minutes.", "body, paragraph 4"),
        ("A text box sentence.", "body, paragraph 5"),
        ("Split across runs.", "body, paragraph 7"),  # the text box anchors in paragraph 6, an empty wrapper
        ("Header text here.", "header 1, paragraph 1"),
        ("Footer text here.", "footer 1, paragraph 1"),
        ("A footnote sentence.", "footnotes, paragraph 1"),
        ("An endnote sentence.", "endnotes, paragraph 1"),
    ],
)
def test_docx_reads_every_part_and_locates_each_quote(quote: str, locator: str) -> None:
    e = _docx_everything()
    assert e.contains(quote), quote
    assert e.locate(quote) == locator


def test_docx_part_order_is_fixed_and_labeled() -> None:
    e = _docx_everything()
    assert [p.label for p in e.parts] == ["body", "header 1", "footer 1", "footnotes", "endnotes"]
    assert all(p.unit == "paragraph" for p in e.parts)
    assert e.accepted_parts is None  # no redline: one view, no pending changes


def test_a_word_written_text_box_is_read_once() -> None:
    # Word stores a text box twice (mc:Choice and mc:Fallback); the fallback
    # copy is skipped, so the text and the digest count it once.
    e = extract_bytes(build_docx(body=["Body."], raw_body_xml=w_textbox_alternate("Boxed once.")), "docx")
    assert e.text == "Body. Boxed once."
    assert e.locate("Boxed once.") == "body, paragraph 2"  # the Choice paragraph; the fallback and the wrapper are empty


def test_docx_tabs_and_breaks_read_as_spaces() -> None:
    raw_body = '<w:p><w:r><w:t>left</w:t></w:r><w:r><w:tab/></w:r><w:r><w:t>right</w:t></w:r><w:r><w:br/></w:r><w:r><w:t>below</w:t></w:r></w:p>'
    e = extract_bytes(build_docx(raw_body_xml=raw_body), "docx")
    assert e.text == "left right below"


# ---------------------------------------------------------------- Word: redlines


def test_a_pending_redline_gives_two_views_and_names_what_an_acceptance_breaks() -> None:
    e = extract_bytes(
        build_docx(redline=("Departure delays, in ", "minutes", "seconds", ". Negative means early.")),
        "docx",
    )
    assert e.has_pending_changes
    assert e.text == "Departure delays, in minutes. Negative means early."
    assert e.accepted_text == "Departure delays, in seconds. Negative means early."
    assert e.contains("delays, in minutes") and not e.accepted_contains("delays, in minutes")
    assert e.accepted_contains("delays, in seconds")


def test_a_redline_elsewhere_leaves_the_anchor_in_both_views() -> None:
    e = extract_bytes(
        build_docx(body=["Delays are in minutes."], redline=("Colour ", "grey", "gray", " is fine.")),
        "docx",
    )
    assert e.has_pending_changes
    assert e.contains("Delays are in minutes.") and e.accepted_contains("Delays are in minutes.")


# ---------------------------------------------------------------- PowerPoint


def test_pptx_reads_text_boxes_tables_groups_and_notes_in_slide_order() -> None:
    e = extract_bytes(
        build_pptx(
            [
                {"text": "Slide one text.", "table": ["Term", "A table cell sentence."], "group": "A grouped sentence."},
                {"text": "Slide two text.", "notes": "Speaker notes for slide two."},
            ]
        ),
        "pptx",
    )
    assert [p.label for p in e.parts] == ["slide 1", "slide 2", "slide 2 notes"]
    assert e.locate("A table cell sentence.") == "slide 1, paragraph 3"
    assert e.locate("A grouped sentence.") == "slide 1, paragraph 4"
    assert e.locate("Speaker notes for slide two.") == "slide 2 notes, paragraph 1"


def test_pptx_notes_follow_the_relationships_not_the_file_numbers() -> None:
    # Only slide 2 has notes, so its notes part is notesSlide1.xml: a reader
    # that pairs slideN with notesSlideN attributes the notes to slide 1.
    e = extract_bytes(build_pptx([{"text": "One."}, {"text": "Two.", "notes": "Notes of two."}]), "pptx")
    notes = [p for p in e.parts if p.label.endswith("notes")]
    assert [p.label for p in notes] == ["slide 2 notes"]
    assert notes[0].name == "ppt/notesSlides/notesSlide1.xml"


def test_pptx_field_text_stays_out_of_the_words() -> None:
    # A slide number or date field carries cached text that moves on a
    # re-save; it is not part of the deck's words or its digest.
    e = extract_bytes(build_pptx([{"text": "Slide words.", "field": "7"}]), "pptx")
    assert e.text == "Slide words."


def test_pptx_slide_order_comes_from_the_presentation_part() -> None:
    e = extract_bytes(build_pptx([{"text": "First."}, {"text": "Second."}, {"text": "Third."}]), "pptx")
    assert e.text == "First. Second. Third."
    assert e.locate("Third.") == "slide 3, paragraph 1"


# ---------------------------------------------------------------- identity across a re-save


def test_the_same_words_saved_twice_have_different_bytes_and_one_text_digest() -> None:
    first = build_docx(body=["Delays are in minutes."], fixed_time=False)
    second = build_docx(body=["Delays are in minutes."], fixed_time=True)
    assert first != second  # the zip timestamps differ (F-69)
    assert extract_bytes(first, "docx").text_sha256 == extract_bytes(second, "docx").text_sha256


def test_fixed_time_builds_are_byte_identical_and_extraction_is_deterministic() -> None:
    a = build_pptx([{"text": "Same.", "notes": "Same notes."}])
    b = build_pptx([{"text": "Same.", "notes": "Same notes."}])
    assert a == b
    assert extract_bytes(a, "pptx").text_sha256 == extract_bytes(b, "pptx").text_sha256


# The parts the extractor does not read (docs/documents.md, "The
# extractors"), each carrying a sentence, so that a walk which starts
# reading one of them moves the golden digests below and the part-list
# tests go red by name.
_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
UNREAD_DOCX_PARTS = {
    "word/comments.xml": f'<?xml version="1.0" encoding="UTF-8"?><w:comments xmlns:w="{_W_NS}"><w:comment w:id="0">{w_paragraph(w_run("A reviewer comment, not read."))}</w:comment></w:comments>',
    "word/glossary/document.xml": f'<?xml version="1.0" encoding="UTF-8"?><w:glossaryDocument xmlns:w="{_W_NS}"><w:docParts><w:docPart><w:docPartBody>{w_paragraph(w_run("A building block, not read."))}</w:docPartBody></w:docPart></w:docParts></w:glossaryDocument>',
    "word/diagrams/data1.xml": f'<?xml version="1.0" encoding="UTF-8"?><dgm:dataModel xmlns:dgm="http://schemas.openxmlformats.org/drawingml/2006/diagram" xmlns:a="{_A_NS}"><dgm:ptLst><dgm:pt modelId="1"><dgm:t><a:p><a:r><a:t>SmartArt text, not read.</a:t></a:r></a:p></dgm:t></dgm:pt></dgm:ptLst></dgm:dataModel>',
}
UNREAD_PPTX_PARTS = {
    "ppt/comments/comment1.xml": f'<?xml version="1.0" encoding="UTF-8"?><p:cmLst xmlns:p="{_P_NS}"><p:cm authorId="0" idx="1"><p:text>A slide comment, not read.</p:text></p:cm></p:cmLst>',
    "ppt/slideLayouts/slideLayout1.xml": f'<?xml version="1.0" encoding="UTF-8"?><p:sldLayout xmlns:a="{_A_NS}" xmlns:p="{_P_NS}"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>Layout placeholder text, not read.</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sldLayout>',
    "ppt/slideMasters/slideMaster1.xml": f'<?xml version="1.0" encoding="UTF-8"?><p:sldMaster xmlns:a="{_A_NS}" xmlns:p="{_P_NS}"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>Master text, not read.</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sldMaster>',
}


def test_the_docx_part_list_is_pinned_by_name() -> None:
    # The part list a maintainer edits: body, headers and footers by number,
    # footnotes, endnotes, and nothing else. An addition shows up here first.
    names = {"word/document.xml", "word/header2.xml", "word/header1.xml", "word/footer1.xml", "word/footnotes.xml", "word/endnotes.xml"}
    assert extract._docx_part_names(names | set(UNREAD_DOCX_PARTS)) == [
        ("body", "word/document.xml"),
        ("header 1", "word/header1.xml"),
        ("header 2", "word/header2.xml"),
        ("footer 1", "word/footer1.xml"),
        ("footnotes", "word/footnotes.xml"),
        ("endnotes", "word/endnotes.xml"),
    ]
    e = extract_bytes(build_docx(body=["Only the body."], extra_members=UNREAD_DOCX_PARTS), "docx")
    assert e.text == "Only the body."
    assert [p.label for p in e.parts] == ["body"]


def test_the_pptx_part_list_is_pinned_by_name() -> None:
    # Slides in presentation order and each slide's notes through its
    # relationships; comments, layouts, and masters stay out.
    e = extract_bytes(build_pptx([{"text": "Only the slide.", "notes": "And its notes."}], extra_members=UNREAD_PPTX_PARTS), "pptx")
    assert e.text == "Only the slide. And its notes."
    assert [p.label for p in e.parts] == ["slide 1", "slide 1 notes"]


# Golden digests of the code-built fixtures under the running extractor id.
# The fixtures carry the unread parts too, so a change to normalization,
# the part list, or the walk moves these; the maintainer then bumps
# EXTRACTOR_VERSION and every standing row is re-verified by pull request
# (docs/documents.md, "The extractors").
def test_golden_digests_are_held_to_the_extractor_version() -> None:
    assert EXTRACTOR_ID == "metricmine.documents@1.0.0"
    docx = build_docx(
        body=["Body sentence one."], table=["Term", "Delays are measured in minutes."], header="Header text here.", extra_members=UNREAD_DOCX_PARTS
    )
    pptx = build_pptx(
        [{"text": "Slide one text.", "table": ["Term", "A table cell sentence."]}, {"text": "Two.", "notes": "Notes of two."}],
        extra_members=UNREAD_PPTX_PARTS,
    )
    measured = {
        "text": extract_bytes("First line.\nSecond   line.\n".encode("utf-8"), "text").text_sha256,
        "docx": extract_bytes(docx, "docx").text_sha256,
        "pptx": extract_bytes(pptx, "pptx").text_sha256,
    }
    expected = {
        "text": "b1cf50d8e70479da334ed0a60e05790af87a17c648d40e3cd8fa3c911c4132f5",
        "docx": "ff1eea9ef02fa7413189e1160f1466fae9b92791ad4d1cefd8ef91e19a336721",
        "pptx": "09fc9d7d371d5807fa7fdc1d4379398d28a7c5590ef0b1a247752101c78f8648",
    }
    assert measured == expected, (
        "the extractor's output moved: bump EXTRACTOR_VERSION, update these goldens in the same pull request, "
        "and re-verify every standing row (docs/documents.md, The extractors)"
    )


def test_the_formats_and_limits_are_the_published_constants() -> None:
    assert extract.FORMATS == ("text", "markdown", "docx", "pptx")
    assert extract.MAX_PART_BYTES == 16 * 1024 * 1024
    assert extract.MAX_TOTAL_BYTES == 64 * 1024 * 1024
    assert extract.MAX_COMPRESSION_RATIO == 100
    assert extract.MAX_XML_DEPTH == 1000
