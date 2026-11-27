## user 1
Using the metricmine-gold tools, I want to report something about the quantity field of invoice_lines to the people who own this data. What I am asking for is a rule or a flag: negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Include the query that returns those lines, and show me the message exactly as it was returned.

## assistant 1
Let me check the data first so the query is correct.

The message below is exactly as the tool returned it. Nothing has been sent, and you would need to send it yourself.

```
FEEDBACK
field: invoice_lines.quantity
kind: rule_wanted
claim: Negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Please add a rule or a flag (for example is_stock_adjustment) so the adjustment is marked explicitly. Today the contract says a negative quantity alone does not mean a cancellation, but the only way to identify an adjustment is to notice unit_price = 0. In the current data all 90 such lines have unit_price 0.00.
query: SELECT invoice_id, is_cancellation, stock_code, product_description, customer_id, country, invoiced_at, quantity, unit_price, fact_hash_id FROM gold.mart_invoice_lines_typed WHERE ((quantity < 0) AND (is_cancellation = CAST('f' AS BOOLEAN)))
rows matching: 90 at gold_invoice_lines_mapping 1.1.2, silver_invoice_lines 1.3.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: 0, CAST('f' AS BOOLEAN)
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

- **Rows:** the query matches 90 lines, and all 90 have `unit_price` 0.00. That agrees with the contract's `decisionNegativeQuantityCause` ("cancellation-or-zero-price-adjustment").
- **Claim wording:** the claim and query are my text, and the server checked them only through its read-only gate. I added the example flag name `is_stock_adjustment` and the 90-line observation to your request. Edit them if you'd rather not suggest a name.
