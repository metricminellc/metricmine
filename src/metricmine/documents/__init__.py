"""Governed documents: the deterministic foundation (D-43).

THIS IS NOT AN AGENT (D-10 Amendment G, CLAUDE.md rule 15): pure Python
over the standard library plus pyyaml and duckdb, no model call, no
network, no loop. The two proposers stay the only LLM surface. This
package reads a document the register names, extracts its text, measures
whether the quotes the contracts rest on are still there, and derives a
state on every run; it writes nothing but a draft to the gitignored
outbox (D-24) and the plan the scan already writes (D-35 as amended).

The boundary, in three sentences. A document's identity is its extracted
text, never its bytes: the same words saved twice have different bytes
and the same text digest. This package opens a document only in the
repository working tree or under a root the operator mapped through
MM_DOCS_ROOT; it never opens a private location, never fetches a URL, and
never follows a path that escapes the root it was given. The register
(documents/register/, under contracts/documents_register.odcs.yaml) is
the record, the merge is the only approval, and every derived state is
written to the outbox and never stored.

Modules: extract (the text extractors and the package safety limits),
register (the two tables and their contract's rules), states (the derived
vocabulary the scan reports), commands (find, inspect, bind, verify).
"""

from metricmine.documents.extract import EXTRACTOR, EXTRACTOR_VERSION, FORMATS

__all__ = ["EXTRACTOR", "EXTRACTOR_VERSION", "FORMATS"]
