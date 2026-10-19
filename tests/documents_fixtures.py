"""Word and PowerPoint packages built by code, on the standard library.

The documents module's tests never read a binary file of unknown
provenance: every .docx and .pptx they open is written here from the
parts the Office formats name, so a reader can see exactly which part
holds which sentence. `fixed_time=True` stamps every zip entry with the
same date, so two builds are byte-identical; `fixed_time=False` lets
`zipfile` stamp the current time, which is how the same words saved twice
get different bytes (F-69).
"""

from __future__ import annotations

import io
import time
import zipfile
from xml.sax.saxutils import escape

from metricmine.documents.extract import EXTRACTOR_ID

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT = "http://schemas.openxmlformats.org/package/2006/content-types"

FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def write_zip(members: dict[str, str | bytes], fixed_time: bool = True) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in members.items():
            data = content.encode("utf-8") if isinstance(content, str) else content
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME if fixed_time else time.localtime()[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)
    return buf.getvalue()


# ---------------------------------------------------------------- Word


def w_run(text: str, deleted: bool = False) -> str:
    tag = "w:delText" if deleted else "w:t"
    return f'<w:r><{tag} xml:space="preserve">{escape(text)}</{tag}></w:r>'


def w_paragraph(*runs: str) -> str:
    return "<w:p>" + "".join(runs) + "</w:p>"


def w_table(cells: list[str]) -> str:
    row = "".join(f"<w:tc><w:tcPr/>{w_paragraph(w_run(c))}</w:tc>" for c in cells)
    return f"<w:tbl><w:tblPr/><w:tblGrid/><w:tr>{row}</w:tr></w:tbl>"


def w_textbox(text: str) -> str:
    """A text box as Word stores it: a drawing with w:txbxContent inside a run."""
    return (
        "<w:p><w:r><w:pict><v:shape xmlns:v=\"urn:schemas-microsoft-com:vml\"><v:textbox>"
        f"<w:txbxContent>{w_paragraph(w_run(text))}</w:txbxContent>"
        "</v:textbox></v:shape></w:pict></w:r></w:p>"
    )


def w_textbox_alternate(text: str) -> str:
    """A text box as Word writes it: mc:AlternateContent with the DrawingML
    form in mc:Choice and the VML form in mc:Fallback, the same text twice."""
    mc = "http://schemas.openxmlformats.org/markup-compatibility/2006"
    wps = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
    return (
        f'<w:p><w:r><mc:AlternateContent xmlns:mc="{mc}"><mc:Choice Requires="wps">'
        f'<w:drawing><wps:wsp xmlns:wps="{wps}"><wps:txbx><w:txbxContent>{w_paragraph(w_run(text))}</w:txbxContent></wps:txbx></wps:wsp></w:drawing>'
        "</mc:Choice><mc:Fallback>"
        f'<w:pict><v:shape xmlns:v="urn:schemas-microsoft-com:vml"><v:textbox><w:txbxContent>{w_paragraph(w_run(text))}</w:txbxContent></v:textbox></v:shape></w:pict>'
        "</mc:Fallback></mc:AlternateContent></w:r></w:p>"
    )


def w_redline(before: str, deleted: str, inserted: str, after: str) -> str:
    """One tracked change: `deleted` replaced by `inserted`, not yet accepted."""
    return (
        "<w:p>"
        + w_run(before)
        + f'<w:del w:id="101" w:author="Reviewer" w:date="2026-10-17T12:00:00Z">{w_run(deleted, deleted=True)}</w:del>'
        + f'<w:ins w:id="102" w:author="Reviewer" w:date="2026-10-17T12:00:00Z">{w_run(inserted)}</w:ins>'
        + w_run(after)
        + "</w:p>"
    )


def _w_document(body_xml: str, with_header: bool, with_footer: bool) -> str:
    sect = "<w:sectPr>"
    if with_header:
        sect += '<w:headerReference w:type="default" r:id="rIdH"/>'
    if with_footer:
        sect += '<w:footerReference w:type="default" r:id="rIdF"/>'
    sect += "</w:sectPr>"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W}" xmlns:r="{_R}"><w:body>{body_xml}{sect}</w:body></w:document>'
    )


