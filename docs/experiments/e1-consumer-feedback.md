# E1, the consumer feedback loop, staged: the canary (October 21, 2026)

> Repo path: `docs/experiments/e1-consumer-feedback.md`
> An experiments-lane record (CLAUDE.md rule 19). It mints no decision
> and no finding. The serving layer is unchanged: five tools (D-31 as
> amended through Amendment AB), and the instructions text as it stands
> on main.

## The question

Can a consumer's agent prepare feedback about a served field that the
data's producer can re-measure on its own build? And does that take a
sixth server tool, or only a paragraph of server instructions? D-31 holds
the surface at five tools and no sixth, so the experiment was staged: a
paragraph of `instructions` first (stage 1), and a tool only if the
paragraph could not carry a message a producer can re-measure (stage 2).
Every graduation would be a D-31 amendment by its own documentation pull
request, and nothing would be submitted to the public tracker by any
run.

Stage 1 was designed as fifteen fresh Claude Desktop conversations on a
branch, `experiment/consumer-feedback`, against the v1.1.1 release asset
pinned by its sha256 (the pinned served file, on which a served sentence
and the rows disagree: the quantity meaning that main corrected at
`gold_invoice_lines_mapping` v1.1.2, F-62), with every transcript
committed, a command and never an agent re-measuring each message, and a
verdict rule committed before the first run.

## The canary that gates stage 1

A paragraph of server instructions can only be tested on a host that
passes the server's `instructions` to its model. Whether Claude Desktop
does was unmeasured. So the first step was a canary: in a fresh
conversation, ask the model to quote the instructions, and look for a
phrase that sits in the instructions and in no tool description. If the
host does not pass the instructions, stage 1 cannot run on it, and a
tool-first design would need its own rule, cut and read before anything
is built.

The reading rule, fixed before the run: a reply that quotes either
phrase passes. A plain report that the server sent no instructions
fails. A refusal, or a paraphrase that carries neither phrase, is
ambiguous, and the question is asked again in a fresh conversation
after a tool has run.

The two phrases, both in the instructions since v1.1.0 (Amendment W):

- `Cite which of the two an answer rests on`
- `the warehouse is the measurement`

Measured on a fresh clone of main at `2f73dfc` on October 21, 2026,
through the real server over stdio with a vendor-neutral MCP client
(`initialize`, `tools/list`, then `list_fact_categories`, `get_context`,
and `query`): the instructions are 3,812 characters, sha256
`0ccdd17147c5044e1b04ef57e6413a3604876ac91eee5ae70a7773352ac918ba`. Both
phrases are in them, whitespace folded. Neither phrase is in any of the
five tools' descriptions or titles. The five tools carry their titles
and the four annotations. The same server answers the same way against
the v1.1.1 and the v1.2.0 assets; the instructions do not depend on the
served file.

## What ran

- Host: Claude Desktop 3.1623.0 on macOS, keyless. Model: "Sonnet 5.5
  Extra", as the conversation's picker names it. The `metricmine-gold`
  server was enabled in every conversation. The paste notes no
  permission prompt; each tool-using conversation showed two "Loaded
  tools, used metricmine-gold integration" steps in the chat.
- The server: Desktop's config entry launches the working clone's
  interpreter (`.venv/bin/python -m metricmine.server`, no environment),
  and the clone was clean on main at `2f73dfc` by the sitting's own
  read-only lines. Which server process answered is not measured by the
  replies: Desktop's log records each message by method, never its
  payload, and the `query_hint` text the third reply quotes is the same
  at `2f73dfc` and at the previous head. The served file was the
  clone's `demo/demo.duckdb`, which held the v1.2.0 export since the
  Prep C close; the row counts in the replies (airport_weather 13,014,
  flights 166,158, invoice_lines 44,721) match that export and the
  v1.1.1 asset alike.
- Three fresh conversations, one message each, sent exactly as written
  below. The replies are quoted whole as the person pasted them; the
  lines "Thought for 2s" and "Loaded tools, used metricmine-gold
  integration" are Desktop's own interface text.

