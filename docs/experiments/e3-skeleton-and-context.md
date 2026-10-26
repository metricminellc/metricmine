# E3, the skeleton and the context channel: measured (2026-10-23)

> Repo path: `docs/experiments/e3-skeleton-and-context.md`
> An experiments-lane record (CLAUDE.md rule 19). It mints no decision
> and no finding. The two proposers, their prompts on main, the
> validators, the scorer, and the eval lane at head are unchanged; the
> experiment ran on the branch `experiment/e3-skeleton-and-context`
> under the key committed at `4f95ca6` (`docs/experiments/e3/KEY.md`
> on that branch), which fixed every rule below before the first run.

## The question

E3a: does a few sentences of operator context, bound as one more
governed input and rendered as data, move the cleanup proposer off
the three `0/0` fixtures of the Arc 6 agreement study without
regressing the other eight? E3b: when code writes the machine half
of a describe or amend proposal and the model emits only the judgment
over it, do the first-attempt machine-half failures go to zero
without the judgment failures rising, and how many of the output
tokens were structure? The key states both as measurable claims
(Section 1) and the verdict rule per question (Section 9).

## The rule

E3a is earned when, over ten repeats at the pinned model, at least
two of the three `0/0` fixtures reach a nonzero checked set under
arm A (rule 1), no comparable fixture's oracle-normalized agreement
median under A falls below its baseline median by more than one
field's worth (rule 2), the first-attempt lint and groundedness
rates under A are not below the baseline's by more than one
attempt's worth (rule 3), and the prompt-only control A0 does not
satisfy rule 1 on its own (rule 4). E3b is earned when the
first-attempt machine-half errors under arm B are zero (rule 1, held
by construction and checked), the judgment-error rate under B is not
above the B-baseline's per stance by more than one attempt's worth
(rule 2), no fixture's oracle-normalized agreement median under B
falls below the B-baseline's by more than one field's worth (rule
3), and the output-token split is measurable on every fixture over
first-attempt runs (rule 4). A cell with fewer than five results
decides no rule: the question is then not measured. A technical
failure at attempt 1 is not a result; a fixture whose latest result
failed closed lost its remaining attempts unless a person continued it
by name (D-10 Amendment G). The scorer is `agreement.py` at head,
unchanged; the oracle-normalized measure divides its agree count by
the oracle's column count times its field count.

## What was measured

Models: `claude-fable-5`, `claude-opus-5`, `claude-sonnet-5` (the baseline arm
alone ran at a model other than `claude-sonnet-5`, the D-34 override).
Runs: 420 ledger rows from 2026-10-23 to 2026-10-23; ledger total
$55.6640 against the bound $200.00.
The live calls ran on the operator's machine by the runbook with
`ANTHROPIC_API_KEY` in the environment; the sandbox ran nothing live.

| Arm | Model | Rows | Results | Technical | Failed closed | Cost |
|---|---|---|---|---|---|---|
| `A` | `claude-sonnet-5` | 80 | 80 | 0 | 0 | $8.3465 |
| `A0` | `claude-sonnet-5` | 30 | 30 | 0 | 0 | $2.0393 |
| `A1` | `claude-sonnet-5` | 30 | 30 | 0 | 0 | $2.0299 |
| `B` | `claude-sonnet-5` | 30 | 30 | 0 | 0 | $4.0826 |
| `B-baseline` | `claude-sonnet-5` | 30 | 30 | 0 | 0 | $5.0583 |
| `baseline` | `claude-fable-5` | 55 | 55 | 0 | 0 | $16.4932 |
| `baseline` | `claude-opus-5` | 55 | 55 | 0 | 0 | $8.6018 |
| `baseline` | `claude-sonnet-5` | 110 | 110 | 0 | 0 | $9.0123 |

The leakage count over the committed context files, as the lane prints it:

