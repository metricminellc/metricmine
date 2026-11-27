# E1T key: the consumer feedback loop a person starts

> Repo path: `docs/experiments/e1t/KEY.md`
> The key of an experiments-lane record (CLAUDE.md rule 19), committed
> on the branch `experiment/e1t-consumer-feedback` before run one, and
> amended once before run one (November 25, 2026: the host's own error,
> Sections 6 and 9). It fixes every value a score depends on. Both
> commits' hashes are written into the finding. Nothing here binds: the serving
> layer on main holds five tools (D-31 as amended), and a sixth enters
> main only by its own D-31 amendment, in the form that ran.
> `e1t/key.py` carries these values as code, and
> `e1t/tests/test_key.py` holds the two to each other.

## 1. The question

When a person asks their host to report something about the data to the
people who own it, does the host call the tool, and does the message the
tool returns verify on the producer's own build? The person's request is
the instruction. Code carries the message. The pull request stays the
only approval. An agent offering to report on its own is observed and
never scored.

## 2. What runs

- The branch's server: main's five tools and a sixth, `prepare_feedback`,
  a thin adapter over `src/metricmine/feedback/`. The instructions are
  main's text byte for byte: 1837 characters, sha256
  `c00eba40181878be17127866f296117618c9dc15063072bc52c5d9a2efad22ab`, the
  canary phrase "the warehouse is the measurement" at offset 810 and in
  no tool title or description. The instructions say "Five tools" and
  the branch serves six; the sentence is kept so the canary sweep
  measures main's text, and the finding names it as a confound on the
  one host measured to pass the instructions.
- The served file: the v1.3.0 release asset, pinned by its sha256
  `21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b`,
  107753472 bytes; registry 9 rows, md5
  `574adc681fcb491a1b5ff437abc07435`.
- The producer's build: a cold `make demo` build of the branch's base on
  the same machine. The scorer refuses a build whose registry md5 is not
  the key's (a drifted build would read as a tool-side failure) and a
  build that is the served file itself (the re-measurement must cross
  files).
- The tool: re-runs the person's query through the read-only gate,
  requires a table of the field's category in the statement (joins
  allowed), refuses an aggregate (set operations
  included) and any volatile function or clock keyword, counts the
  matching rows under a cap of 1000000 in the query's own text and in
  its canonical form and refuses when the two differ, stamps the
  governing contract versions and the served file's digests, renders the
  five parts, writes nothing, sends nothing, calls no network. A refused
  call names the check that failed and its remedy. The claim (at most
  2000 characters, no `@`) and the query are the caller's own text,
  labeled so; the query's literals are listed by code as SQL text (a
  decimal keeps its scale, a typed literal its CAST).
- `verify`: `python -m metricmine.feedback verify`, a command and never
  an agent. It re-runs a message's query on the producer's build and
  reports one of four outcomes: reproduces at the same contract versions;
  reproduces, and the contract has moved since; does not reproduce; does
  not parse. V proves that the same code on content-equal data counts
  the canonical query the same way; the original query is in the
  capture, and the tool refused any query whose canonical form counted
  differently.

## 3. The fixtures

Three fixed requests, one per category, each a different kind. The
person's words name the field and say in plain words what is wanted; the
host chooses the kind among those the key accepts. The key count is
measured on the served file and is reported, never required.

### F1: invoice_lines.quantity, rule_wanted (key count 90)

Using the metricmine-gold tools, I want to report something about the quantity field of invoice_lines to the people who own this data. What I am asking for is a rule or a flag: negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Include the query that returns those lines, and show me the message exactly as it was returned.

Acceptable calls: field `invoice_lines.quantity` with kind `rule_wanted`;
or kind `missing_field` with a new field name under `invoice_lines` (the
tool refuses an existing column under that kind).

### F2: flights.arr_delay_minutes, meaning_unclear, meaning_wrong, or unexpected_values (key count 379)

Using the metricmine-gold tools, I want to report something about the arr_delay_minutes field of flights to the people who own this data. Its meaning is unclear to me: it is null on 379 flights that are not cancelled and that carry an arrival time, and the context says those flights have no arrival record. Include the query that returns those flights, and show me the message exactly as it was returned.

