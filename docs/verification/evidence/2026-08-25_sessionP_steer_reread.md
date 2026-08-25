# Session P steer re-read: a live agent takes the mart path

Environment: Claude Desktop over stdio against the committed `demo/demo.duckdb`, the `metricmine-gold` server relaunched from the merged repository after a full quit of Claude Desktop; keyless, no API key anywhere in the loop. The prep measured the pre-relaunch half (the running server returned only `category`, `fact_table`, and `row_count` from `list_fact_categories`); this file records the post-relaunch run, the behavior measurement Stage 8 exists to take (D-31 and D-32 as amended by Amendment L; Amendment M for the served-case posture).

Question asked, exactly: "Using the metricmine-gold tools, what are the top five countries by revenue, excluding cancellations?"

## Tool calls, in order

The agent opened with: "I'll load the MetricMine tools and check what's in the gold layer."

### 1. `list_fact_categories`

Response:

```json
{
  "categories": [
    {
      "category": "invoice_lines",
      "fact_table": "fact_invoice_lines_values",
      "row_count": 44721,
      "typed_table": "mart_invoice_lines_typed",
      "typed_columns": [
        "invoice_id",
        "is_cancellation",
        "stock_code",
        "product_description",
        "customer_id",
        "country",
        "invoiced_at",
        "quantity",
        "unit_price",
        "fact_hash_id"
      ],
      "query_hint": "Ask questions against gold.mart_invoice_lines_typed (typed columns, one row per invoice_lines event). gold.fact_invoice_lines_values and the dim_* tables are the content-addressed provenance layer: hash keys and canonical JSON payloads, joined by hash, meant for lookup_record and audit, not for analytics."
    }
  ]
}
```

### 2. `get_context`

Request:

```json
{
  "schema_key": "invoice_lines"
}
```

Response:

```json
{
  "found": false,
  "schema_key": "invoice_lines",
  "contract_name": null,
  "contract_version": null,
  "compiled_context": null
}
```

### 3. `query`: the catalog listing

Request:

```json
{
  "sql": "select table_schema, table_name from information_schema.tables order by 1,2",
  "row_cap": 200
}
```

Response:

```json
{
  "columns": ["table_schema", "table_name"],
  "rows": [
    ["gold", "context_registry"],
    ["gold", "dim_invoice_lines_columns"],
    ["gold", "dim_invoice_lines_values"],
    ["gold", "dim_run_columns"],
    ["gold", "dim_run_values"],
    ["gold", "dim_source_columns"],
    ["gold", "dim_source_values"],
    ["gold", "dim_timeframe_columns"],
    ["gold", "dim_timeframe_values"],
    ["gold", "fact_invoice_lines_values"],
    ["gold", "mart_invoice_lines_typed"],
    ["gold", "vw_invoice_lines_typed"]
  ],
  "row_count": 12,
  "truncated": false,
  "row_cap": 200
}
```

### 4. `query`: the context registry

Request:

```json
{
  "sql": "select * from gold.context_registry limit 20",
  "row_cap": 20
}
```

Response:

```json
{
  "columns": [
    "schema_key",
    "entity_group",
    "contract_name",
    "contract_version",
    "compiled_context",
    "loaded_at"
  ],
  "rows": [
    [
      "61e74223d961799a0f8b12bf9045b422b5cad4fc9273e1ce3f65eb07966a2e1f",
      "source",
      "gold_invoice_lines_mapping",
      "1.1.0",
      "{\"manifest\":[\"source_table\"],\"role\":\"source\",\"source_table\":\"silver.silver_invoice_lines\"}",
      "2026-08-25 10:35:57"
    ],
    [
      "dacafb1855b6ce1628eb3be9b6c8eeeedc3d4f45454a6fd87093deda9d0cc848",
      "run",
      "gold_invoice_lines_mapping",
      "1.1.0",
      "{\"manifest\":[\"mapping_contract_name\",\"mapping_contract_version\",\"engine_version\"],\"role\":\"run\"}",
      "2026-08-25 10:35:57"
    ],
    [
      "8f99de0c5aa34c2e3e2e66890f7b986f0c2d39b9276b901f1232efd0ebcc0dd8",
      "timeframe",
      "gold_invoice_lines_mapping",
      "1.1.0",
      "{\"fields\":{\"invoiced_at\":{\"description\":\"Invoice timestamp; the declared time column.\",\"logicalType\":\"date\",\"mappingRole\":\"time\",\"physicalType\":\"TIMESTAMP\"}},\"manifest\":[\"invoiced_at\"],\"role\":\"timeframe\",\"time_grain\":\"minute\"}",
      "2026-08-25 10:35:57"
    ],
    [
      "2d27bd360b5092ff22047c65407ff05699afad98f455de2409665a5950a05e82",
      "invoice_lines",
      "gold_invoice_lines_mapping",
      "1.1.0",
      "{\"derived_identifiers\":{\"line_identity\":{\"derivation\":\"canonical-key-v2\",\"of\":[\"invoice_id\",\"stock_code\",\"quantity\",\"unit_price\"],\"source\":\"derived\"}},\"fields\":{\"country\":{\"description\":\"Customer country as landed; the signature-test dimension, mapped at v1.1.0.\",\"logicalType\":\"string\",\"mappingRole\":\"dimension\",\"physicalType\":\"VARCHAR\"},\"customer_id\":{\"description\":\"Customer identifier; null on guest checkouts.\",\"logicalType\":\"integer\",\"mappingRole\":\"dimension\",\"physicalType\":\"INTEGER\"},\"invoice_id\":{\"description\":\"Invoice number; C prefix marks a cancellation.\",\"logicalType\":\"string\",\"mappingRole\":\"dimension\",\"physicalType\":\"VARCHAR\"},\"is_cancellation\":{\"description\":\"Cancellation flag; exclusion is a consumer decision.\",\"logicalType\":\"boolean\",\"mappingRole\":\"dimension\",\"physicalType\":\"BOOLEAN\"},\"product_description\":{\"description\":\"Product description; nulls retained.\",\"logicalType\":\"string\",\"mappingRole\":\"dimension\",\"physicalType\":\"VARCHAR\"},\"stock_code\":{\"description\":\"Product code as landed.\",\"logicalType\":\"string\",\"mappingRole\":\"dimension\",\"physicalType\":\"VARCHAR\"}},\"manifest\":[\"invoice_id\",\"is_cancellation\",\"stock_code\",\"product_description\",\"customer_id\",\"country\",\"line_identity\"],\"role\":\"dimensions\",\"source_table\":\"silver.silver_invoice_lines\",\"typed_surface\":\"mart_invoice_lines_typed\"}",
      "2026-08-25 10:35:57"
    ],
    [
      "9dbc23cabca765eeaed72eb8161c90b5ae7857f81031656002f03e5bd9d99319",
      "invoice_lines",
      "gold_invoice_lines_mapping",
      "1.1.0",
      "{\"fields\":{\"quantity\":{\"description\":\"Units on the line; negative only on cancellations.\",\"logicalType\":\"integer\",\"mappingRole\":\"measure\",\"physicalType\":\"INTEGER\"},\"unit_price\":{\"description\":\"Unit price in sterling; zero-price lines retained.\",\"logicalType\":\"number\",\"mappingRole\":\"measure\",\"physicalType\":\"DECIMAL(10,2)\"}},\"manifest\":[\"quantity\",\"unit_price\"],\"role\":\"measures\",\"source_table\":\"silver.silver_invoice_lines\",\"typed_surface\":\"mart_invoice_lines_typed\"}",
      "2026-08-25 10:35:57"
    ]
  ],
  "row_count": 5,
  "truncated": false,
  "row_cap": 20
}
```

*Agent narration: "Identified revenue calculation gap and flagged consumer-side derivation requirement."*

### 5. `query`: the first analytical read, against the mart

Request:

```json
{
  "sql": "select\n  count(*) as rows_total,\n  sum(case when is_cancellation then 1 else 0 end) as cancellation_rows,\n  sum(case when is_cancellation is null then 1 else 0 end) as cancel_flag_null,\n  sum(case when not is_cancellation and quantity < 0 then 1 else 0 end) as neg_qty_noncancel,\n  sum(case when not is_cancellation and unit_price < 0 then 1 else 0 end) as neg_price_noncancel,\n  sum(case when not is_cancellation and unit_price = 0 then 1 else 0 end) as zero_price_noncancel,\n  sum(case when country is null then 1 else 0 end) as country_null,\n  count(distinct country) as country_distinct,\n  min(invoiced_at) as first_event,\n  max(invoiced_at) as last_event\nfrom gold.mart_invoice_lines_typed"
}
```