def build_docx(
    body: list[str] | None = None,
    table: list[str] | None = None,
    header: str | None = None,
    footer: str | None = None,
    footnote: str | None = None,
    endnote: str | None = None,
    textbox: str | None = None,
    split_runs: list[str] | None = None,
    redline: tuple[str, str, str, str] | None = None,
    raw_body_xml: str = "",
    extra_members: dict[str, str | bytes] | None = None,
    fixed_time: bool = True,
) -> bytes:
    """A .docx whose parts hold exactly the sentences passed in."""
    body_xml = "".join(w_paragraph(w_run(p)) for p in (body or []))
    if table:
        body_xml += w_table(table)
    if textbox:
        body_xml += w_textbox(textbox)
    if split_runs:
        body_xml += w_paragraph(*(w_run(piece) for piece in split_runs))
    if redline:
        body_xml += w_redline(*redline)
    body_xml += raw_body_xml
    members: dict[str, str | bytes] = {}
    overrides = ['<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>']
    rels = []
    if header is not None:
        members["word/header1.xml"] = f'<?xml version="1.0" encoding="UTF-8"?><w:hdr xmlns:w="{_W}">{w_paragraph(w_run(header))}</w:hdr>'
        overrides.append('<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>')
        rels.append(f'<Relationship Id="rIdH" Type="{_R}/header" Target="header1.xml"/>')
    if footer is not None:
        members["word/footer1.xml"] = f'<?xml version="1.0" encoding="UTF-8"?><w:ftr xmlns:w="{_W}">{w_paragraph(w_run(footer))}</w:ftr>'
        overrides.append('<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>')
        rels.append(f'<Relationship Id="rIdF" Type="{_R}/footer" Target="footer1.xml"/>')
    if footnote is not None:
        members["word/footnotes.xml"] = f'<?xml version="1.0" encoding="UTF-8"?><w:footnotes xmlns:w="{_W}"><w:footnote w:id="1">{w_paragraph(w_run(footnote))}</w:footnote></w:footnotes>'
        overrides.append('<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>')
        rels.append(f'<Relationship Id="rIdFn" Type="{_R}/footnotes" Target="footnotes.xml"/>')
    if endnote is not None:
        members["word/endnotes.xml"] = f'<?xml version="1.0" encoding="UTF-8"?><w:endnotes xmlns:w="{_W}"><w:endnote w:id="1">{w_paragraph(w_run(endnote))}</w:endnote></w:endnotes>'
        overrides.append('<Override PartName="/word/endnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml"/>')
        rels.append(f'<Relationship Id="rIdEn" Type="{_R}/endnotes" Target="endnotes.xml"/>')
    members["[Content_Types].xml"] = (
        f'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="{_CT}">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>' + "".join(overrides) + "</Types>"
    )
    members["_rels/.rels"] = (
        f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{_REL}">'
        f'<Relationship Id="rId1" Type="{_R}/officeDocument" Target="word/document.xml"/></Relationships>'
    )
    members["word/_rels/document.xml.rels"] = f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{_REL}">' + "".join(rels) + "</Relationships>"
    members["word/document.xml"] = _w_document(body_xml, header is not None, footer is not None)
    if extra_members:
        members.update(extra_members)
    return write_zip(members, fixed_time=fixed_time)


# ---------------------------------------------------------------- PowerPoint


def a_paragraph(text: str) -> str:
    return f'<a:p><a:r><a:rPr lang="en-US"/><a:t>{escape(text)}</a:t></a:r></a:p>'


def p_field(text: str, shape_id: int = 6) -> str:
    """A slide-number field with its cached text, as PowerPoint stores one."""
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="Slide Number {shape_id}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:fld id="{{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}}" type="slidenum">'
        f'<a:rPr lang="en-US"/><a:t>{escape(text)}</a:t></a:fld></a:p></p:txBody></p:sp>'
    )


