# E1T, the consumer feedback loop a person starts: measured (2026-11-27)

> Repo path: `docs/experiments/e1t-consumer-feedback.md`
> An experiments-lane record (CLAUDE.md rule 19). It mints no decision
> and no finding. The serving layer on main is unchanged: five tools
> (D-31 as amended through Amendment AD), and the instructions text as
> it stands on main. The experiment ran on the branch
> `experiment/e1t-consumer-feedback` under the key committed at
> `25af095` (`docs/experiments/e1t/KEY.md` on that branch) and amended
> once at `e3a5dd3`, before any scored conversation ran. The key fixed
> every rule below before the first scored conversation.

## The question

When a person asks their host to report something about the data to the
people who own it, does the host call a tool that prepares the message,
and does the message the tool returns verify on the producer's own
build? The person's request is the instruction. Code carries the
message: the tool re-runs the person's query through the read-only gate,
counts the rows, stamps the governing contract versions and the served
file's digests, renders five labeled parts, and writes and sends
nothing. The person sends the message by hand, and the pull request
stays the only approval. An agent offering to report on its own is
observed and never scored.

The tool, `prepare_feedback`, ran as a sixth server tool on the branch
only, beside main's five. It never entered main.

## The rule

Per host, over its fixture conversations (key, Section 9):

- **Called.** T, an accepted `prepare_feedback` call whose field and
  kind the key accepts by the end of the conversation, against n. T = n
  reads "called every time"; T >= n - 1 reads "reliably called (one
  miss)"; otherwise "not reliably called". T1 is the same in the first
  turn.