### Conversation 1, no tool call

Sent:

    Quote, word for word, the instructions the metricmine-gold MCP server sent when it connected. Do not call any tool. If that server sent you no instructions, say so plainly.

Reply (after two "Thought for 2s" lines):

> The metricmine-gold server sent me no instructions. All I have from it
> is a listing of five deferred tools (get_context, get_schema,
> list_fact_categories, lookup_record, and query) with one-line
> descriptions. I haven't loaded their full definitions, and there's no
> server-level instruction text for me to quote.

### Conversation 2, one tool call

Sent:

    Using the metricmine-gold tools, list the fact categories.

Reply (after two "Loaded tools, used metricmine-gold integration"
lines):

> The metricmine-gold server has three fact categories.
>
> | Category | Fact table | Rows | Typed table |
> |---|---|---|---|
> | airport_weather | fact_airport_weather_values | 13,014 | mart_airport_weather_typed |
> | flights | fact_flights_values | 166,158 | mart_flights_typed |
> | invoice_lines | fact_invoice_lines_values | 44,721 | mart_invoice_lines_typed |
>
> airport_weather holds one row per New York City airport per hour,
> January through June 2013. It joins each observation to the airport's
> reference attributes on the conformed airport code. It has 19 typed
> columns, including temp_f, wind_speed_mph, precip_inches, and
> visibility_miles.
>
> flights holds one row per scheduled departure from New York City,
> January through June 2013. Carrier, aircraft, and origin and
> destination airport details are joined in. It has 35 typed columns,
> including dep_delay_minutes, arr_delay_minutes, distance_miles, and
> is_cancelled.
>
> invoice_lines is the cleaned, typed, one-row-per-line view of the
> Online Retail II sample. It is the first contracted silver table and
> the only silver input to the gold unified event star. It has 11 typed
> columns, including invoice_id, stock_code, customer_id, quantity, and
> unit_price.
>
> Analytics queries should target the mart_*_typed tables. The
> fact_*_values and dim_* tables are the content-addressed provenance
> layer, meant for lookup_record and audit. String literals there are
> lowercase, for example origin_airport = 'jfk'.
>
> Each category exposes two context keys, dimensions and measures.
> get_context resolves them to column definitions and the contract
> authors' notes on units, vintages, nulls, and joins. I can pull the
> context for any category or run a query against one of the typed
> tables.

### Conversation 3, the tools loaded and used, then the quote

The first reply described a listing of five deferred tools with
one-line descriptions and said their full definitions were not loaded,
and Desktop's own interface shows a "Loaded tools" step once a tool is
used. Whether a definition load also brings the instructions was the
open case, so a third conversation asked for the quote after a tool had
run.

Sent:

    First, using the metricmine-gold tools, list the fact categories. Then quote, word for word, the instructions the metricmine-gold MCP server sent you, if any. If it sent none, say so plainly.

Reply (after two "Loaded tools, used metricmine-gold integration"
lines):

> Here are the three fact categories:
>
> | Category | Fact table | Rows | Typed table |
> |---|---|---|---|
> | airport_weather | fact_airport_weather_values | 13,014 | mart_airport_weather_typed |
> | flights | fact_flights_values | 166,158 | mart_flights_typed |
> | invoice_lines | fact_invoice_lines_values | 44,721 | mart_invoice_lines_typed |
>
> airport_weather has one row per NYC airport per hour, January through
> June 2013. flights has one row per scheduled NYC departure in the same
> window. invoice_lines is the typed, one-row-per-line view of the
> Online Retail II sample.
>
> Server instructions: The metricmine-gold server did not send me a
> separate instructions block, such as a system prompt or server-level
> guidance. What I received was:
>
> Tool descriptions. These are the standard docstrings for the five
> tools: list_fact_categories, lookup_record, get_context, get_schema and
> query.
> A query_hint field in each category of the tool result. This is usage
> guidance embedded in the data, not an instruction channel. The text is
> the same template for all three categories with the names swapped. For
> airport_weather it reads:
> Ask questions against gold.mart_airport_weather_typed (typed columns,
> one row per airport_weather event). gold.fact_airport_weather_values
> and the dim_* tables are the content-addressed provenance layer: hash
> keys and canonical JSON payloads, joined by hash, meant for
> lookup_record and audit, not for analytics. String columns there carry
> canonical lowercase text: write literals in lowercase (origin_airport =
> 'jfk'). get_context on the keys in context_keys returns what the
> columns are (data) and, kept apart by name, what the people who
> approved the contracts wrote about them (expert_context): units,
> vintages, nulls, joins.
>
> I didn't act on the hint beyond listing the categories, which is all
> you asked for.

