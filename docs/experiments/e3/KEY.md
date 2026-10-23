# E3 key: the skeleton and the context channel on the proposers' API path

> Repo path: `docs/experiments/e3/KEY.md`
> The experiment's key: the questions as measurable claims, the arms,
> the fixtures with their oracles, the context texts, the leakage check,
> the spend bound, what is a result and what is a technical failure, the
> error-class table, and the verdict rule for each question. Written
> before run one, read by two independent reviewers before run one
> (October 21, 2026; the dispositions are in the prep's audit record),
> committed in one commit whose hash the finding quotes. Nothing in this
> file binds: the experiments lane's rule
> ([`docs/experiments/README.md`](../README.md)) holds, and a graduation
> is a register amendment by its own documentation pull request, in the
> form it ran.

## 1. The questions, as measurable claims

**E3a, the context channel (HW-15).** A few sentences of operator
context, carried as one more governed input (hashed, recorded verbatim,
rendered inside its own delimiter tag after the evidence, as data), move
the cleanup proposer's first-class agreement off `0/0` on the three
fixtures that share no column name with their oracles, without lowering
the first-attempt lint rate, the first-attempt groundedness rate, or any
other oracle-bound fixture's agreement, and the move is the context's,
not the prompt edit's. The care: the context is written from the
sources' own documentation and the team's naming conventions, never from
the oracle contract; a counter reports every oracle column name a
context carries verbatim and every oracle-only name whose parts the text
carries (Section 5). Composition is the mechanism under test: the text
gives the parts and the conventions say how to join them, and the
question is whether the proposer uses them.

**E3b, the skeleton (HW-14).** When code writes the machine half of a
describe or amend proposal (every profiled column in profile order with
the profiled physical type, `required` equal to `null_rate == 0.0`, the
logical type from the validator's fixed map, the two fixed table rules
for describe; the committed contract's columns as they stand for amend),
and the model emits only the judgment over it, first-attempt
machine-half validation errors are zero by construction (a theorem the
keyless test proves on every committed silver profile; the live arm
checks it and measures the rest), the judgment error rate does not rise,
agreement does not fall, and the output-token split between structure
and judgment is measured on live calls rather than estimated from one
example.

Both questions are read against the Arc 6 agreement study (D-25,
September 5, 2026) with one variable changed at a time, scored by the
unchanged scorer (`src/metricmine/agents/agreement.py`), at
`claude-sonnet-5`, with repeats, so the finding reports rates with their
spread.

## 2. The arms

An arm is one row of [`arms.yaml`](arms.yaml): a prompt set, a context
switch, a skeleton switch, a model rule, a fixture list, and a repeat
count. `make eval-agents ARM=<arm> REPEATS=<n> [MODEL=<id>]` runs one
batch: every fixture of the arm, `<n>` attempts each, one structured
call per attempt with the harness's own bounded retry, in the fixture
order the arm declares. The runner prints the spend bound before the
first call and one reported line per run.

| Arm | Prompts | Context | Skeleton | Fixtures | Repeats | Model |
|---|---|---|---|---|---|---|
| `baseline` | head's four prompts at 1.0.0 and head's schemas | off | off | the eleven of `agents.eval.fixtures` at head, in their order | 10 | `claude-sonnet-5`; the control (Section 7) re-runs this arm at `claude-opus-5` and `claude-fable-5`, 5 repeats each |
| `A` | the E3 cleanup and mapping prompts at 1.1.0 (the payload paragraph names `<operator_context>`), head's schemas | on, from the committed context file each fixture names | off | the eight oracle-bound fixtures | 10 | `claude-sonnet-5` only |
| `A0` | the E3 cleanup prompt at 1.1.0 | off | off | the three `0/0` fixtures | 10 | `claude-sonnet-5` only |
| `A1` | the E3 cleanup prompt at 1.1.0 | on, from the docs-only context file (the same text without its four conventions sentences) | off | the three `0/0` fixtures | 10 | `claude-sonnet-5` only |
| `B-baseline` | head's describe and amend prompts at 1.0.0 and head's table-contract schema | off | off | the three describe and amend fixtures | 10 | `claude-sonnet-5` only |
| `B` | the E3 describe and amend prompts at 1.1.0 and the judgment schema | off | on | the same three | 10 | `claude-sonnet-5` only |

`A0` and `A1` are the Architect's additions, not thread-prompt defaults.
Arm `A` changes two things against the baseline, the prompt's payload
paragraph and the presence of a context, so `A0` runs the 1.1.0 prompt
with no context on the three fixtures the question is about: its user
payload is byte-identical to the baseline's (measured by the dry path),
so it isolates the paragraph. If `A0` moves agreement off `0/0` by
itself, the paragraph did it, not the context, and E3a is not earned
(rule 4, Section 9). `A1` separates the two halves of a context, the
documentation sentences and the conventions sentences; it is reported
beside the verdict and is never a condition.

The order of the batches: sitting 1 runs `baseline` at sonnet, then `A`,
then `A0`, then `A1`, then `baseline` at opus, then `baseline` at fable;
sitting 2 runs `B-baseline`, then `B`, then the scoring. If the window
or the bound tightens, batches are dropped from the end of sitting 1's
list: fable first, then opus, then `A1`; dropping any of the three
changes no verdict (the scorer keys every verdict cell on the default
model, and `A1` is reported only). A batch is one `make` line; its
printed lines are reported, never matched.

## 3. The fixtures and their oracles

The eight oracle-bound fixtures and the three without an oracle are the
eleven of `agents.eval.fixtures` at head (`config/default.yaml`), their
profiles and oracles unchanged, re-declared in `arms.yaml` label for
label (a test holds the two lists equal). The three `0/0` fixtures,
named in `arms.yaml` as `zero_fixtures`:

| Fixture | Profile | Oracle | Arc 6 reading (agree/checked, mismatches) |
|---|---|---|---|
| `silver-cleanup-nyc-flights` | `profiles/bronze.nyc_flights/v0001.json` (19 columns and 3 metadata columns) | `contracts/silver_nyc_flights.odcs.yaml` (19 columns, 1.0.0) | `0/0`, 38 |
| `silver-cleanup-nyc-weather` | `profiles/bronze.nyc_weather/v0001.json` (15 and 3) | `contracts/silver_nyc_weather.odcs.yaml` (14, 1.0.0) | `0/0`, 29 |
| `silver-cleanup-nyc-airlines` | `profiles/bronze.nyc_airlines/v0001.json` (2 and 3) | `contracts/silver_nyc_airlines.odcs.yaml` (3, 1.0.0) | `0/0`, 5 |

The five others watched for regressions: `silver-cleanup-nyc-planes`
(`10/10`, 15; 2 shared names), `silver-cleanup-ourairports-airports`
(`61/65`, 15; 12 shared), `silver-cleanup-ourairports-runways`
(`30/30`, 18; 4 shared), `mapping-propose-flights` (`131/132`, 3),
`mapping-propose-airport-weather` (`67/68`, 3). Measured at head on
October 21, 2026: the shared-name counts above, by comparing each
profile's non-metadata column names to its oracle's property names.
Checked is the shared names times five first-class fields for a table
contract (`logicalType`, `physicalType`, `required`, `primaryKey`,
`primaryKeyPosition`) and times four for a mapping contract
(`mappingRole`, `logicalType`, `physicalType`, `required`).

The three new fixtures for E3b, declared in `arms.yaml` and runnable
only by the branch's eval lane (head's lane builds cleanup and propose
fixtures only):

| Fixture | Stance | Profile | Committed input | Intent | Oracle |
|---|---|---|---|---|---|
| `describe-silver-flights` | describe | `profiles/silver.silver_flights/v0001.json` (34 columns) | none | none | `contracts/silver_flights.odcs.yaml` (1.0.0, hand-authored, `proposedBy: human`, with Arc 6's describe draft as its evidence) |
| `describe-silver-airport-weather` | describe | `profiles/silver.silver_airport_weather/v0001.json` (18 columns) | none | none | `contracts/silver_airport_weather.odcs.yaml` (1.0.0, hand-authored the same way) |
| `amend-silver-invoice-lines-f28` | amend | `profiles/silver.silver_invoice_lines/v0002.json` (10 columns; `captured_at` at null rate 0.0 over 44,721 rows) | `docs/experiments/e3/fixtures/silver_invoice_lines@1.2.0.odcs.yaml`, the committed contract before #160, byte for byte from `6ad6e86` (sha256 `65c6ffd6dc4668cf94c502a9dc39b912603d73d635d95fea820865b099404391`) | the F-28 tightening, in the operator's words (Section 4) | `contracts/silver_invoice_lines.odcs.yaml` (1.3.0, the contract after #160) |

The describe fixtures run on the branch's eval path, which builds the
describe spec directly and never evaluates the CLI's duplicate-id
refusal; the draft's version is the regeneration bump over the existing
contract and is unscored. For the describe fixtures the machine half
(types, required flags, column order) equals the oracle's on every
column by construction under both arms, so agreement there measures the
grain choice (`primaryKey`, `primaryKeyPosition`) and nothing else; the
grain set-equality rate is reported beside it (Section 9). The amend
fixture binds the 1.2.0 document as its `committed_contract` input and
stamps `amendsContract` over its bytes; the validator holds the
re-emitted machine half to that document, and the scorer compares the
rendered draft to the 1.3.0 oracle, where agreement measures whether
the declared change was made (49 or 50 of 50 for any written draft).

## 4. The context texts, and the amend intent

One file per arm-`A` fixture under [`contexts/`](contexts/), and one
docs-only file per `0/0` fixture under [`contexts/docs-only/`](contexts/docs-only/)
for arm `A1`, committed on the branch, read by the eval lane from the
path the fixture declaration names, as bytes decoded, hashed over those
bytes (`sha256:`, as Amendment I hashes the intent), recorded verbatim
in the proposal record with the path, re-read and re-hashed before the
draft is written (a moved file fails closed), and rendered inside
`<operator_context>` after every other governed input. Each text is
three to seven sentences in this shape: what the source is, in the
publisher's words as [`docs/sources.md`](../../sources.md) and the
extract's README cite it; the documented meaning and unit of the
columns whose names do not carry one, in the publisher's documentation's
words; and the team's naming conventions, stated as conventions. A
context never names a target column verbatim, never lists the oracle's
columns, never states the grain, and never quotes the oracle contract;
no context carries a `<` character, so no tag can be forged. The six
cleanup contexts end with these four sentences, in the same words:

> We name a measure with its unit as a suffix (minutes, miles, mph,
> inches, degrees, feet, percent). We name a code column with `_code`
> and a boolean with `is_`. We carry a calendar date as one DATE column
> rather than three integer parts. We spell out abbreviated column
> names.

The two mapping contexts end instead with "We keep every field name as
the silver contract names it.", because a mapping proposal keeps the
silver names, and carry only what `docs/sources.md` states about the
unified tables (their sources and their declared joins). The
conventions above fit the three `0/0` oracles and misfit some names in
the airports and runways oracles (`latitude_deg`, `elevation_ft`,
`length_ft`, `iso_country`, `has_scheduled_service` do not follow
them); the finding reads those two fixtures with that in mind.

The committed texts at the key's commit, by size and sha256 prefix,
pinned here so a later reader can check the ledger's `context_hash`
against the key: `silver-cleanup-nyc-flights` 1,238 bytes
`9708ec857fa28308`; `silver-cleanup-nyc-weather` 1,080 `919ea6837199b5a3`;
`silver-cleanup-nyc-airlines` 587 `540c7f03c22a6ac0`;
`silver-cleanup-nyc-planes` 907 `7b8c5eca89109714`;
`silver-cleanup-ourairports-airports` 1,469 `2489eab77d3fdb81`;
`silver-cleanup-ourairports-runways` 1,442 `5fb5712e5e64337e`;
`mapping-propose-flights` 508 `75279986162cfab7`;
`mapping-propose-airport-weather` 479 `b43024d0a540798d`; docs-only
`silver-cleanup-nyc-flights` 962 `527710b17e4211df`,
`silver-cleanup-nyc-weather` 804 `6e48de7d4b1a63ef`,
`silver-cleanup-nyc-airlines` 311 `e5ab980ba32ec9a9`.

The amend fixture's intent, recorded verbatim:

> The incremental path has landed and every row carries captured_at;
> the fresh profile measures it at null rate 0.0 over 44,721 rows.
> Tighten captured_at to required and say in its description why it is
> required now. Change nothing else.

## 5. The leakage check

`make e3-leakage` (`python -m metricmine.agents e3-leakage`) reads every
context text, tokenizes it into identifier tokens (`[a-z][a-z0-9_]*`,
lower-cased), and counts, per file, the oracle's column names in three
groups: names the profile also carries that appear verbatim (shared
names, which a context naturally uses when it explains a source column);
names only the oracle carries that appear verbatim (oracle-only names);
and names only the oracle carries that do not appear verbatim but every
underscore part of which is a token, or a token's underscore part, in
the text (composable names: `dep_delay_minutes` when the text carries
`dep_delay` and `minutes`). It prints one line per file and exits 0
always: the counts are observations the finding reports. The bar this
key sets, held by a test on the committed texts: **zero verbatim
oracle-only names in every context**. The composable count is not a
bar: composition is the mechanism under test (Section 1), and a high
count says the text carries the parts, not that the proposer will join
them. A context that fails the bar is rewritten before run one; after
run one the texts are frozen with this key.

Measured on the committed texts at the key's commit (oracle columns,
of which not in the profile; shared verbatim; oracle-only verbatim;
composable): `silver-cleanup-nyc-flights` 19 of which 19; 0; 0; 17
(docs-only 16). `silver-cleanup-nyc-weather` 14 of which 14; 0; 0; 5
(docs-only 5). `silver-cleanup-nyc-airlines` 3 of which 3; 0; 0; 2
(docs-only 1). `silver-cleanup-nyc-planes` 10 of which 8; 2; 0; 3.
`silver-cleanup-ourairports-airports` 18 of which 6; 12; 0; 4.
`silver-cleanup-ourairports-runways` 10 of which 6; 4; 0; 5.
`mapping-propose-flights` 33 of which 0; 0; 0; 0.
`mapping-propose-airport-weather` 17 of which 0; 0; 0; 0. So the flights
text carries the parts of 17 of its 19 target names, most of them in
the documentation sentences themselves (16 docs-only), and the finding
reports rule 1's result beside these counts and beside `A1`.

## 6. The spend bound and the estimates

The bound is **$200.00** for the whole experiment, every arm and every
model, ruled on October 21, 2026, from credits that expire on October
25. It is enforced in code: `arms.yaml` carries `spend_bound_usd`, the
runner keeps a committed ledger ([`ledger.jsonl`](ledger.jsonl), one
line per attempt with its model, disposition, tokens, and cost at the
pinned rates), reads the ledger's total once at the start of a batch
and carries it forward as every row is appended, and before every call
checks that total plus the next run's estimate against the bound; when
it would pass, the runner prints `BOUND-STOP` and exits 3 without
calling. The bound is printed as a line before the first batch and
before every batch (`SPEND-BOUND`, with the ledger total and the
batch's planned run count and estimate; the plan counts every attempt
the batch names, attempts the ledger already holds included, so a
repeated batch prints the full plan and its `BATCH` line reports the
skipped count). A cost in the ledger is the SDK's token counts at the
rate rows `models.py` pins, never a billing figure.

Per-run estimates are the Arc 6 cost actuals per fixture at sonnet-5
(`docs/verification/evidence/2026-09-05_arc6_exit.md`), scaled by the
model's rate ratio (opus 2.5, fable 5.0, since both rates scale
uniformly). The amend fixture takes the Arc 6 amend call's actual
($0.0879). The two describe fixtures are derived from output, which
drives the cost: the Session P describe call over 10 columns returned
3,060 output tokens (`docs/verification/evidence/2026-08-25_sessionP_adoption_rehearsal.md`),
306 per column, so `describe-silver-flights` (34 columns; a 30,763
character brief of system prompt, tagged inputs, and compact wire
schema, at about 4 characters per token) is estimated at $0.1194 and
`describe-silver-airport-weather` (18 columns, 22,999 characters) at
$0.0666. These are first-attempt estimates: a retried run
spends again. The batch estimates below are what `--dry-run` prints from
`arms.yaml`, at four decimals, with `REPEATS=5` and `MODEL=` on the two
control rows:

