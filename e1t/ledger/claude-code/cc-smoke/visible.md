## user 1
Using the metricmine-gold tools, list the fact categories.

## assistant 1
There are three fact categories in the metricmine-gold layer:

| Category | Rows | Typed table | Subject |
|---|---|---|---|
| **airport_weather** | 13,014 | `mart_airport_weather_typed` | One row per New York City airport per hour, January to June 2013. It has observed conditions (temperature, dewpoint, humidity, wind, precipitation, pressure, visibility) plus airport reference attributes. |
| **flights** | 166,158 | `mart_flights_typed` | One row per scheduled departure from New York City, January to June 2013. It joins in carrier, aircraft, and origin and destination airport details, along with delay, air-time, and distance measures. |
| **invoice_lines** | 44,721 | `mart_invoice_lines_typed` | One row per invoice line from the Online Retail II sample. It is cleaned and typed, and it is the only silver input to the gold star. Columns include invoice, stock code, product, customer, country, quantity, and unit price. |

Each category also has two context keys, one for dimensions and one for measures. `get_context` resolves them to column definitions and the expert notes on units, vintages, nulls, and joins.

I can read the context for any of these or query a typed table if you'd like.