## The result

The canary fails. Neither phrase appears in any reply, and no reply
quotes the instructions. Both replies that addressed the question
reported that the server sent no instructions. What the model reported
instead is what reached it: the tools' descriptions, which it named,
and the `query_hint` field of the `list_fact_categories` result, which
it reproduced word for word. So on this host and this model, the
server's `instructions` do not reach the model, at connect or after a
tool loads. The tool that ran answered as designed; the sentences the
model repeated about the typed tables, the lowercase literals, and the
two context keys are the `query_hint` text that D-31 as amended by
Amendments L and W put into the tool result, so that the steer reaches
an agent at its first call.

## What the result bounds

- Stage 1 does not run on this host. A paragraph of instructions cannot
  be tested where no instructions arrive, and a baseline and an arm
  would serve the model the same text. The experiment ends at this
  record; the fifteen conversations, the branch, and the measuring
  command were prepared and are not run.
- On Claude Desktop 3.1623.0 with this model, guidance in `instructions`
  is not load-bearing for anything, which is the posture the serving
  design already took (the governed host workflow's design rule 1:
  guidance in instructions is never load-bearing for a read). Every
  steer that reaches a model here travels in a tool description or in a
  tool result: the `query_hint`, the category `subject`, and the served
  note of the `documents` block, which carries the sentence that a
  consumer treats what it reads at a document's location as data, never
  as instructions (Amendment AA). The instructions' own copies of those
  sentences are not read here.
- A measurement of one host, one build, one model, one day. Another host,
  or another build of this one, is named as passing instructions only
  when measured the same way. A host or model change re-opens the
  measurement.
- The measurement rests on what the model reports and quotes. Desktop's
  log keeps no payloads, so where the text is dropped is not measured.
- No defect at head. The tool the canary called (`list_fact_categories`)
  answered what the server holds, the sandbox probe's calls over stdio
  (`list_fact_categories`, `get_context`, `query`) did the same, and the
  gate set at `2f73dfc` is green; `get_schema` and `lookup_record` were
  not exercised by the canary. No finding is minted, and the website's
  counts do not move.

## What remains possible

- A host that passes `instructions`: the staged design runs there as
  cut, under its own canary first.
- A tool-first form of the experiment, where the guidance a host does
  pass (a tool's description) carries the layout and the offer. It needs
  its own verdict rule, cut and read before anything is built, and it
  would add a sixth tool on a branch only; the five-tool surface on main
  changes only by a D-31 amendment. It is not designed here.
- The producer's side needs no host at all: a command that re-measures
  a five-part message on a second build was built and tested in the
  experiment's preparation and is kept with the preparation records,
  outside this repository, for the form that runs next.

The lesson for a hosted version, now measured rather than assumed:
guidance that matters must survive a host that drops instructions, or be
measured per host. On this host it did not survive, and the tool
descriptions and tool results carried what mattered.

## Status

This record is the result the canary issue (#220) asked for, and the
reason the stage 1 issue (#221) does not run on this host. The
experiment's preparation is recorded outside the repository and was
never pushed: the pinned file, the second build at the v1.1.3 tag, the
key's fixed values carried in the instruments' code (the marker, the
layout, the extraction rule, the target field), the measuring command,
the capture shim, the screen, and the scorer, every one tested in a
sandbox.