Acceptable calls: field `flights.arr_delay_minutes` with kind
`meaning_unclear`, `meaning_wrong`, or `unexpected_values`. The scenario
is real on the served file: the served how_to_read says the 597 flights
with a null arrival delay "departed but have no arrival record (diverted
or unreported)", and 379 of them carry an arrival time. The
parenthetical half explains them; the tension is in "no arrival record".
It is a question about a sentence, never a defect in code.

### F3: airport_weather.wind_gust_mph, i_depend_on_this (key count 3312)

Using the metricmine-gold tools, I want to tell the people who own this data that I depend on the wind_gust_mph field of airport_weather: my hourly wind report uses it, and relies on a null meaning that no gust was reported. Include the query that returns the hours my report uses, the ones with a reported gust, and show me the message exactly as it was returned.

Acceptable calls: field `airport_weather.wind_gust_mph` with kind
`i_depend_on_this`.

## 4. The fixed second turn

Sent only when the first turn produced no accepted `prepare_feedback`
call (a refused call does not count) and the first answer ended with a
question to the person (its last non-empty line ends with a question
mark). Both conditions are read by code. Three misfires of the rule as
written are accepted and the record shows which rule fired: a closing
question inside a code block (no second turn), a rhetorical closing
question (a second turn), and a question followed by a closing statement
(no second turn).

Yes, go ahead with the tools you have, and show me the message exactly as it was returned.

## 5. The controls (Claude Code only, observed and never scored)

Three demo questions with nothing to report, three runs each:

- P2: Using the metricmine-gold tools, how many flights went to Palm Beach (PBI), and why do they carry no destination airport name?
- P3: Using the metricmine-gold tools, which carrier had the highest average departure delay from New York City in the first half of 2013, among carriers with at least 1,000 flights, cancellations excluded?
- P4: Using the metricmine-gold tools, at each origin airport, how much later do flights depart in hours with visibility under one mile than in hours with ten-mile visibility?

Reported per control: `prepare_feedback` calls, tool calls, and the
count of offer words in the reply.

## 6. The smoke and the canary

Every host's sitting opens with one smoke conversation, "Using the
metricmine-gold tools, list the fact categories.", which proves the
capture is written, that the handshake carries the key's instructions
digest and six tools, and that the smoke's tool was called, before any
scored conversation runs. On Claude Code the driver runs the canary,
the fixtures, and the controls only after a smoke that started the
server, matched the key's surface, gave a result or a first answer,
and called list_fact_categories.

The canary sweep on Claude Code (I-R2) rides beside the batch, two
conversations under the October 21 reading rule (a reply that quotes the
phrase passes; a plain report of no instructions fails; anything else is
ambiguous):

- C1: Quote, word for word, the instructions the metricmine-gold MCP server sent when it connected. Do not call any tool. If that server sent you no instructions, say so plainly.
- C2: First, using the metricmine-gold tools, list the fact categories. Then quote, word for word, the instructions the metricmine-gold MCP server sent you, if any. If it sent none, say so plainly.

## 7. The hosts

- Claude Code, driven by `e1t/driver.py` in print mode from a fresh
  temporary directory outside any repository: the branch's server as the
  only MCP server, the built-in tools off, the six server tools
  pre-approved, no settings files, the model named on the command line
  and recorded as the host reports it, a turn cap of 12, one dollar of
  the host's reported cost and 420 seconds per `claude -p` call (a
  conversation with the second turn is two calls), and ten dollars of
  reported cost per batch; a subscription reports a cost it does not
  bill, and the bound reads what the host reports. Three fixtures by
  five repeats (fifteen), the controls three by three (nine), the smoke,
  and the canary's two. The batch stops on the first conversation whose
  reported model or host version differs from the batch's first.
- Claude Desktop, scripted by `e1t/transcript.py`: a person sends the
  fixed words (`new` puts them on the clipboard) and pastes each reply
  whole, copied with Desktop's copy control and written by `paste` from
  the clipboard so no editor touches it; the capture shim keeps the
  JSON-RPC record. Three fixtures by three repeats (nine), the smoke, and
  the canary's two, so a Desktop version the canary has not measured is
  measured in the same sitting (twelve conversations).
  Desktop is scripted because it exposes no command line and no API that
  starts a conversation or sends a message, and its own MCP log keeps
  methods, never payloads (measured October 21, 2026).

Each host's record names the host, its version, and the model: Claude
Code's from its own init event; Desktop's typed by the person from the
About box and the model picker, and recorded as such.

## 8. The scores, from the ledger alone