- `silver-cleanup-nyc-flights`: 1238 characters; oracle 19 columns, 19 not in the profile; shared names in the text 0; oracle-only names in the text 0; composable from the text 17
- `silver-cleanup-nyc-flights` (docs-only): 962 characters; oracle 19 columns, 19 not in the profile; shared names in the text 0; oracle-only names in the text 0; composable from the text 16
- `silver-cleanup-nyc-weather`: 1080 characters; oracle 14 columns, 14 not in the profile; shared names in the text 0; oracle-only names in the text 0; composable from the text 5
- `silver-cleanup-nyc-weather` (docs-only): 804 characters; oracle 14 columns, 14 not in the profile; shared names in the text 0; oracle-only names in the text 0; composable from the text 5
- `silver-cleanup-nyc-airlines`: 587 characters; oracle 3 columns, 3 not in the profile; shared names in the text 0; oracle-only names in the text 0; composable from the text 2
- `silver-cleanup-nyc-airlines` (docs-only): 311 characters; oracle 3 columns, 3 not in the profile; shared names in the text 0; oracle-only names in the text 0; composable from the text 1
- `silver-cleanup-nyc-planes`: 907 characters; oracle 10 columns, 8 not in the profile; shared names in the text 2; oracle-only names in the text 0; composable from the text 3
- `silver-cleanup-ourairports-airports`: 1469 characters; oracle 18 columns, 6 not in the profile; shared names in the text 12; oracle-only names in the text 0; composable from the text 4
- `silver-cleanup-ourairports-runways`: 1442 characters; oracle 10 columns, 6 not in the profile; shared names in the text 4; oracle-only names in the text 0; composable from the text 5
- `mapping-propose-flights`: 508 characters; oracle 33 columns, 0 not in the profile; shared names in the text 0; oracle-only names in the text 0; composable from the text 0
- `mapping-propose-airport-weather`: 479 characters; oracle 17 columns, 0 not in the profile; shared names in the text 0; oracle-only names in the text 0; composable from the text 0

## The result, as measured

### Arm `baseline` at `claude-sonnet-5`

| Fixture | n | written | failed closed | technical | lint at 1 | grounded at 1 | machine at 1 (runs, errors) | judgment at 1 (runs) | agreement median (min, max) | normalized median | shared names median (min, max) | mismatches median | grain set equal | empty descriptions | out tokens median (first-attempt runs) | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `mapping-propose-airport-weather` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0.9853 (0.9853, 1) | 0.9853 | 17 (17, 17) | 4 | 0 | 0 | 6192 (6192) | $0.7995 |
| `mapping-propose-flights` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0.9924 (0.9924, 1) | 0.9924 | 33 (33, 33) | 3 | 0 | 0 | 11587 (11587) | $1.3777 |
| `mapping-propose-invoice-lines` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | - | 0 | 0 | 3064.5 (3064.5) | $0.4686 |
| `silver-cleanup-messy-orders` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | - | 0 | 0 | 8005 (8005) | $0.9772 |
| `silver-cleanup-nyc-airlines` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0 (0, 1) | 0 | 0 (0, 1) | 5 | 0 | 0 | 2231 (2231) | $0.3280 |
| `silver-cleanup-nyc-flights` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | 38 | 0 | 0 | 7133.5 (7133.5) | $0.9025 |
| `silver-cleanup-nyc-planes` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 1 (1, 1) | 0.2 | 2 (2, 2) | 15 | 0 | 0 | 4160.5 (4160.5) | $0.5553 |
| `silver-cleanup-nyc-weather` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | 29 | 0 | 0 | 5621 (5621) | $0.7704 |
| `silver-cleanup-online-retail` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | - | 0 | 0 | 6532.5 (6532.5) | $0.8284 |
| `silver-cleanup-ourairports-airports` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0.9385 (0.9333, 0.9385) | 0.6778 | 13 (12, 13) | 15 | 0 | 0 | 6728.5 (6728.5) | $0.8852 |
| `silver-cleanup-ourairports-runways` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 1 (0.92, 1) | 0.4 | 4 (4, 5) | 22 | 1 | 0 | 9557 (9557) | $1.1194 |

### Arm `A` at `claude-sonnet-5`