def p_textbox(text: str, shape_id: int = 2) -> str:
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="TextBox {shape_id}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f"<p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>{a_paragraph(text)}</p:txBody></p:sp>"
    )


def p_table(cells: list[str], shape_id: int = 3) -> str:
    tcs = "".join(f"<a:tc><a:txBody><a:bodyPr/>{a_paragraph(c)}</a:txBody></a:tc>" for c in cells)
    return (
        f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{shape_id}" name="Table {shape_id}"/><p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
        f"<a:tbl><a:tblPr/><a:tblGrid/><a:tr>{tcs}</a:tr></a:tbl></a:graphicData></a:graphic></p:graphicFrame>"
    )


def p_group(text: str, shape_id: int = 4) -> str:
    return (
        f'<p:grpSp><p:nvGrpSpPr><p:cNvPr id="{shape_id}" name="Group {shape_id}"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        f"<p:grpSpPr/>{p_textbox(text, shape_id + 1)}</p:grpSp>"
    )


def _slide_xml(shapes: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sld xmlns:a="{_A}" xmlns:r="{_R}" xmlns:p="{_P}"><p:cSld><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
        f"{shapes}</p:spTree></p:cSld></p:sld>"
    )


def build_pptx(slides: list[dict], fixed_time: bool = True, extra_members: dict[str, str | bytes] | None = None,
               notes_target_override: str | None = None) -> bytes:
    """A .pptx with the slides given, in order. Each slide dict may carry
    `text` (a text box), `table` (a list of cell texts), `group` (a text
    box inside a grouped shape), and `notes`. Notes parts are numbered in
    the order they are created, which is not the slide order when an
    earlier slide has no notes: the extractor must follow the
    relationships, never the file names."""
    members: dict[str, str | bytes] = {}
    overrides = ['<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>']
    sld_ids = []
    pres_rels = []
    notes_counter = 0
    for number, slide in enumerate(slides, 1):
        shapes = ""
        if "text" in slide:
            shapes += p_textbox(slide["text"], 2)
        if "table" in slide:
            shapes += p_table(slide["table"], 3)
        if "group" in slide:
            shapes += p_group(slide["group"], 4)
        if "field" in slide:
            shapes += p_field(slide["field"], 6)
        slide_member = f"ppt/slides/slide{number}.xml"
        members[slide_member] = _slide_xml(shapes)
        overrides.append(f'<Override PartName="/{slide_member}" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
        slide_rels = []
        if "notes" in slide:
            notes_counter += 1
            notes_member = f"ppt/notesSlides/notesSlide{notes_counter}.xml"
            members[notes_member] = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<p:notes xmlns:a="{_A}" xmlns:r="{_R}" xmlns:p="{_P}"><p:cSld><p:spTree>'
                '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
                f"{p_textbox(slide['notes'], 2)}</p:spTree></p:cSld></p:notes>"
            )
            overrides.append(f'<Override PartName="/{notes_member}" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>')
            target = notes_target_override or f"../notesSlides/notesSlide{notes_counter}.xml"
            slide_rels.append(f'<Relationship Id="rId2" Type="{_R}/notesSlide" Target="{target}"/>')
        members[f"ppt/slides/_rels/slide{number}.xml.rels"] = f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{_REL}">' + "".join(slide_rels) + "</Relationships>"
        sld_ids.append(f'<p:sldId id="{255 + number}" r:id="rId{number}"/>')
        pres_rels.append(f'<Relationship Id="rId{number}" Type="{_R}/slide" Target="slides/slide{number}.xml"/>')
    members["ppt/presentation.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:presentation xmlns:a="{_A}" xmlns:r="{_R}" xmlns:p="{_P}"><p:sldIdLst>' + "".join(sld_ids) + "</p:sldIdLst></p:presentation>"
    )
    members["ppt/_rels/presentation.xml.rels"] = f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{_REL}">' + "".join(pres_rels) + "</Relationships>"
    members["[Content_Types].xml"] = (
        f'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="{_CT}">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>' + "".join(overrides) + "</Types>"
    )
    members["_rels/.rels"] = (
        f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{_REL}">'
        f'<Relationship Id="rId1" Type="{_R}/officeDocument" Target="ppt/presentation.xml"/></Relationships>'
    )
    if extra_members:
        members.update(extra_members)
    return write_zip(members, fixed_time=fixed_time)


