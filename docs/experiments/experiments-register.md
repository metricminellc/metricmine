# The experiments register: the deferred design questions of the gold layer

> Repo path: `docs/experiments/experiments-register.md`
> Part B of the experiments and disclosure register, cut August 27, 2026,
> before the v1.0.0 tag, and kept with the planning records past the
> tag. It graduates here, on October 21, 2026, under the stability rule
> (CLAUDE.md rule 19),
> unchanged in meaning: each item carries what was measured, the named
> alternative, the cost, and the reason for deferral, in the shape it
> was left. A status line per item, measured on main at `2f73dfc` on
> October 21, 2026, follows each one. Nothing here binds. An item enters
> the [decision register](../decisions/decision-register.md) only by its
> own documentation pull request, and a measurement that contradicts a
> number here goes to the
> [findings register](../verification/gate_proof_findings.md).

## The standing rule the items were left under

No redesign of the gold layer before the v1.0.0 tag, ruled August 27,
2026. Permitted: documentation, disclosure, positioning, tests, and
every arc already inside the v1.0.0 conditions, Arc 5b among them as
the plan of record then scoped it.
Forbidden before the tag: reopening the D-18 keying, relocating
`line_identity`, renaming `fact_hash_id`, changing the stored payload
bytes, adding a second source, or any other change to the star's shape.
The tag landed on September 2, 2026, and the rule's successor is rule
19: the stable core changes only through the decision register, and
experiments end in written findings.

## The standing recommendation

For whoever opens this lane: treat X-01, X-02, and X-03 as one decision
rather than three banked items. All three are downstream of the same
D-18 question: what goes inside the hashed payload, and what the hash is
computed over. Deciding them separately risks three regenerations and
three moves of the signature-test evidence base.

## X-01. Rename `fact_hash_id`

**Source:** F-24 (Session M, August 14, 2026).

**Measured against the committed demo artifact at the cut:** fact rows
44,721; distinct `fact_hash_id` 2,041; distinct `fact_col_hash_id` 1.
Rule-13 hashing covers the measure payload alone, so every line with the
same quantity and price collides by design. `COUNT(DISTINCT
fact_hash_id)` is wrong as a row count by 95 percent, and the column
name invites exactly that query.

**The problem is the name, not the design.** The composite key stands
(D-18, D-19).

**Named alternative:** rename to `measures_hash_id` or similar.

**Cost:** an engine and contract change with a full regeneration.

**Deferred because:** the trade-off is documented where a reader will
look, and the rename is not worth a regeneration and a moved evidence
base before the tag.

**Status at graduation:** deferred as left. The column is `fact_hash_id`
at head. The reading rule lives in the
[gold spec](../spec/gold-unified-event-star.md) (never
`COUNT(DISTINCT fact_hash_id)`; F-24) and on the face of the
current-state ERD.

## X-02. Relocate `line_identity` onto the fact

**Source:** F-23 (Session M, August 14, 2026).

**Measured at the cut:** fact rows 44,721; dimension rows 44,721;
distinct `dim_hash_id` 44,721. At transaction grain the category
dimension is 1:1 with its fact by construction, because the declared
degenerate identifier rides inside the dimension payload so content keys
stay unique. Content addressing there buys identity and change
detection, not compression. The compression it buys elsewhere is real
and measured: `dim_timeframe_values` at 2,004 rows for 44,721 facts,
`dim_source_values` and `dim_run_values` at one row each.

**Named alternative:** relocate `line_identity` out of the dimension
manifest onto the fact as a true degenerate dimension, restoring dedup
to the category group.

**Cost:** a mapping-contract amendment plus a regeneration that moves
the signature-test evidence base.

**Note added at the register's second revision:** this is a grain
problem, not a source-count problem. Two sources at transaction grain
give two 1:1 dimensions, so X-04 does not absorb this item, and the two
stay separate.

**Status at graduation:** deferred as left. `line_identity` is still the
derived degenerate identifier of the `invoice_lines` mapping contract
(`contracts/gold_invoice_lines_mapping.odcs.yaml`), carried inside the
dimension payload, and the star contract states the 1:1 construction.

## X-03. Case-preserving served payload

**Source:** Amendment M to D-18, minted at Arc 5a. Ruled August 24,
2026.

**The state:** the canonical text is also the served text, so every
value read through the star, its projections, and its marts is
lowercased. Stated deliberately at the serving surface (the
[serving spec](../spec/serving.md) and the server instructions) rather
than changed.

**Named alternative:** hash over the normalized form, store the
original text. Key computation stays byte-identical.

**Cost:** it changes stored bytes and the fixtures.

**Drift note, as left:** an earlier plan line for Arc 5b read "the
case-preserving payload if decided." It was decided at Arc 5a and moved
post-tag, and Arc 5b's prep was not to carry it.