| Fixture | n | written | failed closed | technical | lint at 1 | grounded at 1 | machine at 1 (runs, errors) | judgment at 1 (runs) | agreement median (min, max) | normalized median | shared names median (min, max) | mismatches median | grain set equal | empty descriptions | out tokens median (first-attempt runs) | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `mapping-propose-airport-weather` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0.9853 (0.9853, 1) | 0.9853 | 17 (17, 17) | 4 | 0 | 0 | 5306 (5306) | $0.7238 |
| `mapping-propose-flights` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0.9924 (0.9924, 1) | 0.9924 | 33 (33, 33) | 2 | 0 | 0 | 12280.5 (12280.5) | $1.4580 |
| `silver-cleanup-nyc-airlines` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 1 (1, 1) | 0.6667 | 2 (2, 2) | 1 | 10 | 0 | 1944.5 (1944.5) | $0.3329 |
| `silver-cleanup-nyc-flights` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0.9417 (0.92, 0.9714) | 0.2684 | 5.5 (4, 8) | 29.5 | 0 | 0 | 11845 (11845) | $1.4144 |
| `silver-cleanup-nyc-planes` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 1 (1, 1) | 0.4 | 4 (3, 7) | 11 | 2 | 0 | 5039 (5039) | $0.6581 |
| `silver-cleanup-nyc-weather` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0.8 (0.8, 0.8) | 0.1714 | 3 (3, 3) | 24.5 | 0 | 0 | 9919 (9919) | $1.1964 |
| `silver-cleanup-ourairports-airports` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0.9556 (0.9333, 0.9692) | 0.4778 | 9 (7, 13) | 21 | 1 | 0 | 10110.5 (10110.5) | $1.2207 |
| `silver-cleanup-ourairports-runways` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0.9 (0.8667, 1) | 0.33 | 3.5 (3, 8) | 24 | 10 | 0 | 11413.5 (11413.5) | $1.3423 |

### Arm `A0` at `claude-sonnet-5`

| Fixture | n | written | failed closed | technical | lint at 1 | grounded at 1 | machine at 1 (runs, errors) | judgment at 1 (runs) | agreement median (min, max) | normalized median | shared names median (min, max) | mismatches median | grain set equal | empty descriptions | out tokens median (first-attempt runs) | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `silver-cleanup-nyc-airlines` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0 (0, 1) | 0 | 0 (0, 1) | 5 | 1 | 0 | 2031.5 (2031.5) | $0.3283 |
| `silver-cleanup-nyc-flights` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | 38 | 0 | 0 | 6864.5 (6864.5) | $0.9042 |
| `silver-cleanup-nyc-weather` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | 29 | 0 | 0 | 6385.5 (6385.5) | $0.8069 |

### Arm `A1` at `claude-sonnet-5`

| Fixture | n | written | failed closed | technical | lint at 1 | grounded at 1 | machine at 1 (runs, errors) | judgment at 1 (runs) | agreement median (min, max) | normalized median | shared names median (min, max) | mismatches median | grain set equal | empty descriptions | out tokens median (first-attempt runs) | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `silver-cleanup-nyc-airlines` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | 5 | 0 | 0 | 1630 (1630) | $0.2879 |
| `silver-cleanup-nyc-flights` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0 (0, 1) | 0 | 0 (0, 1) | 38 | 0 | 0 | 6976.5 (6976.5) | $0.9021 |
| `silver-cleanup-nyc-weather` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | 29 | 0 | 0 | 6287.5 (6287.5) | $0.8399 |

### Arm `B-baseline` at `claude-sonnet-5`

| Fixture | n | written | failed closed | technical | lint at 1 | grounded at 1 | machine at 1 (runs, errors) | judgment at 1 (runs) | agreement median (min, max) | normalized median | shared names median (min, max) | mismatches median | grain set equal | empty descriptions | out tokens median (first-attempt runs) | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `amend-silver-invoice-lines-f28` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 1 (1, 1) | 1 | 10 (10, 10) | 0 | 10 | 0 | 5132.5 (5132.5) | $0.7218 |
| `describe-silver-airport-weather` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 1 (1, 1) | 1 | 18 (18, 18) | 0 | 10 | 0 | 10990 (10990) | $1.2309 |
| `describe-silver-flights` | 10 | 10 | 0 | 0 | 2 | 2 | 0, 0 | 0 | 0.9882 (0.9765, 0.9882) | 0.9882 | 34 (34, 34) | 2 | 0 | 0 | 24363.5 (14716.5) | $3.1056 |