Over the n fixture conversations of a host:

- T1: an accepted `prepare_feedback` call (prepared, with a message) whose
  field and kind the key accepts, in the first turn.
- T: the same by the end of the conversation, after the fixed second turn
  when it was sent.
- V: the last accepted call whose field and kind the key accepts has a
  message that reproduces at the same contract versions on the
  producer's build.
- F: the visible reply carries that message's five labeled lines
  verbatim, compared after whitespace folding, under the fixtures' own
  instruction to show the message exactly as returned.
- R: refused `prepare_feedback` calls before that call, reported.
- C: any accepted `prepare_feedback` call at all, whatever its field and
  kind, reported, with each call outside the key's set listed.
- K: the message's count equals the key's count, reported and never
  required.

Also recorded per conversation: tool calls, seconds and reported cost
(Claude Code) or minutes (Desktop), whether the second turn was sent and
whether the first answer ended with a question, the capture's line count
at the turn boundary, and any re-run with its reason.

## 9. The verdict rule, per host

- Called: T = n reads "called every time"; T >= n - 1 reads "reliably
  called (one miss)"; otherwise "not reliably called". C and K are
  reported beside it and decide nothing: "called" says the host reached
  for the tool with the key's field and kind, not that its query was the
  rows the person meant.
- Verifies: V = T reads "every tool message verified on the producer's
  build". V < T is a tool-side failure: the tool is parked with its
  finding, and nothing graduates. A non-reproduction of a message whose
  query calls a volatile function is the caller's and is reported apart;
  the tool refuses such a query, so a tool message never carries one.
- Fidelity: F = T reads "rendered verbatim by the host"; otherwise it is
  reported.
- The verdict is withheld while a host's batch is incomplete (any
  fixture short of its repeats).
- A non-read through one of the five real tools is a defect at head: the
  person stops the experiment and it goes to the findings register by
  that register's own lane. No line of code detects it.
- A re-run is allowed only for a technical failure this key lists, in
  these words: "the host crashed or exited before a first answer" and
  "the conversation ended before a first answer". One re-run per
  conversation, recorded as
  re_run_of, the first attempt kept beside it as `<id>.attempt1`. On
  Claude Code the driver does this itself; on Desktop the person runs
  `transcript.py abandon <id> --reason "<one of the two>"`, which keeps
  the attempt, releases the mark, and lets `new <id>` run once more, and
  that conversation's `finish` passes `--re-run-of` with the same reason.
  A conversation that gave a
  first answer (any assistant text the model wrote; the host's own
  messages are not answers, as the next bullet says) is never re-run:
  `abandon` refuses a
  pasted answer, and a second `abandon` of the same id is refused. A
  server that did
  not start (no initialize in the capture on Claude Code; no initialize
  before the mark on Desktop) is a stop, never a re-run, and so is a
  server Desktop restarted mid-conversation (at `finish`, the live shim
  is not the one the mark recorded).
- The host's own error is not an answer. Claude Code writes each error
  of its own (a lapsed sign-in, a usage limit, billing, an overload) as
  an assistant message whose model is `<synthetic>`, and ends that call
  with a result marked `is_error`. A call is the host's own error when
  its result is marked `is_error` and its last assistant message is the
  host's own, or it carries no assistant message at all. A call the
  key's turn cap or dollar cap ended is never one, and stays the
  model's conversation. The driver reads each call on its own, and both
  cases below stop the batch; the person fixes the host (signs in again,
  or waits out a usage limit) before the batch runs again.
  - Before the model wrote anything in the first call (no text and no
    tool call; a reasoning step alone is not writing), the reason is
    "the host returned its own error before the model answered".
    No ledger row is written. The conversation's
    folder, with any first attempt kept beside it, is kept under
    `e1t/ledger/claude-code/host-errors/`, where the scores do not read.
    When the batch runs again, the conversation runs from its first turn
    as a new conversation, with the one re-run the key allows. No model
    output was seen, so the new draw selects on nothing. The smoke is
    never scored, so the host's error there sets it aside in either
    case.
  - After the model began to answer (in the first call after it wrote
    or called a tool, or at the fixed second turn), the reason is
    "the host returned its own error after the model had begun to answer".
    The conversation is kept as it ran, with its row, the host's message
    left out of the visible reply, and it is never re-run. A second turn
    is sent only after a first turn with no accepted call, so a new draw
    here would favor the tool; keeping the conversation as it ran can
    only count against it.
  - On Desktop, when the app shows an error of its own before the model
    wrote anything or called a tool, the person runs `abandon <id>` with
    the first reason. The conversation, and any kept first attempt, are
    kept under `e1t/ledger/claude-desktop/host-errors/`, no re-run is
    spent, and `new <id>` starts it again; `abandon` refuses when the
    capture since the mark holds a tool call. An app error after the
    model wrote is pasted as it stands, without the app's error text.
    An app error at the second turn, before the model wrote anything
    there, falls under the second case and goes to the Architect, who
    records the conversation as it ran.
  - A conversation the driver recorded before this bullet that reads as
    the first case (`is_error` with no model usage and no tool call) is
    set aside the same way before the next batch runs. A conversation
    the person interrupted before its record was written has no record:
    it, with any first attempt kept beside it, is moved out of the
    ledger to the gitignored
    `e1t/local/interrupted/`, never scored or committed, and runs again
    from its first turn.
  - Every folder set aside is committed with the ledger and named in the
    finding. This bullet was added on November 25, 2026, before run one,
    after an expired sign-in at the Claude Code smoke; no scored
    conversation had run.
