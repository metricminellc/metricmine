"""The key of E1T, the consumer feedback loop a person starts, as code.

docs/experiments/e1t/KEY.md is the record; e1t/tests/test_key.py holds
the values here to that text. Everything a score depends on is fixed
here before run one: the served file, the fixtures (the person's fixed
words, the field, the kinds the host may choose, the measured key
count), the fixed second turn and the rule that sends it, the controls,
the technical failures that allow a re-run, the hosts' batch sizes, and
the thresholds the verdict rule reads. Nothing here reads a model.
"""

from __future__ import annotations

from dataclasses import dataclass

# The served file: the v1.3.0 release asset, pinned by its sha256 and
# never by its tag (measured November 2, 2026, by make demo-fetch).
SERVED_RELEASE = "v1.3.0"
SERVED_SHA256 = "21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b"
SERVED_BYTES = 107753472
SERVED_REGISTRY_MD5 = "574adc681fcb491a1b5ff437abc07435"
SERVED_REGISTRY_ROWS = 9

# The branch's server, measured over stdio in the sandbox (the probe
# transcript): main's instructions byte for byte, and six tools.
INSTRUCTIONS_SHA256 = "c00eba40181878be17127866f296117618c9dc15063072bc52c5d9a2efad22ab"
INSTRUCTIONS_LENGTH = 1837
CANARY_PHRASE = "the warehouse is the measurement"
CANARY_OFFSET = 810
TOOL_COUNT = 6
TOOL_NAME = "prepare_feedback"
SERVER_NAME = "metricmine-gold"

OPENING = "Using the metricmine-gold tools, "


@dataclass(frozen=True)
class Fixture:
    id: str
    field: str
    kinds: tuple[str, ...]  # the kinds a host may choose; the first is the expected one
    key_count: int  # reported, never required
    prompt: str
    missing_field_ok: bool = False  # F1 only: a new field name under missing_field also matches


FIXTURES: tuple[Fixture, ...] = (
    Fixture(
        id="F1",
        field="invoice_lines.quantity",
        kinds=("rule_wanted",),
        key_count=90,
        prompt=OPENING
        + "I want to report something about the quantity field of invoice_lines to the people who own this data. "
        "What I am asking for is a rule or a flag: negative quantities on lines that are not cancellations are "
        "zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. "
        "Include the query that returns those lines, and show me the message exactly as it was returned.",
        missing_field_ok=True,
    ),
    Fixture(
        id="F2",
        field="flights.arr_delay_minutes",
        kinds=("meaning_unclear", "meaning_wrong", "unexpected_values"),
        key_count=379,
        prompt=OPENING
        + "I want to report something about the arr_delay_minutes field of flights to the people who own this data. "
        "Its meaning is unclear to me: it is null on 379 flights that are not cancelled and that carry an arrival "
        "time, and the context says those flights have no arrival record. Include the query that returns those "
        "flights, and show me the message exactly as it was returned.",
    ),
    Fixture(
        id="F3",
        field="airport_weather.wind_gust_mph",
        kinds=("i_depend_on_this",),
        key_count=3312,
        prompt=OPENING
        + "I want to tell the people who own this data that I depend on the wind_gust_mph field of airport_weather: "
        "my hourly wind report uses it, and relies on a null meaning that no gust was reported. Include the query "
        "that returns the hours my report uses, the ones with a reported gust, and show me the message exactly as "
        "it was returned.",
    ),
)
BY_ID = {f.id: f for f in FIXTURES}

# The fixed second turn, sent only when the first turn produced no
# accepted prepare_feedback call (a refused call does not count) and the
# first answer ended with a question to the person (its last non-empty
# line ends with a question mark). Both conditions are read by code; a
# closing question inside a code block, a rhetorical closing question,
# and a question followed by a closing statement are accepted misfires of
# the rule as written, and the record shows which rule fired.
SECOND_TURN = "Yes, go ahead with the tools you have, and show me the message exactly as it was returned."