### Arm `B` at `claude-sonnet-5`

| Fixture | n | written | failed closed | technical | lint at 1 | grounded at 1 | machine at 1 (runs, errors) | judgment at 1 (runs) | agreement median (min, max) | normalized median | shared names median (min, max) | mismatches median | grain set equal | empty descriptions | out tokens median (first-attempt runs) | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `amend-silver-invoice-lines-f28` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 1 (1, 1) | 1 | 10 (10, 10) | 0 | 10 | 0 | 2082 (2082) | $0.4017 |
| `describe-silver-airport-weather` | 10 | 10 | 0 | 0 | 10 | 10 | 0, 0 | 0 | 1 (1, 1) | 1 | 18 (18, 18) | 0 | 10 | 0 | 11021.5 (11021.5) | $1.2676 |
| `describe-silver-flights` | 10 | 10 | 0 | 0 | 4 | 4 | 0, 0 | 0 | 0.9882 (0.9882, 0.9882) | 0.9882 | 34 (34, 34) | 2 | 0 | 0 | 22103.5 (15284) | $2.4133 |

### The model control: `baseline` at `claude-fable-5`

| Fixture | n | written | failed closed | technical | lint at 1 | grounded at 1 | machine at 1 (runs, errors) | judgment at 1 (runs) | agreement median (min, max) | normalized median | shared names median (min, max) | mismatches median | grain set equal | empty descriptions | out tokens median (first-attempt runs) | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `mapping-propose-airport-weather` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0.9853 (0.8235, 0.9853) | 0.9853 | 17 (17, 17) | 3 | 0 | 0 | 3687 (3687) | $1.3306 |
| `mapping-propose-flights` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0.9773 (0.8864, 0.9773) | 0.9773 | 33 (33, 33) | 6 | 0 | 0 | 6185 (6185) | $2.0930 |
| `mapping-propose-invoice-lines` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | - | 0 | 0 | 2236 (2236) | $0.8929 |
| `silver-cleanup-messy-orders` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | - | 0 | 0 | 5732 (5732) | $1.8009 |
| `silver-cleanup-nyc-airlines` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0 (0, 1) | 0 | 0 (0, 1) | 5 | 0 | 0 | 1403 (1403) | $0.6622 |
| `silver-cleanup-nyc-flights` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 1 (1, 1) | 0.0526 | 1 (1, 1) | 37 | 0 | 0 | 5535 (5535) | $1.8227 |
| `silver-cleanup-nyc-planes` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 1 (1, 1) | 0.2 | 2 (2, 3) | 15 | 0 | 0 | 2941 (2941) | $1.0862 |
| `silver-cleanup-nyc-weather` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | 29 | 0 | 0 | 4583 (4583) | $1.5728 |
| `silver-cleanup-online-retail` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | - | 0 | 0 | 4838 (4838) | $1.5266 |
| `silver-cleanup-ourairports-airports` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0.9429 (0.9385, 0.9692) | 0.7 | 13 (13, 14) | 13 | 0 | 0 | 5330 (5330) | $1.8049 |
| `silver-cleanup-ourairports-runways` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0.9429 (0.92, 1) | 0.46 | 5 (4, 7) | 22 | 3 | 0 | 5873 (5873) | $1.9006 |

### The model control: `baseline` at `claude-opus-5`

