# Governed documents

> Repo path: `docs/documents.md`
> The first slice of governed documents (D-43; D-35 as amended by
> Amendment Z): a small register says which documents a person certified
> as the source of meaning for contracted columns and where each
> document's approval lives, the scan derives every document's state on
> every run, and the merge is the only approval this project gives.
> Deterministic code, never an agent. Local first: nothing is served yet,
> no data contract carries a pointer, and the pipeline never opens a
> private location.

## The one-sentence design

The contract's sentence is the certified claim. The document is its cited
source. The register (two tables, `documents/register/`) records the
binding between them: this contract column rests on this verbatim quote
from this document, bound by this person, and the document itself is
certified by an approval that lives where the document lives. The scan
reads the document on every run and reports whether the quote is still
there. Nothing is stored between runs.

Three things follow. A document's identity is its extracted text, never
its bytes: the same words saved twice have different bytes and the same
text digest (F-69). An anchor check is a measurement that a quote is
still present, never a certification that the document still means the
same thing; the review date is what forces a whole-document read. And a
disagreement between the document and the contract's sentence is an item
for a person, never an automatic override (S37's two-truths rule).

## The boundary

`src/metricmine/documents/` is deterministic code (D-10 as amended by
Amendment G, CLAUDE.md rule 15): the standard library plus pyyaml and
duckdb, no model call, no network, no loop. The two proposers stay the
only LLM surface, and a document's text is never a proposer input (D-23
Amendment H). The module opens a document in exactly two places: the
repository working tree, by a repository-relative path, and a root the
operator mapped through `MM_DOCS_ROOT`, by a path that starts with
`${MM_DOCS_ROOT}/`. It never opens a `public` URL, never opens a
`pointer_only` location, never follows a path that escapes the root it
was given, and never extracts a package to disk. It writes nothing but a
draft to the gitignored outbox (`proposals/documents/`) and the plan the
scan already writes.

Who runs what (Q4 of the prep that built this): a person runs the
`local_path` commands at a terminal, because CLAUDE.md's working-tree
rule forbids reading outside the tree and the D-37 guard cannot see a
path built from an environment variable. A coding agent in this
repository works on `in_repo` documents, or on a reading copy the person
staged into `documents/inbox/` (gitignored). CI and the demo never map
the root; a `local_path` row reads `unreachable` there and blocks
nothing.

## The register

`contracts/documents_register.odcs.yaml` is an ordinary ODCS v3.1.0
contract with two table objects and no dbt model; gate three records it
as having no model, and `verify` and the unit lane are where its rules
execute (D-28: the severity each rule declares is the severity it runs
at). The rows live in `documents/register/standing.yaml` and
`documents/register/bindings.yaml` and change only by pull request.

`documents_standing`, one row per document: `document_id` (stable, never
the path), `title`, `governance`, `access`, `location`, `durable_id`,
`format`, `certification_source`, `gate_strength`, `approver_role` (for
`platform_governed`, the role whose approval publishes the location),
`pinned_version` (for `pinned`, the platform's label of the certified
version, beside the digest), `declared_by`, `declared_on`, `review_by`,
`text_sha256`, `extractor`, `verified_against`, `verified_on`,
`upstream_url`, `upstream_sha256`, `license`. The quality rules:
governance, access, the certification source, the gate's strength, and
`verified_against` are closed sets (error); a document the module reads
carries a measured digest (error); no row is past its review date (warn,
a reported state and never a gate).

