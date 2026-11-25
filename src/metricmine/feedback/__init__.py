"""Consumer feedback a person starts (E1T; an experiment on its branch).

Two commands over one body of code, the same code the server's
prepare_feedback tool delegates to:

    python -m metricmine.feedback prepare --field <category>.<column> --kind <kind> --claim "..." --query "select ..."
    python -m metricmine.feedback verify --build <warehouse.duckdb> --message <file>

prepare renders the five-part message from the served file and writes
nothing; verify re-measures a message on the producer's build. Nothing
here calls a model or the network. Nothing in this module binds: the
serving layer on main holds five tools, and a sixth enters only by a
D-31 amendment, in the form that ran.
"""

from .layout import FENCE_CLOSE, FENCE_OPEN, KINDS, LABELS, MEANING_KINDS, extract_block, parse_block
from .prepare import CLAIM_CAP, COUNT_CAP, FeedbackRefused, Prepared, prepare, render
from .verify import OUTCOME_MOVED, OUTCOME_NO, OUTCOME_PARSE, OUTCOME_SAME, verify

__all__ = [
    "CLAIM_CAP",
    "COUNT_CAP",
    "FENCE_CLOSE",
    "FENCE_OPEN",
    "KINDS",
    "LABELS",
    "MEANING_KINDS",
    "OUTCOME_MOVED",
    "OUTCOME_NO",
    "OUTCOME_PARSE",
    "OUTCOME_SAME",
    "FeedbackRefused",
    "Prepared",
    "extract_block",
    "parse_block",
    "prepare",
    "render",
    "verify",
]