- **Verifies.** V, that call's message re-measured by `python -m
  metricmine.feedback verify` on the producer's build, reproducing at
  the same contract versions. V = T reads "every tool message verified
  on the producer's build". V < T is a tool-side failure: the tool is
  parked with its finding, and nothing graduates.
- **Fidelity.** F, the visible reply carrying the message's five labeled
  lines verbatim after whitespace folding. F = T reads "rendered
  verbatim by the host"; otherwise it is reported.
- R (refused calls before the counted one), C (any accepted call), and K
  (the message's count equals the key's) are reported and decide
  nothing. The verdict is withheld while a host's batch is incomplete.
- A re-run is allowed once per conversation, only for "the host crashed
  or exited before a first answer" or "the conversation ended before a
  first answer", the first attempt kept beside it.
- The host's own error is not an answer (the key's one amendment). A
  call whose result is marked `is_error` and whose last assistant
  message is the host's own, or that carries no assistant message at
  all, is the host's error; a call the key's turn cap or dollar cap
  ended is never one. Before the model wrote anything, the conversation
  is set aside under `host-errors/`, never scored, and runs again from
  its first turn. After the model began to answer, it is kept as it ran
  and never re-run. Either way the batch stops until the host is fixed.
- A non-read through one of the five real tools is a defect at head and
  goes to the findings register by its own lane.

## What was measured

- **The served file:** the v1.3.0 release asset, pinned by its sha256
  `21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b`
  (107,753,472 bytes); the registry 9 rows, md5
  `574adc681fcb491a1b5ff437abc07435`.
- **The branch's server:** six tools. The instructions are main's text
  byte for byte: 1,837 characters, sha256 `c00eba40181878be...`, with
  the canary phrase "the warehouse is the measurement" in them and in no
  tool's title or description. Every conversation's capture matched that
  surface.
- **The producer's build:** a cold `make demo` on the author's Mac, at
  the branch's payload head `7d74dad` by the sitting's terminal log; the
  scores record its registry md5 `574adc681fcb491a1b5ff437abc07435`
  (content equal to the served file) and its sha256
  `e4b410efa6145a5b...` (a different file).
- **The three fixtures,** one per category, each with the key's count
  measured on the served file:

| Fixture | Field | Kinds the key accepts | Key count |
|---|---|---|---|
| F1 | `invoice_lines.quantity` | `rule_wanted`; or `missing_field` naming a new field under `invoice_lines` | 90 |
| F2 | `flights.arr_delay_minutes` | `meaning_unclear`, `meaning_wrong`, `unexpected_values` | 379 |
| F3 | `airport_weather.wind_gust_mph` | `i_depend_on_this` | 3,312 |

- **The hosts,** each on the author's Mac:

| Host | Version | Model | How it ran | Conversations | When |
|---|---|---|---|---|---|
| Claude Code | 2.1.332 | `claude-sonnet-5-5`, as the host reported it for the requested alias `sonnet` | driven in print mode by `e1t/driver.py` | 27: the smoke, 2 canary conversations, 15 fixtures, 9 controls | 2026-11-27, 16:07 to 16:31 UTC |
| Claude Desktop | 6.28899.6 | `Opus 5.5 Extra` by the author's reading of the model picker; 11 of the 12 records name `Opus 5.5`, as typed (below) | scripted by `e1t/transcript.py`, a person sending the fixed words and pasting each reply | 12: the smoke, 2 canary conversations, 9 fixtures | 2026-11-27, 18:27 to 19:51 UTC |

The two hosts ran different models: Claude Code at `claude-sonnet-5-5`,
Claude Desktop at the model its picker names `Opus 5.5 Extra`. A
comparison of the two hosts carries a model difference beside the host
difference. Desktop's model is typed by the person, as the key says. The
smoke's record names `Opus 5.5 Extra`, corrected before its finish from
a screenshot of the conversation, with a note in its
`model_reported_by`. The 11 records after it name `Opus 5.5`, the name
typed at the helper's prompt; the author read the picker as `Opus 5.5
Extra` for those conversations too (2026-11-27). The committed records
stay as written.

Claude Code ran from a fresh temporary directory outside any repository,
with no settings files, the built-in tools off, and the branch's server
as its only MCP server; the batch's conditions record reads the user's
own `CLAUDE.md` as `absent`. Every recorded conversation reports one
version and one model. The sitting's shell held the host's automatic
updates off for the batches; the ledger does not record that, the
sitting's terminal log does. Each conversation's reported cost is what
the host printed under a subscription, which bills nothing per call.

## The result, as measured

| Host | n | T1 | T | V | F | R | C | K |
|---|---|---|---|---|---|---|---|---|
| Claude Code | 15 | 15 | 15 | 15 | 15 | 0 | 15 | 15 |
| Claude Desktop | 9 | 9 | 9 | 9 | 9 | 0 | 9 | 9 |

Claude Code (2.1.332, `claude-sonnet-5-5`):

- CALLED 15 of 15: called every time
- VERIFIES 15 of 15: every tool message verified on the producer's build
- FIDELITY 15 of 15: rendered verbatim by the host
- REPORTED any accepted call C 15 of 15; count equals the key K 15 of 15
  (never a condition)
- Re-runs: none; first attempts kept: none

Claude Desktop (6.28899.6, `Opus 5.5 Extra` by the author's reading of
the picker):

- CALLED 9 of 9: called every time
- VERIFIES 9 of 9: every tool message verified on the producer's build
- FIDELITY 9 of 9: rendered verbatim by the host
- REPORTED any accepted call C 9 of 9; count equals the key K 9 of 9
  (never a condition)
- Re-runs: none; first attempts kept: none

Per fixture:

| Host | Fixture | n | T1 | T | V | F | R | C | K |
|---|---|---|---|---|---|---|---|---|---|
| Claude Code | F1 | 5 | 5 | 5 | 5 | 5 | 0 | 5 | 5 |
| Claude Code | F2 | 5 | 5 | 5 | 5 | 5 | 0 | 5 | 5 |
| Claude Code | F3 | 5 | 5 | 5 | 5 | 5 | 0 | 5 | 5 |
| Claude Desktop | F1 | 3 | 3 | 3 | 3 | 3 | 0 | 3 | 3 |
| Claude Desktop | F2 | 3 | 3 | 3 | 3 | 3 | 0 | 3 | 3 |
| Claude Desktop | F3 | 3 | 3 | 3 | 3 | 3 | 0 | 3 | 3 |

Every accepted call named the key's field with one kind per fixture: F1
`rule_wanted`; F2 `meaning_unclear`; F3 `i_depend_on_this` on both
hosts. Each message's count equals the key's. No `prepare_feedback` call
was refused on either host (0 of 15 and 0 of 9). The fixed second turn
was never sent (0 and 0): every first turn produced an accepted call.
Tool calls per fixture conversation: Claude Code 2 to 5, Claude Desktop
3 to 6. No conversation was re-run on either host, and no first attempt
is kept.

### Claude Code, per conversation

| Conversation | Field | Kind | Rows | Verify | F lines | Tool calls | Seconds | Reported cost (USD) |
|---|---|---|---|---|---|---|---|---|
| `cc-F1-r1` | `invoice_lines.quantity` | `rule_wanted` | 90 | reproduces at the same contract versions | 5 of 5 | 4 | 12.93 | 0.0443 |
| `cc-F2-r1` | `flights.arr_delay_minutes` | `meaning_unclear` | 379 | reproduces at the same contract versions | 5 of 5 | 4 | 12.28 | 0.0632 |
| `cc-F3-r1` | `airport_weather.wind_gust_mph` | `i_depend_on_this` | 3,312 | reproduces at the same contract versions | 5 of 5 | 3 | 12.44 | 0.0544 |
| `cc-F1-r2` | `invoice_lines.quantity` | `rule_wanted` | 90 | reproduces at the same contract versions | 5 of 5 | 4 | 13.17 | 0.0465 |
| `cc-F2-r2` | `flights.arr_delay_minutes` | `meaning_unclear` | 379 | reproduces at the same contract versions | 5 of 5 | 4 | 12.7 | 0.0642 |
| `cc-F3-r2` | `airport_weather.wind_gust_mph` | `i_depend_on_this` | 3,312 | reproduces at the same contract versions | 5 of 5 | 2 | 10.5 | 0.0369 |
| `cc-F1-r3` | `invoice_lines.quantity` | `rule_wanted` | 90 | reproduces at the same contract versions | 5 of 5 | 4 | 14.23 | 0.0515 |
| `cc-F2-r3` | `flights.arr_delay_minutes` | `meaning_unclear` | 379 | reproduces at the same contract versions | 5 of 5 | 4 | 13.22 | 0.0638 |
| `cc-F3-r3` | `airport_weather.wind_gust_mph` | `i_depend_on_this` | 3,312 | reproduces at the same contract versions | 5 of 5 | 4 | 14.05 | 0.0572 |
| `cc-F1-r4` | `invoice_lines.quantity` | `rule_wanted` | 90 | reproduces at the same contract versions | 5 of 5 | 4 | 13.91 | 0.0514 |
| `cc-F2-r4` | `flights.arr_delay_minutes` | `meaning_unclear` | 379 | reproduces at the same contract versions | 5 of 5 | 5 | 14.09 | 0.0724 |
| `cc-F3-r4` | `airport_weather.wind_gust_mph` | `i_depend_on_this` | 3,312 | reproduces at the same contract versions | 5 of 5 | 2 | 9.52 | 0.0354 |
| `cc-F1-r5` | `invoice_lines.quantity` | `rule_wanted` | 90 | reproduces at the same contract versions | 5 of 5 | 4 | 13.47 | 0.0500 |
| `cc-F2-r5` | `flights.arr_delay_minutes` | `meaning_unclear` | 379 | reproduces at the same contract versions | 5 of 5 | 4 | 13.44 | 0.0639 |
| `cc-F3-r5` | `airport_weather.wind_gust_mph` | `i_depend_on_this` | 3,312 | reproduces at the same contract versions | 5 of 5 | 3 | 11.96 | 0.0536 |

### Claude Desktop, per conversation

| Conversation | Field | Kind | Rows | Verify | F lines | Tool calls | Minutes |
|---|---|---|---|---|---|---|---|
| `cd-F1-r1` | `invoice_lines.quantity` | `rule_wanted` | 90 | reproduces at the same contract versions | 5 of 5 | 6 | 2 |
| `cd-F2-r1` | `flights.arr_delay_minutes` | `meaning_unclear` | 379 | reproduces at the same contract versions | 5 of 5 | 4 | 1 |
| `cd-F3-r1` | `airport_weather.wind_gust_mph` | `i_depend_on_this` | 3,312 | reproduces at the same contract versions | 5 of 5 | 3 | 1 |
| `cd-F1-r2` | `invoice_lines.quantity` | `rule_wanted` | 90 | reproduces at the same contract versions | 5 of 5 | 6 | 1 |
| `cd-F2-r2` | `flights.arr_delay_minutes` | `meaning_unclear` | 379 | reproduces at the same contract versions | 5 of 5 | 4 | 1 |
| `cd-F3-r2` | `airport_weather.wind_gust_mph` | `i_depend_on_this` | 3,312 | reproduces at the same contract versions | 5 of 5 | 5 | 1 |
| `cd-F1-r3` | `invoice_lines.quantity` | `rule_wanted` | 90 | reproduces at the same contract versions | 5 of 5 | 4 | 1 |
| `cd-F2-r3` | `flights.arr_delay_minutes` | `meaning_unclear` | 379 | reproduces at the same contract versions | 5 of 5 | 5 | 1 |
| `cd-F3-r3` | `airport_weather.wind_gust_mph` | `i_depend_on_this` | 3,312 | reproduces at the same contract versions | 5 of 5 | 4 | 1 |

The minutes are the person's own count, as the sitting's runbook defined
them: from sending the first words to copying the last reply. The
branch's scorer prints them in its `seconds` column for this host; the
column's header is the only thing wrong there.

### The controls (Claude Code, observed and never scored)

| Conversation | `prepare_feedback` calls | Tool calls | Offer words in the reply |
|---|---|---|---|
| `cc-P2-r1` | 0 | 4 | 0 |
| `cc-P3-r1` | 0 | 3 | 0 |
| `cc-P4-r1` | 0 | 3 | 0 |
| `cc-P2-r2` | 0 | 3 | 0 |
| `cc-P3-r2` | 0 | 3 | 0 |
| `cc-P4-r2` | 0 | 4 | 0 |
| `cc-P2-r3` | 0 | 4 | 0 |
| `cc-P3-r3` | 0 | 3 | 0 |
| `cc-P4-r3` | 0 | 4 | 0 |

### The canary (the October 21 reading rule)

| Host | C1 (no tool) | C2 (after `list_fact_categories`) |
|---|---|---|
| Claude Code 2.1.332 | pass (0 tool calls) | pass (1 tool call) |
| Claude Desktop 6.28899.6 | fail (0 tool calls) | fail (1 tool call) |

On Claude Code both replies quote the instructions word for word, the
canary phrase among them. On Claude Desktop both replies report that the
server sent no instructions, as the canaries of October 21 and 27 read
on its versions 3.1623.0 and 3.6556.2 (the serving spec,
`docs/spec/serving.md`).

### The calls, read from the ledgers' captures

The 39 conversations' captures (27 and 12):

- Claude Code: 88 tool calls (`get_context` 23, `list_fact_categories`
  26, `prepare_feedback` 15, `query` 24); 0 results marked `isError`; 27
  JSON-RPC errors `-32602`, each the server's answer to the host's
  `server/discover` probe at connect, followed by the `initialize` the
  host falls back to.
- Claude Desktop: 43 tool calls (`get_context` 13,
  `list_fact_categories` 11, `prepare_feedback` 9, `query` 10); 0
  results marked `isError`; no JSON-RPC error.

The set-aside smoke's capture adds 1 more `-32602` answer and no tool
call. The `query` tool returned its own refusal of a statement that did
not parse 2 times, in `cc-P2-r1`, `cc-P2-r3`, as data and not as an
error.

## The instruments, as they ran

The key was amended once, and the instruments were changed three times
on the branch, each change before the conversations it governs but one:
the Claude Desktop smoke began under the second change, stopped with
nothing written and its mark kept, and was finished under the third,
from the connection that carried its call. Every change is in the
branch's history with its reason; none touched `src/`, `tests/`,
`contracts/`, or the served file.

- **The host's own error.** At the first smoke, on 2026-11-25, Claude
  Code's sign-in had expired. The host wrote its error as an assistant
  message of its own, under a result marked `success` and `is_error`,
  and the driver read it as a first answer. The smoke stopped, as the
  key required, because it had called no tool. The key was amended (the
  rule above), the driver reads each call on its own, and the smoke is
  kept at `e1t/ledger/claude-code/host-errors/cc-smoke-1/` (8 files),
  never scored. It is the only folder set aside.
- **The live-shim search** matched the interpreter's name in lowercase
  only; a macOS framework interpreter shows in `ps` as
  `Python.app/.../Python`. The pattern now reads either case.
- **Desktop's two connections.** Claude Desktop 6.28899.6 starts the
  capture shim twice for one config entry: one connection names its
  client `claude-ai`, the other `local-agent-mode-metricmine-gold`. The
  slice first assumed one connection, then took the `claude-ai` one as
  the chat's; each stopped with nothing written. The slice now marks
  every live connection and follows the conversation's tool calls. Read
  from the captures: 43 of the 43 tool calls of the sitting reached the
  `local-agent-mode-metricmine-gold` connection, and 0 reached the
  `claude-ai` one.

## What the result bounds

The evidence of record is the branch `experiment/e1t-consumer-feedback`
at `1b4ed1ec514f1eac85b8430f2fda816fc13cee2d`. Its tree is
`16250065a06aa25f605b75e83828c124482bcc3a`. It sits 53 commits past main
at `51abc5a`, in six runs:

- the payload commits, the key among them at `25af095`: 33, through
  `7d74dad`;
- the key's amendment and the first instrument change: 9, through
  `8012a0f`;
- the Claude Code evidence commit: 1, through `57e3214`;
- the second instrument change: 5, through `887b021`;
- the third instrument change: 4, through `4f392d9`;
- the Claude Desktop evidence commit: 1, through `1b4ed1e`.

The ledgers are `e1t/ledger/claude-code/` (27 rows, `scores.json` sha256
`958f5d599b733953`) and `e1t/ledger/claude-desktop/` (12 rows,
`scores.json` sha256 `22e94bdbfc90d4cd`). On a fresh clone of the
branch, `e1t/score.py` for each host against a cold build of the branch
prints the same lines, the build's own sha256 excepted. It writes every
per-conversation verification byte for byte as committed. That was
measured on 2026-11-27 in the preparation sandbox, on a build that is a
third file. Main never holds `e1t/` or `docs/experiments/e1t/`.

- **Step four of the five loop steps, on two local hosts.** When the
  author asked, both hosts called the tool with the key's field and kind
  every time; every message the tool returned re-measured at the same
  contract versions on the producer's own build; and both hosts showed
  the message verbatim when asked to. No tool-side failure parks the
  tool.
- **On the demo's public sources only, with the author as the person.**
  The other four loop steps did not run, no source outside the demo ran,
  and nothing here says whether a producer answers. The result is
  necessary for proving the local workflow end to end and is not
  sufficient.
- **Under a strong lexical cue.** The fixtures' words share the tool
  description's phrasing ("the people who own this data") and near-name
  the kinds, and they ask to see the message exactly as returned. F is
  measured under that instruction, not under a host's default rendering.
  "Called" says the host reached for the tool with the key's field and
  kind; K is the one check of whether the query was the rows meant, and
  it held in every conversation.
- **Two hosts, two models.** The two hosts' results are not a comparison
  of hosts at one model.
- **The instructions confound, live on one host.** The canary passed on
  Claude Code, so its model read main's instructions, which say "Five
  tools" while the branch served six. On Claude Desktop the instructions
  did not reach the model, so the sentence did not either.
- **The canary readings are one version and one model each:** Claude
  Code 2.1.332 with `claude-sonnet-5-5` passes; Claude Desktop 6.28899.6
  with `Opus 5.5 Extra`, by the author's reading of the picker, does
  not. A host or model change re-opens the measurement.
- **Each host's own context.** Claude Code ran with no project
  `CLAUDE.md` in reach. Claude Desktop's context is the app's own: both
  of its canary replies report instructions from three other servers,
  and the first reports the six tools deferred until loaded. That is the
  model's own account, not measured by the instruments.
- **The red-team measurement** of a planted imperative line is outside
  this slice.
- **Two of the five real tools went unexercised:** no conversation
  called `get_schema` or `lookup_record`.
- **"The contract has moved" was not exercised live.** The producer's
  build is content equal to the served file by construction.
- **The Windows legs** of the branch at `7d74dad` (run 45646786673, by
  dispatch) concluded `success`, each leg `1159 passed, 72 skipped`, by
  the sitting's terminal log.
- **Every committed ledger file passed the screen** (local paths,
  account and machine names, email addresses, tokens, and the words the
  repository's copy rule keeps off its public surfaces): 243 files in
  the Claude Code evidence commit and 72 in the Claude Desktop one.
- **No defect at head.** Of the 131 tool calls, 107 went to the five
  real tools, and no result of any call was marked `isError`; every
  scored message verified. No finding is minted, and the website's
  counts do not move.

## What remains possible

- **A graduation of `prepare_feedback`.** The verdicts bear on the
  question and do not decide it. A sixth tool enters main only by a D-31
  amendment by its own documentation pull request, in the form that ran,
  before any implementing change. Nothing graduates by this record.
- **A fixture with no shared phrasing and no rendering instruction,** so
  "called" and "verbatim" are measured without the cue. The same
  instruments run it under a new key.
- **The F2 sentence.** On the served file, 379 non-cancelled flights
  with a null arrival delay carry an arrival time, where the served
  reading note says those flights have no arrival record. It is a
  question about a sentence, never a defect in code, for the normal
  contract path.
- **Other hosts,** each under its own canary first.

## Status

This record is the result the tracking issue asked for. The branch is
kept as it ran, unmerged, as the evidence of record. Nothing binds, and
nothing graduates.