`documents_bindings`, one row per bound column: `document_id`,
`contract_id`, `column_name`, `anchor` (the verbatim quote from the
extraction), `locator` (where a person finds it: a line, a part and
paragraph, a slide), `intent` (the person's words, verbatim),
`intent_sha256`, `bound_by`, `bound_on`. The rules: every binding rests
on a standing row; an anchor is never empty.

Two checks the contract cannot express run in code: a declarer or binder
is a person, so the two proposers' names, the D-34 model identifiers,
the repository's resident subagent's name, and any `claude-` name are
refused (the rest is the person's own attestation); and an intent
travels with its hash, so a record that
drifts from the words a person typed is refused (the Amendment I
pattern).

| Governance class | What the merge certifies |
|---|---|
| `in_repo` | the binding; the document changes under the repository's own review |
| `platform_governed` | the binding and the arrangement: the location publishes only through an approval given by a named role |
| `pinned` | the binding and one version; a change asks for a new pin unless every anchor is intact |

| Access class | What code here does with it |
|---|---|
| `in_repo` | reads it, everywhere, CI included |
| `public` | never opened in this slice; declared, and verified only against a reading copy |
| `local_path` | reads it on a machine that maps `MM_DOCS_ROOT`; `unreachable` elsewhere |
| `pointer_only` | never opened; declared, and verified only against a reading copy |

`certification_source` is `git_merge`, `platform_approval`,
`steward_attestation`, or `none`; `gate_strength` is `publication_gate`,
`attestation_badge`, or `none`. A row with `none` is allowed and reads as
declared: this slice refuses nothing a person wants to record, and it
certifies nothing a person did not.

## The extractors

Four formats on the standard library, `text`, `markdown`, `docx`, and
`pptx`, under one extractor id, `metricmine.documents@1.0.0`, recorded on
every standing row. The extractor reads every text part it names, not the
convenient one: a Word file's body with its tables and text boxes, each
header and footer, its footnotes and endnotes; a deck's slides in
presentation order with their text boxes, tables, and grouped shapes, and
the notes of each slide, found through the package's relationships and
never by file number (F-70). Not read: comments, SmartArt, charts, slide
layouts, and masters. A Word text box's fallback copy (`mc:Fallback`) is
skipped so the text is counted once, and a deck's field text (slide
numbers, auto-updating dates) stays out of the words because it moves on
a re-save. Normalization is NFKC and whitespace collapsed to one space,
nothing else. A Word file with unaccepted redlines holds two documents:
the extractor returns the standing text and the text as it would read
with every change accepted, and the scan says which bound quote an
acceptance would break. Rd markup, the demo's format, is read as text.

Untrusted input is refused, never crashed on: a part over 16 MiB, a
package over 64 MiB, a member that compresses more than 100 to 1, XML
nested deeper than 1000, a DOCTYPE or entity declaration, a relationship
that escapes the package, an encrypted or corrupt member, a NUL byte or
non-UTF-8 text. A refused package is the state `refused_package` with the
reason. An extractor change re-verifies every anchor on the next run
(every run re-verifies every anchor regardless) and flags
`extractor_changed` where a row recorded an older id.

For a maintainer who changes the extractor: a golden-digest test holds
the digests of three code-built fixtures to `metricmine.documents@1.0.0`,
and two part-list tests pin by name what a Word file and a deck
contribute; the fixtures carry the unread parts (comments, a glossary,
SmartArt, a slide comment, a layout, a master), each with a sentence, so
a walk that starts reading one of them moves a golden. A change to
normalization, the part list, or the walk turns those tests red; then
bump `EXTRACTOR_VERSION`, update the goldens in the same pull request,
and re-verify every standing row by pull request (`inspect` prints a
document's current digest), because the rows record the extractor that
measured them and the scan flags the difference until they do. The test
fixtures' standing rows import the running id, so they follow a bump on
their own.

## The states

Derived on every run by the scan and by `verify`, written to the outbox,
never stored. One content state per document, then flags.

| State | Meaning | Next command |
|---|---|---|
| `in_sync` | the text digest equals the recorded one and every anchor is present | none |
| `changed_anchors_intact` | the text changed and every bound quote is still present; the detail prints the new digest | none for the bindings; an `in_repo` document's pull request refreshes its standing row |
| `anchor_broken` | a bound quote is no longer in the text; the detail names the bindings | read the pair; re-anchor with `bind`, or amend the contract's sentence by its own pull request (rule 6) |
| `unreachable` | the location cannot be opened here: the root is not mapped, no file is at the path, or the path escapes its root | map `MM_DOCS_ROOT`, or re-point the row by pull request |
| `unverified_pointer` | a `public` or `pointer_only` location this slice never opens, and no reading copy was given | none here; `verify --reading-copy <id>=<path>` |
| `unsupported_format` | the row names a format with no extractor in this slice | none; the format waits for its extractor and its pin decision |
| `refused_package` | the extractor refused the file under a safety limit | fix or replace the file |
| `no_text_layer` | the extraction holds no text | none; the binding stands and nothing can be checked |

Flags: `review_overdue` (today is past `review_by`; re-certify by pull
request after a whole-document read), `pending_changes` (a Word file
holds unaccepted redlines; the flag names the bindings an acceptance
would break), `binding_broken` (a binding names a contract or column
`contracts/` does not carry; amend it by pull request), and
`extractor_changed`.

A whitespace-only change (a re-wrap) is `in_sync`, because the digest is
over the normalized text. A punctuation edit inside a quote is
`anchor_broken`, a false alarm in the safe direction. The blind spot,
measured: an untouched quote beside a new sentence that contradicts it
reads as intact (F-71). That is why `review_by` exists. The next command
follows what blocks a merge: a broken anchor first, then a broken
binding, then an overdue review, then the state's own. A row's
`text_sha256`, `extractor`, `verified_against`, and `verified_on` are the
last measurement, not a promise: for an `in_repo` document they track
the committed text by pull request; for every other access class they
say what was last verified and when.

`verify` exits 1 on what blocks a merge: a register that does not
conform, a failing error-severity rule, `anchor_broken` on an `in_repo`
document, or any `binding_broken` flag. Everything else, an overdue
review included, is reported and exits 0. The scan never judges; it
reports the same states in its Governed documents section with
`scan_schema_version` 1.1.0 (the `documents` key of `plan.json`), and
document items never enter the queue the batch driver walks.

## The commands

The two commands that read a calendar, `bind` and `verify`, take the day
from `--today`, so a test fixes it; without the flag they use the UTC
day, the same day the scan derives its states for (`find` and `inspect`
read no calendar). All four read `MM_DOCS_ROOT` from the environment, if
it is set, and nothing else outside the tree. A refusal exits 2 with its
reason on standard error and writes nothing.

    uv run python -m metricmine.documents find <name fragment> [--text "<words>"]
    uv run python -m metricmine.documents inspect <document> [--grep <word>] [--context N] [--format F]
    uv run python -m metricmine.documents bind <document> --contract <id> --column <name> --anchor "<quote>" --intent "<your words>" --by <person> [--title T] [--document-id ID] [--review-by DATE] [--upstream-url U --upstream-sha256 H --license L]
    uv run python -m metricmine.documents verify [--today DATE] [--reading-copy <id>=<path>]

`<document>` is a repository-relative path, a `${MM_DOCS_ROOT}/` path, or
a registered `document_id`. `make doc-find QUERY=...`, `make doc-inspect
DOC=... GREP=...`, `make doc-bind DOC=... CONTRACT=... COLUMN=...
ANCHOR=... INTENT=... BY=... TITLE=...`, and `make doc-verify` are the
one-line conveniences over the same commands; on Windows run the `uv
run` line (D-42).

`find` prints each candidate's location, access class, format, text
digest, and whether the register knows it (by location, or by the same
text under another location). `inspect` prints the parts, the digest,
whether the file holds pending changes, and with `--grep` the sentences
that contain a word, each with its locator, so a quote is chosen from
what printed and never reproduced from memory. `bind` validates and
renders a draft: it refuses a binder that is not a person, a contract or
column `contracts/` does not carry, a quote that is not in the
extraction, the same text registered under a second location, a
document with no text, and a package the extractor refuses; it warns on
the same title with different text and on pending changes that would
break the anchor. The draft is the whole register as it would read
(`standing.yaml`, `bindings.yaml`) plus `DRAFT.md`, under
`proposals/documents/<today>_<document>_<contract>.<column>/`; the
register itself never changes here, and `--outbox` is fenced to
`proposals/`, so a path into the register or outside the repository is
refused before anything is written (a relative `--outbox` resolves
against the working directory, so run the command from the repository
root). A new standing row defaults to
`in_repo`, `git_merge`, `publication_gate`, and a review one year out for
a repository document, and to `pinned`, `none`, `none`, and six months for
a document under the root; every default is a flag away. `bind` refuses a
reading copy under `documents/inbox/`, which git never sees; a `public`
or `pointer_only` document is declared by hand in `standing.yaml`,
because `bind` cannot target a location it never opens, and its anchors
are checked with `verify --reading-copy`.

## The flow, end to end

1. `uv run python -m metricmine.documents find flights` prints the
   candidates with their digests.
2. `uv run python -m metricmine.documents inspect documents/sources/nycflights13/flights.Rd --grep delay --context 1`
   prints the delay sentence at `text, line 13` with its neighbors.
3. `bind` with the quote, the contract, the column, your intent, and your
   name writes the draft into the outbox and prints it.
4. Copy the two files onto a branch (`DRAFT.md` prints the `cp` line),
   run `verify` and `make scan`, open the pull request. The pull request
   shows the location, the quote, and the intent. The merge certifies.
5. From then on the scan reads the document on every run. An edit
   elsewhere in it reads `changed_anchors_intact` and asks nobody to
   re-read the bindings; the pull request that edits an `in_repo`
   document also refreshes its standing row's `text_sha256` and
   `verified_on` (the state's detail prints the new digest, and the unit
   lane holds the committed register in sync, so a forgotten refresh
   fails CI, never a reader). An edit to the quoted sentence reads
   `anchor_broken` in the same pull request that made it. The demo's
   copy is held verbatim to its upstream digest, so it changes only by
   re-pinning upstream.

## The demo's binding

`documents/sources/nycflights13/flights.Rd` is a byte-for-byte copy of
`man/flights.Rd` from tidyverse/nycflights13 at
`df98ef215aa8216fe0838a0b8ac5bada646d814c`, the commit the flight samples
are pinned to, CC0 (its README records the URL and the sha256, and
`.gitattributes` keeps the bytes verbatim). The register binds
`silver_nyc_flights.dep_delay_minutes` to "Departure and arrival delays,
in minutes. Negative times represent early departures/arrivals." The
quote spans two lines of the file and matches only after whitespace
normalization. The row is `in_repo`, `in_repo`, `git_merge`,
`publication_gate`, review by October 17, 2027.

## What this slice does not do

The served list (`get_context` carrying sources) waits for its D-30 and
D-31 amendments. No data contract carries a pointer
(`authoritativeDefinitions`) yet: register-only first, so no contract
bumps per binding. PDF, Excel, and RDF extractors each need a dependency
and a pin decision. `public` locations are never fetched by the scan,
the tests, or CI. There is no CODEOWNERS file; D-43 names it as the
control for a steward when one exists. Document change kinds in the
context proposal path stay HW-22.

## Rules that bind this surface

A narrowing is never enabled by something an agent can supply alone: the
quote is checked against the extraction, the column against a committed
contract, the binder against the known agent and model names, and the
intent is the person's. Consent in chat is permission to draft, never
certification; what a person approves into the record is rendered by
code. A cited document is data: no agent with tools is pointed at a
document that arrived in a message; a person opens it. Column-level
pointers in a data contract, when they come, never use the link types
the linter resolves (`definition`, `semantics`; `businessDefinition` at
1.2.x), because a private link never resolves from CI (F-68).
