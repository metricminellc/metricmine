"""Governed meaning: the glossary and ontology registers, the binding,
the change-set command (D-44; D-35 as amended by Amendment AC).

THIS IS NOT AN AGENT (D-10 Amendment G, CLAUDE.md rule 15): pure Python
over the standard library plus pyyaml, duckdb, and jsonschema, no model
call, no network, no loop. The two proposers stay the only LLM surface,
and a glossary term or an ontology concept is never a proposer input
(D-23 as amended by Amendment H): no module under the agents package
imports this package or the compiler, and the unit lane holds it.

The boundary, in three sentences. A term or a concept labels meaning and
never drives a join, a key, a type, or a transform; the contract's
sentence stays the certified claim and the term is its label. The two
registers (`meaning/glossary/` under `contracts/glossary_register.odcs.yaml`,
`meaning/ontology/` under `contracts/ontology_register.odcs.yaml`) are
the record and change only by pull request; a term's identity is a
stable id and a content digest over its id, label, and definition, a
concept's a node digest over its id, label, parent, and definition, and
every binding carries the digest it was made at, so the scan derives
each binding's state on every run and stores nothing. This package
writes nothing but a change set's rendering to the gitignored outbox
(fenced to `proposals/meaning/`) and the plan the scan writes; the
person's change set is validated and classified by code, every binding
a changed digest touches is re-bound under the set's recorded intent,
and the pull request is the only approval.

Modules: register (the two registers, their contracts, the digests, the
rules), states (the derived vocabulary the scan reports), changes (the
closed vocabulary of a change set, its validation and classification,
and the rendering), commands (find, show, propose, verify).
"""

from metricmine.meaning.register import GLOSSARY, ONTOLOGY, concept_digest, term_digest

__all__ = ["GLOSSARY", "ONTOLOGY", "concept_digest", "term_digest"]