| Batch | Runs | Estimate |
|---|---|---|
| `baseline` at sonnet, 10 repeats | 110 | $9.4100 |
| `A`, 10 repeats | 80 | $6.5640 plus the context tokens (under $0.10) |
| `A0`, 10 repeats | 30 | $2.1770 |
| `A1`, 10 repeats | 30 | $2.1770 |
| `baseline` at opus, 5 repeats | 55 | $11.7625 |
| `baseline` at fable, 5 repeats | 55 | $23.5250 |
| `B-baseline`, 10 repeats | 30 | $2.7390 |
| `B`, 10 repeats | 30 | $2.7390 (the skeleton emits fewer output tokens; the estimate stays the B-baseline's) |
| All | 420 | $61.09, with the rest of the bound as headroom |

Two guards beside the bound. A single run whose cost exceeds three
times its per-run estimate is reported (`COST-HIGH` on its line) and the
batch continues. A batch whose cumulative cost passes three times the
batch's estimate stops itself (`BATCH-STOP`, exit 3) and is a STOP to
the Architect. The bound can be passed only by the one run that was
under the bound by its estimate and cost more: at `max_tokens` 16,384
and three attempts, a run costs under $0.70 at sonnet, $1.70 at opus,
and $3.40 at fable, so the overshoot is under one such run. In the plan
the bound is unreachable unless every batch runs over three times its
estimate; the batch stop is the guard that will fire first if the
output-derived estimates are low.

## 7. The model control (B5)

The `baseline` arm also runs at `claude-opus-5` and `claude-fable-5`,
five repeats per fixture each, through the eval lane's existing D-34
override (`MODEL=`), recorded and scored the same way. It answers Rev
9's B5 (does a larger model change the cleanup proposer's habit of
keeping source column names) and bounds E3a's reading: if a larger
model moves agreement off `0/0` without context, the habit is
model-dependent, and the channel's value at that model is unmeasured
(no `A` run exists at opus or fable). No `A`, `A0`, `A1`, `B-baseline`,
or `B` run uses another model; the runner refuses `MODEL=` on those
arms. Five repeats per fixture support a reading of each fixture, not a
rate; the control's medians are reported as readings, and its cells are
never verdict cells. Read on October 21, 2026, on the vendor's pages
(platform.claude.com, as read on the page): `claude-sonnet-5` ($2 and
$10 per million tokens; retirement not sooner than June 30, 2027),
`claude-opus-5` ($5 and $25; not sooner than July 24, 2027), and
`claude-fable-5` ($10 and $50; not sooner than June 9, 2027) are each
active with no deprecation date, and each price equals the rate row
`models.py` pins. The sonnet-5 and fable-5 pages carry a legacy badge;
that is a note for the next pin review, never a change here.