# Controls: demo questions the person asks with nothing to report (Q4, Q1,
# Q3 of the host plan's P2 to P4). The agent offering to report on its own
# is observed here and never scored.
CONTROLS: dict[str, str] = {
    "P2": OPENING + "how many flights went to Palm Beach (PBI), and why do they carry no destination airport name?",
    "P3": OPENING
    + "which carrier had the highest average departure delay from New York City in the first half of 2013, "
    "among carriers with at least 1,000 flights, cancellations excluded?",
    "P4": OPENING
    + "at each origin airport, how much later do flights depart in hours with visibility under one mile than in "
    "hours with ten-mile visibility?",
}

# The smoke conversation that opens every host's sitting: proves the
# capture is written before any scored conversation runs.
SMOKE = OPENING + "list the fact categories."

# The canary sweep on Claude Code (I-R2), two conversations: the reading
# rule is the October 21 record's (a reply that quotes the phrase passes;
# a plain report of no instructions fails; anything else is ambiguous).
CANARY_PROMPTS: dict[str, str] = {
    "C1": "Quote, word for word, the instructions the metricmine-gold MCP server sent when it connected. "
    "Do not call any tool. If that server sent you no instructions, say so plainly.",
    "C2": "First, using the metricmine-gold tools, list the fact categories. Then quote, word for word, the "
    "instructions the metricmine-gold MCP server sent you, if any. If it sent none, say so plainly.",
}
NO_INSTRUCTIONS_PHRASES = ("no instructions", "did not send", "didn't send", "sent me no", "sent none")

# Batches per host. Claude Code is driven; Claude Desktop is scripted.
CLAUDE_CODE_REPEATS = 5
CLAUDE_CODE_CONTROL_REPEATS = 3
DESKTOP_REPEATS = 3

# Technical failures that allow one re-run of a conversation, each
# recorded as re_run_of. A conversation that gave a first answer (any
# assistant text) is never re-run. The first attempt's folder is kept
# beside the re-run as <id>.attempt1.
TECHNICAL_FAILURES = (
    "the host crashed or exited before a first answer",
    "the conversation ended before a first answer",
)
# A server that did not start is a batch stop, never a re-run: on Claude
# Code the conversation's capture holds no initialize; on Desktop the live
# shim's file holds no initialize before the mark.
SERVER_DID_NOT_START = "the server did not start (no initialize in the capture)"

# Bounds in code for the driven host, per `claude -p` call (a conversation
# with the fixed second turn is two calls, so twice these), and per batch
# over the host's reported cost (a subscription reports a cost it does not
# bill; the bound reads what the host reports).
MAX_TURNS = 12
PER_TURN_BUDGET_USD = 1.00
PER_CONVERSATION_BUDGET_USD = PER_TURN_BUDGET_USD
BATCH_BUDGET_USD = 10.00
PER_TURN_TIMEOUT_S = 420
PER_CONVERSATION_TIMEOUT_S = PER_TURN_TIMEOUT_S

# The verdict rule's thresholds (KEY.md, the rule verbatim).
# called: T >= n - 1 reads "reliably called"; T == n "called every time".
# verifies: V == T reads "every tool message verified"; V < T parks the tool with its finding.
# fidelity: F == T reads "rendered verbatim"; otherwise reported.
# Also reported, never a condition: C (any accepted call) and K (the count equals the key).
# The verdict is withheld while a host's batch is incomplete.
RELIABLY_CALLED_MISSES = 1


def acceptable(fixture: Fixture, field: str, kind: str) -> bool:
    """Whether a prepare_feedback call's (field, kind) is one the key
    accepts for the fixture."""
    if field == fixture.field and kind in fixture.kinds:
        return True
    if fixture.missing_field_ok and kind == "missing_field":
        category = fixture.field.partition(".")[0]
        return field.partition(".")[0] == category and field != fixture.field
    return False


def ends_with_question(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return bool(lines) and lines[-1].endswith("?")