# ---------------------------------------------------------------- a miniature repository


def write_repo(
    root,
    standing: list[dict] | None = None,
    bindings: list[dict] | None = None,
    contracts: dict[str, list[str]] | None = None,
    documents: dict[str, str | bytes] | None = None,
):
    """A repository under `root` with the committed register contract, one
    small data contract per `contracts` entry (id to column names), the
    `documents` given (repository path to content), and the register rows.
    Dates in rows may be `datetime.date` objects or ISO strings."""
    import shutil
    from pathlib import Path

    import yaml

    here = Path(__file__).resolve().parents[1]
    (root / "contracts").mkdir(parents=True, exist_ok=True)
    shutil.copy(here / "contracts" / "documents_register.odcs.yaml", root / "contracts" / "documents_register.odcs.yaml")
    for cid, columns in (contracts or {"silver_demo": ["delay_minutes", "carrier"]}).items():
        (root / "contracts" / f"{cid}.odcs.yaml").write_text(
            yaml.safe_dump(
                {
                    "apiVersion": "v3.1.0",
                    "kind": "DataContract",
                    "id": cid,
                    "version": "1.0.0",
                    "schema": [
                        {
                            "name": cid,
                            "physicalType": "table",
                            "properties": [{"name": c, "physicalType": "VARCHAR"} for c in columns],
                        }
                    ],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
    for rel, content in (documents or {}).items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    if standing is not None or bindings is not None:
        write_register(root, standing or [], bindings or [])
    return root


def write_register(root, standing: list[dict], bindings: list[dict]) -> None:
    import yaml

    folder = root / "documents" / "register"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "standing.yaml").write_text(yaml.safe_dump({"documents": standing}, sort_keys=False), encoding="utf-8")
    (folder / "bindings.yaml").write_text(yaml.safe_dump({"bindings": bindings}, sort_keys=False), encoding="utf-8")


def standing_row(**overrides) -> dict:
    """A conforming in_repo standing row for docs/policy.md; override freely."""
    import datetime

    row = {
        "document_id": "policy",
        "title": "Delay policy",
        "governance": "in_repo",
        "access": "in_repo",
        "location": "docs/policy.md",
        "format": "markdown",
        "certification_source": "git_merge",
        "gate_strength": "publication_gate",
        "declared_by": "a.person",
        "declared_on": datetime.date(2026, 10, 17),
        "review_by": datetime.date(2027, 10, 17),
        "text_sha256": None,
        "extractor": EXTRACTOR_ID,
        "verified_against": "location",
        "verified_on": datetime.date(2026, 10, 17),
    }
    row.update(overrides)
    return {k: v for k, v in row.items() if v is not None}


def binding_row(**overrides) -> dict:
    import datetime
    import hashlib

    intent = overrides.pop("intent", "delay_minutes rests on the policy's delay sentence.")
    row = {
        "document_id": "policy",
        "contract_id": "silver_demo",
        "column_name": "delay_minutes",
        "anchor": "Delays are measured in minutes.",
        "locator": "text, line 4",
        "intent": intent,
        "intent_sha256": hashlib.sha256(intent.encode("utf-8")).hexdigest(),
        "bound_by": "a.person",
        "bound_on": datetime.date(2026, 10, 17),
    }
    row.update(overrides)
    return row


POLICY_MD = "# Delay policy\n\nA flight is late when it leaves after its scheduled time.\nDelays are measured in minutes.\nNegative values are early departures.\n"


def policy_digest() -> str:
    """The text digest of POLICY_MD under the running extractor."""
    from metricmine.documents.extract import extract_bytes

    return extract_bytes(POLICY_MD.encode("utf-8"), "markdown").text_sha256