**Status at graduation:** deferred as left. Amendment M stands; string
values on the typed surface are canonical lowercase text, and the
registry, the `query_hint`, and the server instructions say so
(CLAUDE.md rule 18). The Arc 5b and Arc 4 exit records
(`docs/verification/evidence/2026-09-01_arc5b_exit.md`,
`docs/verification/evidence/2026-09-02_arc4_exit.md`) each record that
X-03 stays post-tag.

## X-04. Prove multi-source

**Source:** the August 27, 2026 thread. The only Part B item that
strengthens a claim rather than refining a trade-off.

**The gap at the cut:** one source, one category, one fact table. The
uniform-shape property is the project's headline, and it rested on the
signature test as a proxy.

**In scope by the non-goals:** the standing non-goal was "more than one
or two source types," so a second source is permitted.

**Cheapest form that proves the claim:** two sources unioned in silver
into one category, which demonstrates the exact flexibility the design
promises, plus the schema-key behavior when payload shapes differ.

**Open question, unverified at the cut:** the mapping contract binds one
`sourceTable` per category object. Whether two silver tables can map
into one category without a silver union model had not been checked.
Check this first; it determines whether X-04 is a data exercise or an
engine change.

**Framing note added at the register's second revision:** stop calling
this a demo. It is the experiment that tests the thesis. If two
differently shaped sources land in one category and the star's schema
does not move, the headline is proven. If the one-`sourceTable` binding
forces a silver union first, that is a finding worth having, and it
changes how the property is described. Both outcomes are good outcomes,
which is why it deserves the lane rather than a rushed pre-tag sitting.

**Deferred because:** ruled post-v1 on August 27, 2026.

**Status at graduation:** landed, as D-41 (Decision Record 011,
September 2, 2026), shipped at v1.1.0. A second family of sources, six
public files from two publishers, landed through the one connector
type. Conformance was settled in silver, in human-owned SQL, as unified
tables (`silver_flights`, `silver_airport_weather`), with every join
declared and measured. Conformed keys were declared at the contract
plane and are held by the K1 gate. Three categories build under one
star, one registry, and one conformed calendar. The engine is unchanged
beyond the fan-in and the conformed calendar the record mints. The open
question resolved the way the framing note allowed: a mapping binds one
`sourceTable`, so differently shaped sources meet in a unified silver
table before the category. The claim as it now reads: co-location in
gold, conformance in silver, service through the typed surfaces.

## X-05. The parked pressure-test items

**Source:** the Arc 5 pressure test (August 23, 2026). A pointer, not a
duplicate.

Binary keys, a stored composite fact key to speed the incremental
anti-join (small; it could ride the incremental materialization
decision, D-37 in the planned numbering of August 23 and minted as
D-38), entity-group splitting, a cheaper digest, and a second dbt
thread. Each carries its measured numbers in the pressure-test record,
which is kept with the preparation records outside this repository.

**Status at graduation:** parked as left. [`docs/scale.md`](../scale.md)
carries the measured limits and names binary keys, entity-group
splitting, and the cheaper digest as measured and parked, none built.
The incremental path landed as D-38 with anti-joins on the content keys
(the fact on its full composite) and no stored composite key. The Mac
re-measure in the same document ran on one dbt thread.

## X-06. Prior-art sweep on the generic-modeling framing

**Source:** the August 27, 2026 thread, plus the standing recommendation
from the market research that a prior-art sweep precede finalized
positioning claims. Amended at the register's second revision.

**What to check, in priority order:**

1. The schema-registry analogue. Content-addressed schemas stored beside
   data, with a drift signal from key change. Is this a named published
   pattern inside a warehouse rather than a streaming system?
2. The Data Vault adjacency, and specifically the payload-hash versus
   business-key-hash distinction. Data Vault hashes business keys, so a
   hub's key is stable for the same entity across attribute changes.
   MetricMine hashes the whole payload, so `dim_hash_id` changes when
   any attribute changes. That is closer to a satellite hashdiff than a
   hub hash, and MetricMine has no hubs or links at all. The shared move
   set is real (hash keys, insert-only, structure separated from
   meaning, marts as a derived layer); the keying philosophy differs.
   An earlier revision's looser version of this adjacency is not to be
   repeated.
3. Whether "dimensional intent declared in a governed contract over a
   generic container" is a named pattern anywhere.

**Note:** it is research, it touches no code, and it was the one Part B
item permitted to move earlier, into a paperwork slot before Arc 3.
Nothing about modeling-family adjacency goes into public copy before
the sweep runs.

**Status at graduation:** open as left. No record of the sweep is in the
repository, and no public surface in the repository claims a modeling
family as prior art: Data Vault is named nowhere, and "schema registry"
appears only as the gold star flow diagram's label for the columns
dimensions (in its source and its rendered files), not as a claim of
adjacency to a published pattern.
