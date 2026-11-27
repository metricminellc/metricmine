# cd-smoke
fixture: SMOKE; repeat: 0

## user 1
Using the metricmine-gold tools, list the fact categories.

## assistant 1
The gold server has 3 fact categories:

| Category | Typed table to query | Rows in fact table | Subject |
|---|---|---|---|
| `airport_weather` | `gold.mart_airport_weather_typed` (19 columns) | 13,014 | Hourly weather at the New York City airports, January to June 2013, with each airport's reference attributes joined in |
| `flights` | `gold.mart_flights_typed` (35 columns) | 166,158 | Scheduled departures from New York City, January to June 2013, with carrier, aircraft, and origin and destination airports joined in |
| `invoice_lines` | `gold.mart_invoice_lines_typed` (11 columns) | 44,721 | One row per invoice line from the Online Retail II sample |

The server's notes on querying:
- **Where to ask questions:** run them against the `mart_*_typed` tables. The `fact_*_values` tables and the `dim_*` tables hold hash keys and payloads. They're for `lookup_record` and audit, not for analysis.
- **Lowercase text:** text columns in the provenance layer are stored in lowercase, so filter values need to be lowercase too, for example `origin_airport = 'jfk'`.
- **Column details:** each category has two `context_keys`, one for dimensions and one for measures. Passing them to `get_context` returns what each column is and, kept separate, what the people who approved the contracts wrote about units, nulls, and joins.

The metricmine-gold server's instructions don't appear anywhere in this session. Everything above came from the tool's description and its result.