Response:

```json
{
  "columns": [
    "rows_total",
    "cancellation_rows",
    "cancel_flag_null",
    "neg_qty_noncancel",
    "neg_price_noncancel",
    "zero_price_noncancel",
    "country_null",
    "country_distinct",
    "first_event",
    "last_event"
  ],
  "rows": [
    [44721, 1013, 0, 90, 0, 256, 0, 24, "2009-12-01 07:45:00", "2009-12-23 16:58:00"]
  ],
  "row_count": 1,
  "truncated": false,
  "row_cap": 100
}
```

### 6. `query`: rows and cancellations per country

Request:

```json
{
  "sql": "select country, count(*) as rows,\n  sum(case when is_cancellation then 1 else 0 end) as cancel_rows\nfrom gold.mart_invoice_lines_typed\ngroup by 1 order by 2 desc",
  "row_cap": 50
}
```

Response:

```json
{
  "columns": ["country", "rows", "cancel_rows"],
  "rows": [
    ["united kingdom", 42354, 867],
    ["eire", 596, 18],
    ["germany", 417, 34],
    ["france", 337, 54],
    ["spain", 237, 3],
    ["cyprus", 195, 5],
    ["netherlands", 155, 0],
    ["portugal", 98, 0],
    ["united arab emirates", 57, 1],
    ["channel islands", 43, 4],
    ["greece", 41, 0],
    ["austria", 38, 0],
    ["australia", 27, 13],
    ["italy", 24, 5],
    ["poland", 22, 0],
    ["norway", 21, 0],
    ["belgium", 20, 0],
    ["switzerland", 15, 0],
    ["denmark", 11, 3],
    ["finland", 4, 0],
    ["japan", 3, 3],
    ["sweden", 3, 1],
    ["nigeria", 2, 2],
    ["usa", 1, 0]
  ],
  "row_count": 24,
  "truncated": false,
  "row_cap": 50
}
```

### 7. `query`: revenue by country, cancellations excluded

Request:

```json
{
  "sql": "select\n  country,\n  round(sum(quantity * unit_price), 2) as revenue_gbp,\n  count(*) as line_count,\n  count(distinct invoice_id) as invoices,\n  round(sum(case when quantity < 0 then quantity * unit_price else 0 end), 2) as neg_qty_effect\nfrom gold.mart_invoice_lines_typed\nwhere not is_cancellation\ngroup by 1\norder by revenue_gbp desc",
  "row_cap": 30
}
```

Response:

```json
{
  "columns": ["country", "revenue_gbp", "line_count", "invoices", "neg_qty_effect"],
  "rows": [
    ["united kingdom", "747367.59", 41487, 1842, "0.00"],
    ["eire", "20099.74", 578, 20, "0.00"],
    ["netherlands", "15204.73", 155, 6, "0.00"],
    ["germany", "9830.27", 383, 18, "0.00"],
    ["spain", "7950.18", 234, 5, "0.00"],
    ["france", "6521.69", 283, 13, "0.00"],
    ["cyprus", "3541.68", 190, 4, "0.00"],
    ["portugal", "2821.58", 98, 2, "0.00"],
    ["austria", "1998.34", 38, 2, "0.00"],
    ["denmark", "1437.66", 8, 2, "0.00"],
    ["channel islands", "989.18", 39, 1, "0.00"],
    ["greece", "610.95", 41, 1, "0.00"],
    ["switzerland", "589.40", 15, 1, "0.00"],
    ["finland", "549.08", 4, 1, "0.00"],
    ["united arab emirates", "517.70", 56, 1, "0.00"],
    ["norway", "485.31", 21, 1, "0.00"],
    ["belgium", "447.60", 20, 3, "0.00"],
    ["italy", "422.35", 19, 1, "0.00"],
    ["poland", "371.82", 22, 1, "0.00"],
    ["sweden", "285.30", 2, 1, "0.00"],
    ["australia", "271.10", 14, 2, "0.00"],
    ["usa", "141.00", 1, 1, "0.00"]
  ],
  "row_count": 22,
  "truncated": false,
  "row_cap": 30
}
```

