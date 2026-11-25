"""The five-part feedback message layout, read strictly (the governed host
plan, Section 2.3; E1T).

Deterministic code that interprets no free text: a claim is carried as a
string and never read for meaning; a quoted span is compared to a served
sentence by exact match after whitespace folding. The parts are the
field, the kind, the claim, the query, and the rows matching with the
governing contract versions. Anything else in the block is reported and
ignored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

FENCE_OPEN = "FEEDBACK"
FENCE_CLOSE = "END FEEDBACK"
LABELS = ("field", "kind", "claim", "query", "rows matching")
KINDS = (
    "meaning_unclear",
    "meaning_wrong",
    "missing_field",
    "unexpected_values",
    "rule_wanted",
    "i_depend_on_this",
)
MEANING_KINDS = ("meaning_unclear", "meaning_wrong")

# A line that starts a labeled part: a short label and a colon.
_LABEL_RE = re.compile(r"^([A-Za-z][A-Za-z _-]{0,30}):(.*)$")
_FIELD_RE = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$")
_ROWS_RE = re.compile(r"^(\d+)\s+at\s+(.+)$")
_CONTRACT_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s+v?(\d+\.\d+\.\d+)$")
_QUOTE_RE = re.compile(r'"([^"\n]{3,})"')
_FENCE_LINE_RE = re.compile(r"^\s*```")


def fold(text: str) -> str:
    """Whitespace folded to single spaces."""
    return " ".join(text.split())


def split_field(value: str) -> tuple[str, str]:
    """`<category>.<column>` split once; ValueError when the shape is wrong."""
    if not _FIELD_RE.match(value):
        raise ValueError(f"field is not <category>.<column>: {value!r}")
    category, _, column = value.partition(".")
    return category, column


@dataclass
class Message:
    field: str
    kind: str
    claim: str
    query: str
    rows_matching: int
    contracts: dict[str, str]  # contract name -> version, as stated
    extra_parts: list[str] = field(default_factory=list)  # reported, ignored


@dataclass
class ParseResult:
    ok: bool
    reason: str
    message: Message | None
    extra_parts: list[str]


def extract_block(text: str) -> str | None:
    """The extraction rule: the lines between the first line that is
    exactly FEEDBACK and the first END FEEDBACK after it. Markdown fence
    lines (```...) are dropped first, and trailing whitespace is ignored.
    None when no block exists."""
    lines = [ln.rstrip() for ln in text.splitlines() if not _FENCE_LINE_RE.match(ln)]
    try:
        start = lines.index(FENCE_OPEN)
    except ValueError:
        return None
    try:
        end = lines.index(FENCE_CLOSE, start + 1)
    except ValueError:
        return None
    return "\n".join(lines[start + 1 : end])


def parse_block(block: str) -> ParseResult:
    """The five parts, strictly, in order. Anything else is reported and
    ignored."""
    parts: list[tuple[str, list[str]]] = []
    for raw in block.splitlines():
        m = _LABEL_RE.match(raw)
        if m:
            parts.append((m.group(1).strip().lower(), [m.group(2).strip()]))
        elif parts:
            parts[-1][1].append(raw.rstrip())
        elif raw.strip():
            parts.append(("(unlabeled)", [raw.rstrip()]))
    known = [(label, lines) for label, lines in parts if label in LABELS]
    extra = [label for label, _ in parts if label not in LABELS]
    order = [label for label, _ in known]
    if order != list(LABELS):
        missing = [lab for lab in LABELS if lab not in order]
        if missing:
            return ParseResult(False, f"missing part(s): {', '.join(missing)}", None, extra)
        if len(order) != len(LABELS):
            return ParseResult(False, f"a part repeats: {order}", None, extra)
        return ParseResult(False, f"parts out of order: {order}", None, extra)
    values = {label: "\n".join(lines).strip() for label, lines in known}
    fld = values["field"]
    if not _FIELD_RE.match(fld):
        return ParseResult(False, f"field is not <category>.<column>: {fld!r}", None, extra)
    kind = values["kind"]
    if kind not in KINDS:
        return ParseResult(False, f"kind is outside the six: {kind!r}", None, extra)
    if not values["claim"]:
        return ParseResult(False, "claim is empty", None, extra)
    if not values["query"]:
        return ParseResult(False, "query is empty", None, extra)
    rm = _ROWS_RE.match(fold(values["rows matching"]))
    if not rm:
        return ParseResult(
            False,
            f"rows matching is not '<n> at <contract> <version>[, ...]': {values['rows matching']!r}",
            None,
            extra,
        )
    contracts: dict[str, str] = {}
    for item in rm.group(2).split(","):
        cm = _CONTRACT_RE.match(item.strip())
        if not cm:
            return ParseResult(False, f"contract item is not '<name> <version>': {item.strip()!r}", None, extra)
        contracts[cm.group(1)] = cm.group(2)
    msg = Message(fld, kind, values["claim"], values["query"], int(rm.group(1)), contracts, extra)
    return ParseResult(True, "parsed", msg, extra)


def quoted_spans(claim: str) -> list[str]:
    """Double-quoted spans of the claim, for the served-sentence check of a
    meaning kind. Exact text, never interpreted."""
    return [fold(s) for s in _QUOTE_RE.findall(claim)]
