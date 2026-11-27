## user 1
Using the metricmine-gold tools, I want to report something about the quantity field of invoice_lines to the people who own this data. What I am asking for is a rule or a flag: negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Include the query that returns those lines, and show me the message exactly as it was returned.

## assistant 1
Here is the message exactly as returned:

```
FEEDBACK
field: invoice_lines.quantity
kind: rule_wanted
claim: Negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Please add a rule or a flag (for example an is_stock_adjustment column) so the adjustment is stated rather than inferred from unit_price = 0.
query: SELECT * FROM gold.mart_invoice_lines_typed WHERE ((quantity < 0) AND (is_cancellation = CAST('f' AS BOOLEAN)))
rows matching: 90 at gold_invoice_lines_mapping 1.1.2, silver_invoice_lines 1.3.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: 0, CAST('f' AS BOOLEAN)
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

- **Checked against the data:** Before preparing it, I grouped the negative-quantity lines by cancellation status and price. There are 1,013 cancellation lines, all with a nonzero price. There are 90 non-cancellation lines, all with a zero price. So your claim holds in the served data.
- **The query:** It returns 90 rows, which is every non-cancellation negative line. I left out a `unit_price = 0` condition on purpose, so the query doesn't build in the inference you're asking the owners to stop relying on.
- **Not sent:** Nothing was written or sent. You need to send the message to the owners yourself.
- **Wording:** The `is_stock_adjustment` column name is only my suggestion, and the owners may prefer something else.