| Fixture | n | written | failed closed | technical | lint at 1 | grounded at 1 | machine at 1 (runs, errors) | judgment at 1 (runs) | agreement median (min, max) | normalized median | shared names median (min, max) | mismatches median | grain set equal | empty descriptions | out tokens median (first-attempt runs) | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `mapping-propose-airport-weather` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0.9853 (0.8235, 0.9853) | 0.9853 | 17 (17, 17) | 3 | 0 | 0 | 3943 (3943) | $0.6731 |
| `mapping-propose-flights` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0.9924 (0.9167, 0.9924) | 0.9924 | 33 (33, 33) | 4 | 0 | 0 | 6923 (6923) | $1.1265 |
| `mapping-propose-invoice-lines` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | - | 0 | 0 | 2025 (2025) | $0.4273 |
| `silver-cleanup-messy-orders` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | - | 0 | 0 | 5416 (5416) | $0.8833 |
| `silver-cleanup-nyc-airlines` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0 (0, 1) | 0 | 0 (0, 1) | 5 | 0 | 0 | 1595 (1595) | $0.3470 |
| `silver-cleanup-nyc-flights` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | 39 | 0 | 0 | 6087 (6087) | $0.9517 |
| `silver-cleanup-nyc-planes` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 1 (1, 1) | 0.2 | 2 (2, 2) | 16 | 0 | 0 | 3213 (3213) | $0.5735 |
| `silver-cleanup-nyc-weather` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | 29 | 0 | 0 | 4133 (4133) | $0.7217 |
| `silver-cleanup-online-retail` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0 (0, 0) | 0 | 0 (0, 0) | - | 0 | 0 | 4876 (4876) | $0.7928 |
| `silver-cleanup-ourairports-airports` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 0.9385 (0.9333, 0.9385) | 0.6778 | 13 (12, 13) | 15 | 0 | 0 | 6159 (6159) | $1.0229 |
| `silver-cleanup-ourairports-runways` | 5 | 5 | 0 | 0 | 5 | 5 | 0, 0 | 0 | 1 (1, 1) | 0.6 | 6 (4, 6) | 20 | 0 | 0 | 6863 (6863) | $1.0820 |

### E3a by the rule

- Rule 1: fixtures off `0/0` under A: `silver-cleanup-nyc-flights`, `silver-cleanup-nyc-weather`, `silver-cleanup-nyc-airlines` (met; two of three required).
- Rule 1, the shared names under A, median (min, max): `silver-cleanup-nyc-airlines` 2 (2, 2), `silver-cleanup-nyc-flights` 5.5 (4, 8), `silver-cleanup-nyc-weather` 3 (3, 3).
- Rule 2 (over `silver-cleanup-nyc-planes`, `silver-cleanup-ourairports-airports`, `silver-cleanup-ourairports-runways`, `mapping-propose-flights`, `mapping-propose-airport-weather`; the three `0/0` fixtures have no baseline agreement to fall below): fixtures whose normalized median fell below the baseline's by more than one field's worth: `silver-cleanup-ourairports-airports`, `silver-cleanup-ourairports-runways` (not met).
- Rule 3: first-attempt lint A 80/80 against baseline 80/80; groundedness A 80/80 against baseline 80/80 (met).
- Rule 4, the prompt-only control `A0` (the e3 prompt, no context): checked median per `0/0` fixture `silver-cleanup-nyc-airlines` 0, `silver-cleanup-nyc-flights` 0, `silver-cleanup-nyc-weather` 0; A0 alone would not satisfy rule 1 (met).
- Reported, never a condition: the docs-only control `A1` (the context without its conventions sentences): checked median per `0/0` fixture `silver-cleanup-nyc-airlines` 0, `silver-cleanup-nyc-flights` 0, `silver-cleanup-nyc-weather` 0; shared names median `silver-cleanup-nyc-airlines` 0, `silver-cleanup-nyc-flights` 0, `silver-cleanup-nyc-weather` 0.
- **E3a: not earned.**

### E3b by the rule