## 8. What the runner records, and what is a result

Every attempt lands in the gitignored outbox as the harness writes it
(the record, the proposal, the judgment under `B`, the draft, the
agreement study, or the raw response on a failed-closed exit), and the
runner copies the attempt into `runs/` (created by the first batch;
[`runs/README.md`](runs/README.md) says what lands there) under
`<arm>[-<model>]/<fixture>/a<NN>/` after a screen (no key material,
none of the employer-safe words, no service claim, no path under a home
directory; em dashes inside model-written text are counted and
reported, never edited, because a recording is evidence), with every
occurrence of the repository root in the record relativized. The ledger
line carries the arm, the model, the fixture, the attempt number, the
stance, the disposition, the attempts the harness spent, the
first-attempt lint and groundedness flags, the first-attempt
machine-half, judgment, and structural error counts, the agreement
(agree, checked, mismatches, the oracle's column count, the shared and
draft column counts, the field count, the grain set and order equality)
when an oracle exists, the count of empty descriptions in a written
proposal, the tokens, the cost at the pinned rates, the prompt version,
the schema digest, the context hash, the technical flag and the attempt
it fired at, the re-run and continued flags, the timestamp, and the
evidence folder.

A result is any attempt the model answered at attempt 1: a draft
written at any attempt, or a failed-closed exit after the harness's
retry budget (validation errors fed back, then nothing written; a
response stopped on `max_tokens` or an unparseable response counts as
an attempt-level error the harness retries, so the result is the run
after the budget), or a failed-closed exit the harness takes at once
(a moved input; a narrowing the amend validator refuses without the
relaxation flag, which the amend fixture never passes, so any narrowing
the model proposes there fails closed at once with no retry). A result
is never re-run. A fixture whose latest result in the arm failed closed
is **lost**: its remaining attempts in that batch are not run, the
batch continues with the next fixture, the runner prints `LOST` and
the `BATCH` line counts it (the ledger carries the failed row, from
which the loss is derived), and every later batch of the arm prints
`LOST` for it and calls nothing. A person who has read the record may continue it by name
(`make eval-agents ARM=<arm> REPEATS=<n> CONTINUE_LOST=<fixture>`,
printed as `CONTINUE`, the rows marked `continued`); that is invocation
on a human's instruction, which D-10 Amendment G permits, and the
failed result stays in the ledger as a result. Section 9 says what a
lost fixture does to each rule.

