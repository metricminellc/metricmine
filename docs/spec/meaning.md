# Governed meaning

> Repo path: `docs/spec/meaning.md`
> The implementing slice of governed meaning (D-44; D-35 as amended by
> Amendment AC): two small registers say which business terms and which
> concepts a person certified as the labels of contracted elements, each
> binding carries the label's content digest as it read when the binding
> was made, the scan derives every binding's state on every run, a change
> set a person runs through one command renders the registers as they
> would read, and the merge is the only approval this project gives.
> Deterministic code, never an agent. Nothing here is served yet: the
> slice that serves meaning amends D-30 and D-31 (the section "What this
> slice does not do").

## The one-sentence design

The contract's sentence stays the certified claim. The term or the concept
is its label. The registers (`meaning/glossary/`, `meaning/ontology/`)
record each label with a content digest and record the binding between a
label and a contract element: this element carries this term, as the term
read when the binding was made, bound by this person with these words. The
scan compares the digest on every run and reports whether the label still
reads as it did. Nothing is stored between runs.

Three things follow. Identity is a stable id and a content digest, so a
re-wrapped definition keeps its digest and a changed word moves it. A
changed definition is never neutral: the command re-binds every element
that cites it under one recorded intent, each re-bind listed by name for
the reviewer, and a binding left behind by a hand edit reads
`term_changed` and blocks the merge. And meaning is descriptive only: a
term or a concept labels an element and never drives a join, a key, a
type, or a transform; when a term's definition and a contract's sentence
disagree, the contract's sentence is the certified claim, no state detects
the disagreement, the review date is what forces a read, and the
disagreement is an item for a person, never an automatic override (the
two-truths rule D-43 took, restated for terms).

## The boundary

`src/metricmine/meaning/` is deterministic code (D-10 as amended by
Amendment G, CLAUDE.md rule 15): the standard library plus pyyaml,
duckdb, and jsonschema, no model call, no network, no loop, no MCP tool.
jsonschema is the dev group's validator the proposer harness already
reads; `propose` imports it where it validates a change set, and `find`,
`show`, `verify`, and the scan never load it.
The two proposers stay the only LLM surface, and a glossary term or an
ontology concept is never a proposer input (D-23 as amended by Amendment
H): no module under the agents package imports this module or the
compiler, and the unit lane holds it, as it holds for documents. The
module reads the two register contracts, the four register files, and
the committed contracts under `contracts/` (never the warehouse). It
writes nothing but a change set's rendering to the gitignored outbox
(`proposals/meaning/`) and the plan the scan already writes. The
registers are the record and change only by pull request; a declarer, a
binder, an owner, or a change set's `by` is a person, and code refuses
the agent and model names it knows (the two proposers' names, the D-34
model identifiers, the resident subagent's name, and any `claude-` name);
the rest is the person's own attestation. A value in a file or on a make
line is something an agent can supply, `by` and `intent` included,
exactly as `bind --by` is for documents; the pull request is where a
person refuses a set that is not theirs.

The host door is a command, not a tool: the host's agent reads what
exists (the register files, `find`, and the served context through the
five tools), drafts the change set, asks for consent, and runs
`propose`; no MCP tool is added, the `mm` entry point is not widened
(D-42), and a sixth tool would need a D-31 amendment and a measured
need. Consent in chat is permission to draft, never certification; what a
person approves into the record is rendered by code; text gathered from
a chat or a pasted document is untrusted, labeled authored, never
executed, and read by a person before merge.

## The registers

Two ordinary ODCS v3.1.0 contracts with two table objects each and no dbt
model; gate three records them as having no model, and `verify` and the
unit lane are where their rules execute (D-28: the severity each rule
declares is the severity it runs at). The rows change only by pull
request. A register's rows change under the register's digest with no
contract version bump of their own; the register contract's version
moves when its schema or its rules move (D-08 as usual).

`contracts/glossary_register.odcs.yaml`, rows under
`meaning/glossary/terms.yaml` and `meaning/glossary/bindings.yaml`.
`glossary_terms`, one row per term: `term_id` (stable; lowercase letters,
digits, and underscores; never the label), `term` (the term as people
say it), `definition` (in the owner's words), `synonyms` (separated by
`; `; a synonym belongs to one term and never equals a term's label;
served, never hashed), `owner` (a person or a team), `status` (`active`
or `deprecated`), `superseded_by` (on a deprecated row, the id of the
term that replaces it, when one exists), `declared_by`, `declared_on`,
`review_by`. `glossary_bindings`, one row per contract element a term
labels: `term_id`, `contract_id`, `column_name` (the empty string for the
table itself), `term_sha256` (the term's digest when the binding was
made), `intent` (the person's words, verbatim), `intent_sha256`,
`bound_by`, `bound_on`.

`contracts/ontology_register.odcs.yaml`, rows under
`meaning/ontology/concepts.yaml` and `meaning/ontology/bindings.yaml`.
`ontology_concepts`, one row per concept: `concept_id`, `label`,
`parent_id` (a concept the register carries, never the concept itself,
or none at a root; the parent graph has no cycle), `definition`, and the
same governance fields. `ontology_bindings`, one row per element a
concept labels, with `concept_sha256` in place of the term's digest; an
element carries one concept, a table's concept being its entity type and
a column's what the column carries.

The quality rules, at `error` severity: the status is a closed field; an
id is unique and is lowercase letters, digits, and underscores; a label
is unique; a synonym is owned by one term and never equals a term's
label; only a deprecated row names a `superseded_by`, and
it names a row the register carries; a parent is a concept the register
carries and never the concept itself; the parent graph has no cycle
(measured by a recursive rule); every binding names a row the register
carries; a binding carries a 64-character digest; a glossary binding is
unique per term and element and an element carries one concept. At
`warn`, never a red gate: no row is past its review date. Ten rules on
the glossary, eleven on the ontology. The SQL rules compare a label and
a synonym by `lower(trim())`, a narrower normalization than the
command's (NFKC, whitespace, and case), so the command is the stricter
check and runs first; a pair the rule would pass and the command refuses
never reaches a pull request through the command. Two checks the
contracts cannot express run in code: a declarer, an owner, or a binder
is a person, and an intent travels with its hash, so a record that
drifts from the words a person typed is refused (the Amendment I
pattern). An orphaned binding
(a row the register no longer carries) is a rule's finding and a
state's reading, never a load failure, so the scan can say
`term_missing` instead of refusing to look.

## The digests

A term's digest is the sha256 of the canonical bytes of its `term_id`,
`term`, and `definition`, each NFKC- and whitespace-normalized, and
nothing else: synonyms, the owner, the status, and the dates never enter
it, so adding or removing a synonym or deprecating a term moves no
binding. A concept's digest is a node digest over `concept_id`, `label`,
`parent_id` (the empty string at a root), and `definition`: a parent
change re-asks the bindings of the concept whose parent moved and not its
descendants', because the ancestor path is not hashed. The canonical
bytes are the profiler's (`metricmine.profiling.canonical.canonical_bytes`:
sorted keys, two-space indent, UTF-8, a trailing newline), the form the
Prep H probe measured; the unit lane pins the demo's thirteen digests
(six terms, seven concepts) to the probe transcript's values. A re-wrapped or differently normalized
definition keeps its digest; a changed word moves it.

## The states

Derived on every run by the scan and by `verify`, written to the outbox,
never stored. One state per binding, then the flag.

| State | Meaning | Next command |
|---|---|---|
| `in_sync` | the row's current digest equals the one the binding recorded and the element is in a committed contract | none |
| `term_changed`, `concept_changed` | the digest moved under a standing binding (a hand edit changed the definition, the label, or the parent without a re-bind) | re-bind by pull request: a change set with `bind` (or `bind_concept`) for the element re-renders the row at the current digest under your intent; or restore the definition |
| `term_missing`, `concept_missing` | the binding names a row the register no longer carries | amend the binding by pull request: restore the row, or unbind the element in a change set |
| `term_deprecated`, `concept_deprecated` | the row's status is `deprecated`; the detail names `superseded_by` when one exists | none required; move the binding to the successor in a change set when one stands |
| `binding_broken` | the binding names a contract or column `contracts/` does not carry | amend the binding by pull request |

The flag `review_overdue` rides beside the state when the cited row's
`review_by` is past the run's day; every binding that cites an overdue
row carries it, and `verify` reports the rows themselves through the
contract's `warn` rule. The next command follows what blocks a merge: a
missing row first, then a broken binding, then a moved digest, then an
overdue review, then the state's own. No next command routes a term or a
concept into a proposer.

`verify` exits 1 on what blocks a merge: a register that does not
conform (a row outside its contract's columns, a required column
missing, a date that does not parse, a declarer, owner, or binder that
is not a person, an intent that drifted from its hash), a failing
error-severity rule, a `term_changed`, `concept_changed`,
`term_missing`, or `concept_missing` binding, or a `binding_broken` one.
Everything else, a deprecation and an overdue review included, is
reported and exits 0. The scan never judges; it reports the same states
in its Governed meaning section with `scan_schema_version` 1.2.0 (the
`meaning` key of `plan.json`: each register's standing, the counts in a
fixed order, and one item per binding with its next command), and
meaning items never enter the queue the batch driver walks. The gate of
record is the unit lane's test that every committed register conforms,
every rule passes, and every committed binding reads `in_sync`, or
`term_deprecated` or `concept_deprecated` when its row's status says
so, with no flag for a fixed day; `verify` is the person's local form
of it. A deprecation under a standing binding is a declared state
between the two merges of deprecate-then-drop (HW-35), not drift, so
the gate reads it as the register's own word and `verify` reports it
without blocking. So a register on main is always self-consistent:
`term_changed` is a working-tree state a pull request clears before it
merges, and the command never produces one.

## The commands

The two commands that read a calendar, `propose` and `verify`, take the
day from `--today`, so a test fixes it; without the flag they use the UTC
day, the same day the scan derives its states for (`find` and `show`
read no calendar). A refusal exits 2 with its reason on standard error
and writes nothing.

    uv run python -m metricmine.meaning find <text>
    uv run python -m metricmine.meaning show <term_id or concept_id>
    uv run python -m metricmine.meaning propose <file> [--today DATE] [--outbox proposals/meaning/<name>]
    uv run python -m metricmine.meaning verify [--today DATE]

`make meaning-find QUERY=...`, `make meaning-show ID=...`, `make
meaning-propose CHANGES=<file>`, and `make meaning-verify` are the
one-line conveniences over the same commands; on Windows run the `uv run`
line (D-42).

`find` prints every term and concept whose id, label, definition,
synonyms, or parent id contain the text, each with its status and its carried-by list
(which elements carry it), derived from the bindings and never authored,
so it cannot rot. `show` prints one row with its digest, its bindings,
and their states. `verify` prints both registers' standing, every rule
with its result, every binding with its state, its flags, and its next
command, and the result.

## The change set

A context proposal is a declared change set: a YAML file, by convention
`proposals/meaning/<name>.changes.yaml`, carrying `by` (the person's
name), `intent` (the person's words, verbatim), and `changes`, a list in
the closed vocabulary, each with its fields and a `rationale`. The file's
shape is the committed schema `docs/spec/meaning/change-set.schema.json`
(the vocabulary's enum, each kind's required fields); every check a
schema cannot express runs in code, in order, against a working copy of
the two registers, so a change may name a row an earlier change in the
same set added. The class of a kind is what it re-asks of people:

| Kind | Register | Class | What code checks |
|---|---|---|---|
| `add_term` | glossary | additive | the id is well formed and free; the label and each synonym are owned by nobody; the owner is a person or a team; `review_by`, a bare date or text, defaults to one year from the day and an impossible date is refused |
| `amend_definition` | glossary | changing | the term exists; the text differs after normalization; every binding re-bound |
| `rename_term` | glossary | changing | as above; the new label is owned by nobody, its own synonyms included (remove the synonym earlier in the set; the old label may become a synonym by an `add_synonym` later in the set); a change of case or spacing alone is a rename, because the label is served as written |
| `add_synonym` | glossary | additive | owned by nobody; not already on the term |
| `remove_synonym` | glossary | additive | the synonym is on the term |
| `deprecate_term` | glossary | removing, step 1 | the term is active; `superseded_by`, when given, names a term the register carries or the set added earlier, and never the term itself |
| `drop_term` | glossary | removing, step 2 | the term reads deprecated in the committed register (a deprecation in the same set is refused: deprecate, merge, then drop); no binding stands |
| `bind` | glossary | additive | the term exists; the element exists in a committed data contract (`contract_id`, and `column_name` or the empty string for the table; the two register contracts are never elements); not already bound to this term at its current digest (a standing binding whose term moved is re-bound, and that re-bind is classed changing); a bind to a deprecated row is allowed and its note says so |
| `unbind` | glossary | removing | the binding exists |
| `add_concept` | ontology | additive | the id is well formed and free; the label is owned by nobody; the parent, when given, exists and is not the concept itself; the owner is a person or a team; `review_by` as `add_term`'s |
| `amend_concept` | ontology | changing | the concept exists; the definition differs, or the parent moves (an empty `parent_id` moves it to a root; the new parent exists, is not the concept itself, and closes no cycle); every binding re-bound |
| `relabel` | ontology | changing | as above; the label is owned by nobody |
| `deprecate_concept`, `drop_concept` | ontology | removing, two steps | as the glossary's; a drop is also refused while a child names the concept as parent |
| `bind_concept` | ontology | additive | the concept and the element exist; the element carries no other concept (unbind it first) |
| `unbind_concept` | ontology | removing | the binding exists |

The five document kinds D-44 enumerates (`add_document`,
`bind_document`, `unbind_document`, `recertify_document`,
`retire_document`) are in the schema's vocabulary and refused here by
name: they ride the slice that serves governed meaning, and until then a
document change beyond `bind` is a hand edit a reviewer reads. `by` is a
person; `intent` is non-empty; a set with no change is refused; a field
a kind does not read is refused by name, so a misspelled field never
passes silently.

What `propose` does, in order: holds the committed registers to their
contracts' error rules first, naming the rule, so a set is never applied
over a register that already fails; validates the file against the
schema and the document kinds by name; applies each change to the
working copy with the checks above, classifying it; then re-binds every
binding whose row's digest this set moved, a binding the set itself made
earlier included when a later change moved the row again, under the
set's `intent`, `by`, and day, listing each by name (a binding already
stale when the set started is left as it was and reported as standing
drift, and an explicit `bind` re-binds it); holds the rendered registers
to their contracts' error rules and the person checks, and derives every
rendered binding's state, refusing the whole set on any rule failure or
on a `term_changed` or `concept_changed` it did not report as standing
drift; and renders into
`proposals/meaning/<name>/` (named from the file's stem so a repeated
draft overwrites itself and no clock is read) the four register files as
they would read (`glossary/terms.yaml`, `glossary/bindings.yaml`,
`ontology/concepts.yaml`, `ontology/bindings.yaml`), `record.json` (the
set verbatim, the intent verbatim and hashed, the classification per
change, the re-bound elements by name, the standing drift, the register
digests before and after, the rendered files' digests, who and when, the
module's id), and `summary.md` for the pull request body. Every file is
written as UTF-8 bytes with the LF line endings the renderer produced,
on every platform and never through a text mode that translates them,
so each rendered file's digest in `record.json` is the digest of the
file as written (F-75). Nothing under `meaning/` or `contracts/` is
touched; `--outbox` is fenced to
`proposals/meaning/`, so a path into the registers or outside the
repository, the outbox folder itself, or any symbolic link on the way to
the draft or at a file it writes is refused before anything is written
(every path the command will write is checked before the first write,
so a refusal leaves nothing but the planted link behind; F-74, the
documents module's draft shared the defect and the fix); the
command digests `meaning/` and `contracts/` before and after it writes
and prints that they are unchanged only when the two digests are equal
(design rule 5); and the command has no flag that certifies anything and
no flag that relaxes a check.

## The flow, end to end

1. Discuss freely; nothing is recorded. `uv run python -m
   metricmine.meaning find delay` prints what exists and what carries
   it.
2. Write the change set (a coding host's agent may draft it) with the
   person's `by` and `intent`.
3. `make meaning-propose CHANGES=proposals/meaning/<name>.changes.yaml`
   validates, classifies, re-binds, and renders; the summary lists every
   change and every re-bind by name. A refusal names its reason and
   writes nothing.
4. Copy the rendered files onto a branch (the summary prints the `cp`
   lines), run `verify` and `make scan`, open the pull request with the
   summary in its body. The reviewer reads the definition diff and each
   re-bound element beside it; the unit lane holds the registers to their
   contracts and every binding to its row; the merge is the only
   approval.
5. From then on the scan derives every binding's state on every run. A
   hand edit to a definition reads `term_changed` in the same pull
   request that made it, and the unit lane blocks the merge until a
   change set re-binds the element or the definition is restored.

## The demo's registers

Six terms and seven concepts from the two public sources, nycflights13
and OurAirports, in the steward's own words (`aviation stewards` is the
owner of every row): departure delay, arrival delay, carrier, tail
number, airport identifier, and cancellation; flight, airport, aircraft,
airport weather observation (under airport), and delay (under flight)
with departure delay and arrival delay under it. The Prep H probe
fixture also carried the retail sample's invoice line; D-44 names the
two public sources as the demo's vocabulary, so that row and its binding
are not committed and the unit lane holds every owner to the aviation
stewards. Seven glossary bindings: the four column terms and the
table-level cancellation term on `silver_flights`, the unified flights
contract the compiled context serves, plus two level-zero rows kept as
the recorded-and-reported examples (`departure_delay` on
`silver_nyc_flights.dep_delay_minutes`, `airport_ident` on
`silver_ourairports_airports.airport_ident`). Four ontology bindings:
the entity types Flight on `silver_flights` and Airport weather
observation on `silver_airport_weather`, the Departure delay concept on
`silver_flights.dep_delay_minutes`, and the level-zero example Airport
on `silver_ourairports_airports`. Eleven bindings in all: eight on the
mapped silver contracts and three level-zero examples. Every row is
declared and bound by `justinrgoff` on October 26, 2026, review by
October 26, 2027. The rows are the Prep H probe fixture less the invoice
line, and the unit lane pins their digests and the glossary register's
digest to the probe transcript's values.

## What this slice does not do

Nothing is served: `get_context` carries no term and no concept until
the slice that serves meaning amends D-30 and D-31 (the `meaning` block
beside `documents`, the per-field `terms` and `concept` lists, the
served edges, the budget's number, the freshness check's two new
sources, the compiled schema's next version). The five document change
kinds are refused by name until that slice lands them. No data contract
carries a pointer (`authoritativeDefinitions`): the binding lives in the
register first, and the column-level pointer, when it comes, is rendered
from the register by its own slice with opaque link types only (F-68).
No import of a spreadsheet glossary or a SKOS file. There is no
CODEOWNERS file; D-44 names it as the control for a steward when one
exists. A contract pull request that renames a bound element carries the
register's re-pointed rows, because the unit lane would otherwise block
the rename (D-44); the silver contracts' naming convention is a Backlog
item.

## Rules that bind this surface

A narrowing is never enabled by something an agent can supply alone: the
element is checked against a committed contract, the row against the
register, the label and the synonyms against what exists, the author
against the known agent and model names, and the intent is the person's.
Consent in chat is permission to draft, never certification; what a
person approves into the record is rendered by code. A term or a concept
is data: it is declarative, labeled authored, never executed, and never a
proposer input. The server never prints an assurance it cannot check:
when a term is served, the note will say what the compile checked and
never that a term is current.
