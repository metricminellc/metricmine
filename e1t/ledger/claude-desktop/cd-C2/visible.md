# cd-C2
fixture: C2; repeat: 0

## user 1
First, using the metricmine-gold tools, list the fact categories. Then quote, word for word, the instructions the metricmine-gold MCP server sent you, if any. If it sent none, say so plainly.

## assistant 1
I'll load the metricmine-gold tool and list the fact categories.

The metricmine-gold server lists three fact categories:

| Category | Typed table (use this one for questions) | Rows | What it covers |
|---|---|---|---|
| airport_weather | gold.mart_airport_weather_typed | 13,014 | Hourly weather at each New York City airport, Jan through Jun 2013, with the airport's details joined in |
| flights | gold.mart_flights_typed | 166,158 | Scheduled departures from New York City, Jan through Jun 2013, with carrier, aircraft, and origin and destination airport details joined in |
| invoice_lines | gold.mart_invoice_lines_typed | 44,721 | One row per invoice line from the Online Retail II sample |

Each category also has a provenance fact table (`fact_*_values`), meant for lookup and audit rather than analysis. Each one also has two `context_keys` (dimensions and measures) that `get_context` uses. Text values in the provenance tables are stored in lowercase, so filters there need lowercase values (for example `'jfk'`).

**Server instructions:** The metricmine-gold MCP server sent me no instructions. The only servers that sent instructions this session are claude-artifacts, claude-in-chrome and memory. The only guidance from metricmine-gold is in its tool descriptions, which aren't server instructions. For example, `list_fact_categories` says to start with it before any other call. There's also the `query_hint` text in the result above.