A technical failure is one of two things: the SDK raised at attempt 1
before a response (`api_error` in the record; the harness catches the
SDK's connection and API error classes, so a client-side status after
the SDK's own retries is technical too), or the run's responses
carried no usage at all (both token counts zero beside a response id). A
technical attempt is marked `technical` with `technical_attempt` 1 in
the ledger, it does not lose the fixture, it joins no cell, the batch
continues with the fixture's next attempt, and the attempt may be
re-run once, by a person, by the runbook's sideways entry (`make
eval-agents ARM=<arm> REPEATS=<n> RERUN_TECHNICAL=1`, which re-invokes
only the attempts the ledger marks technical and not yet re-run, never
a result, and never a re-run that was itself technical). Every re-run
is reported and keeps both rows. When the SDK raises on a retry turn
(attempt 2 or 3, after the model answered attempt 1 with validation
errors), the row carries `technical_attempt` 2 or 3 and is a result
for the first-attempt rates and classes, scores 0.0 in the agreement
medians as every result with no draft does, does not lose the fixture,
and is not re-run: the model's first answer was measured. A missing key is refused by the runner itself before the
`SPEND-BOUND` line (exit 1, nothing printed to the record). A harness
precondition refusal (no lint tool, a profile that fails integrity, a
prompt that does not parse) writes no row: the runner prints `REFUSED`
and the batch stops with exit 1, because the refusal is the same on
every attempt. An attempt interrupted before its row was
appended has no ledger row: the next batch of the arm plans it again,
and the outbox may hold the interrupted attempt's record; the runbook's
interrupt exit says to read the outbox before re-running.

The runner's printed lines, each reported and never matched: `SPEND-BOUND`
before a batch; `RUN` per attempt (with `COST-HIGH` when a run passed
three times its estimate); `LOST`, `CONTINUE`, `RERUN`, `REFUSED`,
`BOUND-STOP`, `BATCH-STOP`, `SCREEN-STOP` as above; `BATCH` and
`EVIDENCE` at the end of a batch; `DRY` per fixture on the dry path;
`LEAKAGE` per context file; `VERDICT` and `SCORES` from the scorer.

A screen refusal (`SCREEN-STOP`, exit 3) comes after the ledger row is
appended: the attempt is a result and counts; its evidence stays in the
outbox and is copied by hand after the Architect rules on the refusing
text (the banned-word regex is a substring match, so an innocent word
inside a model-written sentence can trip it). The runbook names the
STOP.

## 9. The scorer and the verdict rules

The scorer is `agreement.py` at head, unchanged: agree over checked,
where checked is the shared column names times the fields (five for a
table contract, four for a mapping contract), and a column on one side
only is a mismatch. First-attempt lint and groundedness are the eval
lane's flags as at head. Tokens are what the SDK returned. `make
e3-score` reads the committed ledger and the committed evidence, never
the outbox, and writes `scores.json` and `scores.md`; it is
deterministic and prints the verdict lines by the rules below.

Three measures per attempt, all from the unchanged scorer's output:
the **agreement fraction**, agree over checked (0.0 when checked is 0
or no draft was written); the **oracle-normalized agreement**, agree
over the oracle's column count times the fields (0.0 when no draft was
written), which is the measure the regression rules compare, because
the fraction's denominator is the shared set, and the context's whole
purpose is to change which names are shared; and the **shared count**,
the shared column names. A cell is one arm, one model, one fixture;
its results are the attempts that are not technical; a cell with
fewer than **five** results is **unresolved** and decides no rule: a
question that needs an unresolved cell is **not measured**, never
earned and never not earned. Medians are over a cell's results, except the
mismatch median, which is over its written drafts; a range is min to
max. Two tolerances, coded as stated: a rate is "not
below" another when it is not lower by more than one attempt's worth
of its own denominator; a median is "below" another only when it is
lower by more than one field's worth of the oracle (one over the
oracle's column count times the fields).

**The error classes**, read from the record's
`validation.attempt_log[0]` by substring against the validator's and
the harness's own strings (the lists are `_MACHINE_DESCRIBE`,
`_MACHINE_AMEND`, `_STRUCTURAL`, and `_UNCLASSED` in
`src/metricmine/agents/e3.py`; a test pins the strings):

| Class | Describe | Amend | Reachable under `B`? |
|---|---|---|---|
| machine-half | the columns must enumerate the profiled columns in order; a column that is not a column of the profiled table; `physical_type`, `required`, or `logical_type` against the profile; the two fixed table rules present exactly once; a table-level rule naming a column; `stance`; `target_schema`; `target_table`; `proposed_version`; a non-empty `changes` | a re-emitted `physical_type` or `required` with no declared change; a committed column absent with no declared drop; a new column with no declared add; grain keys off the committed grain with no declared change; a dropped column still present; a `grain_change` disagreeing with `grain_keys`; an added column entering required; `proposed_version` off the derived bump; `stance`; `target_schema`; `target_table` | no: code writes every one of these fields, and a judgment that would move one raises a `SkeletonError`, counted as judgment |
| structural | the response stopped on anything but `end_turn`; the response is not JSON; the response fails the proposal (or judgment) schema | the same | yes |
| judgment | every other validator error: a missing or null grain key, a rule the evidence does not support, a `SkeletonError` (a column the skeleton does not carry, a column described twice or left undescribed, prose under amend, a stated grain off the declared change), a false claim in `changes`, a decision re-valued, a narrowing refused, a lint failure, a contract-schema failure | the same | yes |
| unclassed | a staleness error; an api error (counted in no class) | the same | yes |

One failure moves class between arms and the finding says so: a
hallucinated column name under `B-baseline` counts two machine-half
errors (the enumeration and the column that is not a profiled column)
and no judgment error, while the same hallucination under `B` is one
`SkeletonError`, counted as judgment. Rule 2 of E3b compares
judgment-error run rates with this asymmetry stated. Under `B` the
skeleton also refuses, before the validator sees them, a second
`grain_change` and an `add_column` naming any committed column (dropped
or not), the two judgments that would otherwise reach a machine-half
string; both are `SkeletonError`, counted as judgment.

**E3a is earned when all four hold, and not measured when any cell it
reads is unresolved:**

1. on at least two of the three `0/0` fixtures, the median checked count
   over arm `A`'s results is greater than zero; the median shared count
   and its range are reported beside it;
2. for each of the five oracle-bound fixtures that are not `0/0`
   (`nyc-planes`, `ourairports-airports`, `ourairports-runways`, the two
   mapping fixtures), arm `A`'s median oracle-normalized agreement is
   not below the `baseline` arm's at sonnet-5 by more than one field's
   worth; the three `0/0` fixtures are not compared, because the
   baseline there is 0.0 by convention and a comparison would be met
   trivially;
3. arm `A`'s first-attempt lint pass rate and first-attempt groundedness
   pass rate, over all its results, are not below the `baseline` arm's
   rates at sonnet-5 over the same eight fixtures by more than one
   attempt's worth;
4. arm `A0` does not satisfy rule 1 on its own (if the e3 prompt with no
   context moves two of the three fixtures off zero, the paragraph did
   it, and the channel is not shown to carry it).

Reported beside the verdict, never part of it: `A1`'s medians on the
three fixtures (the documentation sentences without the conventions);
the model control's medians; the leakage counts, verbatim and
composable; the grain set-equality rate per cell; the median mismatch
count; the agreement fraction beside the normalized measure.

**E3b is earned when all four hold, and not measured when any cell it
reads is unresolved:**

1. first-attempt machine-half errors are zero on every arm `B` result.
   This holds by construction: no machine-half string is reachable
   under `B` (the class table), and the keyless test proves the
   code-built skeleton passes every validator machine-half check on
   every committed silver profile. The live arm checks it; a nonzero
   count would be a defect in the skeleton, not a measurement. The
   `B-baseline` count beside it, runs and errors, is the failures the
   skeleton removes, and is the measurement rule 1 reports;
2. the fraction of arm `B` results with at least one first-attempt
   judgment error, per stance (over 20 describe results and 10 amend
   results at full n), is not above `B-baseline`'s by more than one
   attempt's worth;
3. for each of the three fixtures, arm `B`'s median oracle-normalized
   agreement is not below `B-baseline`'s by more than one field's
   worth; for the describe fixtures this compares the grain choice
   only (Section 3), and the count of drafts whose grain set equals the
   oracle's is reported with it, beside the count of drafts; the count
   of empty descriptions per cell is reported with it;
4. the token split is measurable on every fixture over first-attempt
   results only (a retried `B-baseline` run carries its retries'
   tokens): per fixture, the median output tokens of `B-baseline` and
   of `B` over results with `attempts` 1, and one minus their ratio as
   the **output-token saving** on a live call; beside it, the machine
   half's character share of every written `B-baseline` proposal
   (compact JSON characters of `stance`, `target_schema`,
   `target_table`, `proposed_version`, and the four machine fields of
   every column, over the whole proposal), the method of the September
   17 reading, its median across the written proposals, as the
   **structure share**. The saving is the prompts'
   difference in output and may be small or negative; the structure
   share is the direct measure.

**What a lost fixture does to each rule.** A fixture lost at attempt
`k` leaves a cell with `k` results, the failed one at 0.0 agreement.
With `k` under five the cell is unresolved and the question is not
measured until a person continues it. With `k` at five or more the
failure counts as one result at 0.0, so a loss under `A` or `B` pulls
that cell's median down and a loss under a baseline arm pulls the
comparison's floor down; the finding states every loss with the attempt
it happened at and the rule it touched. A loss early in a batch is
therefore a STOP to the Architect, who reads the record and rules on
`CONTINUE_LOST` before the sitting goes on.

**What ten repeats can support.** A median over ten results leaves
zero when at least five produced at least one shared column name. If
the true per-attempt probability of that were 0.2, five or more of ten
would happen about 3 percent of the time; at 0.5, about 62 percent; at
0.8, about 99 percent. So rule 1 reads a per-attempt probability well
above one in five as a move, and misses a move that happens less than
half the time; its median hides magnitude, which the reported shared
count carries. Rules 2 and E3b's rule 3 compare medians of ten against
ten with the one-field tolerance and cannot resolve a difference
smaller than the spread of either side; a fixture whose baseline is
already at its ceiling can only tie. Rule 3 compares rates over 80
results, where one attempt is 1.25 points; E3b's rule 2 compares rates
over 20 (describe) and 10 (amend), where one attempt is 5 and 10
points, and the tolerance is exactly that one attempt. Every rule is
otherwise a zero-margin comparison, and the finding states the counts
and the margins, never only the verdict.

## 10. What a graduation would need, and what this key does not decide

Nothing graduates here. HW-15 is an amendment to D-23 (Amendment H's
fixed list of input kinds gains `operator_context`; on the branch the
boundary test `tests/test_context_harvest.py` admits the fourth kind
and says so) and to D-22 (Amendment I's record gains the context
verbatim and its hash; whether `operatorContextHash` joins the
provenance keys is decided then), with the prompts bumped on main under
D-22. HW-14 is an amendment to D-21 (the model emits a judgment against
a judgment schema, and code writes the proposal) and D-35 (the describe
and amend stances' shape), with the judgment schema beside the frozen
ones and the prompts bumped. Each is a later prep, by its own
documentation pull request, in the form that ran here. Out of this key:
HW-16, HW-17, HW-19, HW-26, E2, HW-49, HW-50, any host path, any sixth
tool, E1's tool-first form, any pin move, any data contract change on
main, any change to the scorer's definition, and cleanup under the
skeleton (`validate_cleanup` holds no type or required equality,
measured at head on October 21, 2026, so there is no machine half for
code to write there). One head observation found on the way, out of
E3's reach and recorded for the findings register's own lane: with
`--allow-relaxation`, `validate_amend` does not check that a
`grain_change`'s keys name a committed or added column, and
`apply_changes` then raises a `KeyError`; the same path exists for a
`description_change` on a column dropped in the same change set.