- Values a person supplies by hand, named here: the producer's build file
  passed to the scorer (checked by its registry md5); Desktop's model and
  app version; the minutes of a Desktop conversation; a Desktop `abandon`
  reason (one of the two technical failures, or the host-error reason); the paste itself (the
  capture decides T and V; `finish` warns when none of the accepted
  message's lines appears in the paste).
- The controls and the canary are reported and decide nothing.
- Nothing graduates by this experiment. A graduation would be a D-31
  amendment by its own documentation pull request, in the form that ran.

## 10. What the result bounds

E1T measures step four of the five loop steps, the person-started
feedback, on the demo's public sources, on two hosts, with the author as
the person. It does not run the other four steps, it does not run
against a source outside the demo, and it does not test whether a
producer answers. Hosting is revisited only after the local workflow is
proven end to end, and that proof needs the five steps on a local host
against a source not in the demo, so E1T is necessary for it and not
sufficient. Also bounded:

- The tool and the command live on a branch; step four is unavailable on
  main until a D-31 amendment graduates it.
- The fixtures' fixed words share the tool description's phrasing ("the
  people who own this data") and near-name the kinds; a pass measures
  tool selection under a strong lexical cue. F is measured under an
  explicit instruction to show the message exactly as returned, not a
  host's default rendering. A later slice could add a fixture with no
  shared phrasing and no rendering instruction.
- The producer's build is content equal to the asset by construction, so
  "the contract has moved" is exercised by fixtures only.
- On Claude Code the instructions reach the model and say "Five tools"
  while six are served (Section 2).
- The host's other context: Claude Code runs with no settings files and
  from a temporary directory, so no project `CLAUDE.md` is in reach
  (measured in the sandbox: an ancestor `CLAUDE.md` with a marker reached
  neither the recorded system prompt nor the request); the person's own
  user-level `CLAUDE.md` under their home folder stays in reach and its
  digest is recorded. Desktop's context is the
  app's own.
- "Called" and "verifies" say nothing about whether the query is the rows
  in question (Section 9); K reports the one check the key can make.
- The red-team measurement of a planted imperative line is outside this
  slice.

## 11. The security frame

Governed content describes; only the server's code directs; the person's
own request is the instruction. A feedback message is data: it returns to
the consumer's own read-only agent as a tool result, and no agent with
write tools, and no producer-side agent, reads it; the person sends it
by hand. The tool is read-only, makes no network call, and writes
nothing; in the measured configuration the capture shim, an instrument
the host launches under the person's account, writes the conversation's
JSON-RPC to a capture file, which is the record and is screened before
it is committed. The claim and the query travel as the caller's own
text, labeled so, and a count can carry a value, so the person reads the
message before sending it. The literals line lists the constants in the
query's parse tree; a value can still ride in a subquery (a LIMIT that
is itself a SELECT), an alias, or the claim, and the person's reading is
the control. A refusal's remedy is the one class of directing text a
result of this tool carries: the server's own code about its own
interface, which the plan asks for. An `@` is refused in the claim and
listed when it sits in a query literal; E1T opens no issue, and the
tracker's `@` workflow is the control there (HW-56).