- Rule 1 (held by construction; checked): first-attempt machine-half errors under B 0; under B-baseline 0 errors over 0 runs, the failures the skeleton removes (met).
- Rule 2: runs with a judgment error at attempt 1, B against B-baseline: amend 0/10 against 0/10; describe 0/20 against 0/20 (met).
- Rule 3: fixtures whose normalized median under B fell below the B-baseline's by more than one field's worth: none (met). Grain set equal (drafts, B against B-baseline): `amend-silver-invoice-lines-f28` 10 against 10; `describe-silver-airport-weather` 10 against 10; `describe-silver-flights` 0 against 0. Empty descriptions (B against B-baseline): `amend-silver-invoice-lines-f28` 0 against 0; `describe-silver-airport-weather` 0 against 0; `describe-silver-flights` 0 against 0.
- Rule 4, the token split over first-attempt runs (output tokens median, B against B-baseline, the output-token saving, and the machine half's character share of the B-baseline proposals): `amend-silver-invoice-lines-f28` 2082 against 5132.5 over 10 and 10 runs, saving 0.5943, structure share 0.1395; `describe-silver-airport-weather` 11021.5 against 10990 over 10 and 10 runs, saving -0.0029, structure share 0.1532; `describe-silver-flights` 15284 against 14716.5 over 4 and 2 runs, saving -0.0386, structure share 0.2292 (met).
- **E3b: earned.**

## What the result bounds

The evidence of record is the branch `experiment/e3-skeleton-and-context`
at `cb27197025f16a5a52f0dc8e71f97c60fcc5ed35` (tree
`42d63a46cf21f35d56249d5540adb36ff692d0e6`, 34 commits past main at
`f44109d`): the 25 payload commits, the key first among them
(`4f95ca6`), one evidence commit per batch in the order the batches ran
(`adc0f94` the baseline at sonnet, `b9e0013` arm A, `5b46eda` arm A0,
`c246066` arm A1, `6922e0f` the baseline at opus, `112a84d` the baseline
at fable, `456d1ea` arm B-baseline, `5616bb8` arm B), and the scores
commit (`cb27197`; `scores.json` sha256 `9f19308e0bf139df`, `scores.md`
sha256 `ef6d4ee95b3268a6`). Main never holds `docs/experiments/e3/`. The
tables above were rendered from `scores.json` and `ledger.jsonl` by the
branch's `render_finding.py`; nothing in them was typed. On a fresh clone
of the branch, `make e3-score` prints the same two `VERDICT` lines and
the same `SCORES` line and leaves both scores files byte for byte as
committed (measured October 23, 2026, in the preparation sandbox, twice).
The header's sentence is about this file: the one behavior of head's own
path the runs measured is not this record's to mint, and it goes to the
findings register by that register's own lane as F-73, carried by the
same pull request.

- **E3a is not earned, by rule 2, and this record does not reopen it.**
  Rules 1, 3, and 4 held: arm A moved all three `0/0` fixtures off zero
  (two of three were required), its first-attempt lint and groundedness
  rates were 80 of 80 against the baseline's 80 of 80, and the
  prompt-only control A0 stayed at zero at the median on all three. Rule 2 failed on
  two of the five compared fixtures: on `silver-cleanup-ourairports-airports`
  the oracle-normalized median under A was 0.4778 against the baseline's
  0.6778, and on `silver-cleanup-ourairports-runways` 0.33 against 0.4,
  each below by more than one field's worth of its oracle. The key's
  Section 4 named this misfit before run one: the conventions sentences
  fit the three `0/0` oracles and misfit some names in the airports and
  runways oracles. Rule 2 counted those two fixtures anyway, so the
  verdict stands as the rule reads.
- **The mechanism, read from the committed drafts, is composition in
  both directions.** On the three `0/0` fixtures the attribution is
  isolated by the two controls; on the two adopted fixtures no control
  arm ran (A0 and A1 ran the three `0/0` fixtures only), so the
  attribution there is read from the drafts' names, where every renamed
  column follows one of the four conventions sentences. Under arm A the
  drafts spelled out what the oracle keeps abbreviated: `length_ft` matched the runways oracle in 10 of 10
  baseline drafts and in 1 of 10 under A, `width_ft` 10 of 10 to 1 of
  10, and on airports `latitude_deg`, `longitude_deg`, and `elevation_ft`
  each 10 of 10 to 3 of 10, with `length_feet`, `latitude_degrees`, and
  `elevation_feet` in their place; `airport_ident` on runways fell from
  10 of 10 to 5 of 10, and `iso_country` and `iso_region` on airports
  from 10 of 10 to 5 of 10. In the other direction the same sentences
  produced oracle names the baseline never wrote: `is_lighted` and
  `is_closed` in 10 of 10 drafts under A against 0 of 10 at the
  baseline, `runway_id` in 10 of 10 against 1 of 10, `continent_code` in
  5 of 10 against 0, `airport_type` in 4 of 10 against 0. Both oracles
  mix the two conventions (`is_lighted` and `has_scheduled_service`
  beside `length_ft` and `latitude_deg`), so no single conventions text
  fits every name in them. The record claims composition, never
  independence from the oracles' names: the leakage counter found zero
  oracle-only names verbatim in every context and 17, 5, and 2
  composable names in the three `0/0` texts, and the docs-only control
  A1 (the same texts without the four sentences) stayed at zero at the
  median on all three fixtures, as A0 did.
- **The model control's reading of Rev 9's B5: at the baseline, the two
  larger models kept the source's names as the pinned model did.**
  At the baseline (head's prompts, no context) `claude-opus-5` and
  `claude-fable-5` kept the source's column names as `claude-sonnet-5`
  did: on `silver-cleanup-nyc-weather` the shared-name median was 0 at
  all three models, on `silver-cleanup-nyc-airlines` 0 at all three, and
  on `silver-cleanup-nyc-flights` 0 at sonnet and opus and 1 of 19 at
  fable. Five repeats per fixture at opus and fable are a reading, not a
  rate. The channel's value at a larger model is unmeasured: no arm A
  run exists at opus or fable.
- **E3b is earned, and its gain is on amend, not describe.** Rule 1 held
  by construction: zero first-attempt machine-half errors under arm B.
  B-baseline also showed zero machine-half errors over its 30 runs, so
  head showed no machine-half failure in this sample and the skeleton
  removed nothing measurable here; what it removes is the class, which
  the keyless test holds on every committed silver profile. Judgment
  errors at the first attempt were 0 of 20 describe runs and 0 of 10
  amend runs in both arms. The median agreement was equal in both arms: 168 of 170
  on `describe-silver-flights` (B-baseline's range reached 166 of 170 in
  three runs), 90 of 90 on
  `describe-silver-airport-weather`, 50 of 50 on
  `amend-silver-invoice-lines-f28`. The grain set equaled the oracle's in
  10 of 10 drafts on airport-weather and on amend in both arms, and in 0
  of 10 drafts on flights in both arms: neither arm matched the
  hand-authored oracle's grain on the 34-column table, the skeleton did
  not change that, and this record does not claim it would. On amend the
  skeleton cut the first-attempt output tokens' median from 5132.5 to
  2082, a saving of 0.5943. On describe it saved nothing (10990 to
  11021.5 on airport-weather, 14716.5 to 15284 on flights), because the
  descriptions the model still writes are the bulk of the output; the
  machine half was 0.1395 of head's output characters on amend, 0.1532
  on airport-weather, and 0.2292 on flights. Arm B cost $4.0826 against
  B-baseline's $5.0583, mostly the fewer retries on flights.
- **One behavior of head's own path was measured on the way, and it goes
  to the findings register by that register's own lane, as F-73 in the
  same pull request; this record itself mints nothing.** At head's
  describe stance (the 1.0.0 prompt, head's schema, `max_tokens` 16384
  under effort high) the first attempt on the 34-column `silver_flights`
  table stopped on `max_tokens` in 8 of 10 B-baseline runs and in 6 of
  10 runs under the skeleton, 14 of 20; each run's `record.json` carries
  `response stopped on 'max_tokens', not end_turn` as its first attempt's
  error. Every retry
  stopped on `end_turn`. Three B-baseline runs needed a third attempt
  because their second attempt failed a groundedness check (an
  accepted-values rule on `is_cancelled` naming values the profile does
  not carry), not the cap. The bounded retry re-sends the truncated
  response, so a two-attempt run's input tokens were 27286 to 30197
  against 12048 for a clean B-baseline run, 2.42 times at the median,
  and a three-attempt run's 46295 to 49262. The clean first attempts
  finished at 14149 to 16383 output tokens, inside the cap's reach. No
  other fixture at any arm or model stopped on the cap: 406 of 420 first
  attempts passed lint and groundedness. The cap's own comment in
  `config/default.yaml` says D-21 requires a cap, not this cap, so a fix
  is a configuration or prompt change and never a register one.
- **What this record does not show.** One model family, ten repeats per
  cell at the pinned model, five at the two controls. The describe
  oracles are hand-authored contracts. No host path ran. The skeleton
  was measured on describe and amend only; cleanup holds no machine half
  for code to write (KEY.md, Section 10). Agreement is against
  self-authored contracts and is never accuracy.

## What remains possible

- **The skeleton's graduation, by a later prep.** The shape of the
  question is fixed by the key's Section 10: an amendment to D-21 (the
  model emits a judgment against a judgment schema, and code writes the
  proposal) and to D-35 (the describe and amend stances' shape), with the
  judgment schema beside the frozen proposal schemas and the describe and
  amend prompts bumped to 1.1.0 on main, in the form they ran on the
  branch, by their own documentation pull request before any implementing
  change. The graduation question stays open on the Backlog (#250); the
  verdicts bear on it. A graduation fires a CLAUDE.md edit
  (rule 15 states the proposer's call shape against the proposal
  schema), drafted by its prep.
- **The channel's re-study, only under a new key.** The channel moved
  what it was asked to move and regressed what the key said it might
  regress, so a re-reading of this run cannot earn it. A new study would
  change one of two things before run one: the conventions sentences
  written per source, so a source whose oracle keeps abbreviated names is
  never told to spell them out; or the two adopted contracts
  (`silver_ourairports_airports`, `silver_ourairports_runways`) renamed
  to the conventions the context stated, which the three `0/0` oracles
  follow and the other silver contracts follow only in part (`temp_f`,
  `dep_hhmm`, and `_ft` suffixes sit in them too), a contract question
  for the backlog, since a rename is a major bump under D-08.
  The same arms, the same scorer, and the same rules would then read a
  different result or the same one. Nothing here decides which.
- **The describe cap's fix.** Two shapes are named for the backlog: a
  cap per stance, or an output budget the describe prompt states; either
  is measured on `describe-silver-flights` before it lands, so the first attempt completes and the retry's doubled input
  disappears. A backlog item by its own pull request; it edits the cap
  and its comment in `config/default.yaml`, never the register, because
  D-21 requires a cap and not this cap.
- **The channel at a larger model is unmeasured.** The model control ran
  the baseline only. A study of arm A at `claude-opus-5` or
  `claude-fable-5` is possible under the same bound and ledger (D-34's
  allow-list is unchanged) and would be its own key.
- **Re-scoring needs no key.** A reader clones the branch at `cb27197`
  and runs `make e3-score`: the two `VERDICT` lines and the `SCORES` line
  print from the committed ledger and evidence, and `scores.json` and
  `scores.md` are unchanged by the run. The branch is kept as it ran,
  unmerged; it is the evidence of record.
- **Out of this record,** as the key's Section 10 lists them: HW-16,
  HW-17, HW-19, HW-26, E2, HW-49, HW-50, any host path, any sixth tool,
  E1's tool-first form, any pin move, any data contract change on main,
  any change to the scorer's definition, and cleanup under the skeleton.

## Status

Nothing graduates by this record. The branch stays as it ran; the
evidence of every attempt is committed under `docs/experiments/e3/runs/`
on the branch with the ledger and the scores, screened before it was
copied. A graduation of either question is a later prep that mints its
amendments (D-21, D-22, D-23, D-35) by their own documentation pull
request and lands the code in the form it ran here (KEY.md, Section 10).