### 8. `query`: the negative-quantity probe

Request:

```json
{
  "sql": "select\n  count(*) as neg_qty_rows,\n  sum(case when unit_price = 0 then 1 else 0 end) as with_zero_price,\n  min(invoice_id) as sample_invoice_min,\n  max(invoice_id) as sample_invoice_max,\n  sum(quantity) as total_units\nfrom gold.mart_invoice_lines_typed\nwhere not is_cancellation and quantity < 0"
}
```

Response:

```json
{
  "columns": ["neg_qty_rows", "with_zero_price", "sample_invoice_min", "sample_invoice_max", "total_units"],
  "rows": [
    [90, 90, "489463", "493406", -15755]
  ],
  "row_count": 1,
  "truncated": false,
  "row_cap": 100
}
```

*Agent narration: "Calculating country revenue shares and identifying UK dominance." then "Filtered cancellations and synthesized country revenue rankings comprehensively."*

## The agent's answer

Top five countries by revenue, cancellation lines excluded:

| # | Country | Revenue (GBP) | Lines | Invoices | Share |
|---|---------|--------------:|------:|---------:|------:|
| 1 | United Kingdom | 747,367.59 | 41,487 | 1,842 | 90.9% |
| 2 | Eire | 20,099.74 | 578 | 20 | 2.4% |
| 3 | Netherlands | 15,204.73 | 155 | 6 | 1.8% |
| 4 | Germany | 9,830.27 | 383 | 18 | 1.2% |
| 5 | Spain | 7,950.18 | 234 | 5 | 1.0% |

Those five account for 97.3% of the £822,454 non-cancellation total across 22 countries.

A few things worth knowing about how I got there:

**Revenue is my derivation, not a contract measure.** The gold contract (`gold_invoice_lines_mapping` v1.1.0) declares `quantity` and `unit_price` as measures. It does not declare a revenue metric. I computed `sum(quantity * unit_price)`. Prices are in sterling per the contract field description.

**The cancellation filter is exactly the decision the contract anticipates.** The `is_cancellation` description reads "exclusion is a consumer decision," so this is a documented consumer choice rather than an assumption I imposed.

**One contract deviation surfaced.** The contract says quantity is "negative only on cancellations." I found 90 rows with negative quantity that are not flagged as cancellations, totaling -15,755 units. All 90 carry a unit price of zero, so they contribute exactly £0 and do not move the ranking. They look like adjustment or write-off lines. The flag description is still inaccurate as written, which may be worth a contract note.

**Two other observations.** Spain outranks France despite France having more lines (234 vs 283), and France carried 54 cancellation rows against Spain's 3. Japan and Nigeria disappear from the ranking entirely because every one of their rows is a cancellation. Also, this dataset covers December 1 through December 23, 2009 only. It is a three-week slice, not a full period, so read the country mix accordingly.

## Read against the EXPECT

- `list_fact_categories` returned `typed_table: mart_invoice_lines_typed`, the ten `typed_columns` in ordinal order, and the `query_hint` (Amendment L). Before the relaunch the same server returned only `category`, `fact_table`, and `row_count` (the prep measurement).
- The first analytical query (call 5) and every analytical query after it (calls 6, 7, 8) targeted `gold.mart_invoice_lines_typed`. No query touched `fact_invoice_lines_values` or any `dim_*` table. The two non-mart reads were `information_schema.tables` (call 3, a catalog listing) and `gold.context_registry` (call 4, the provenance layer read for its compiled context), neither an analytical query.
- Values came back lowercased (`united kingdom`, `eire`, `netherlands`), the served-case posture of Amendment M; the agent restored display case in its own answer table.
- Observed, not judged: `get_context` with `schema_key: invoice_lines` returned `found: false` (schema keys are content hashes, not category names), and the agent then read `gold.context_registry` directly and found the `typed_surface: mart_invoice_lines_typed` pointer on the category-group entries.
- The agent derived revenue as `sum(quantity * unit_price)` itself and said so; the contract declares no revenue measure. Its finding of 90 non-cancellation negative-quantity rows, all at zero price, is recorded here as it stated it.
