## user 1
Using the metricmine-gold tools, I want to report something about the quantity field of invoice_lines to the people who own this data. What I am asking for is a rule or a flag: negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Include the query that returns those lines, and show me the message exactly as it was returned.

## assistant 1
Here is the message, exactly as returned:

```
FEEDBACK
field: invoice_lines.quantity
kind: rule_wanted
claim: Negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Please add a rule or a flag (for example an is_stock_adjustment column) so the adjustment is stated, not inferred from unit_price = 0.
query: SELECT * FROM gold.mart_invoice_lines_typed WHERE ((quantity < 0) AND (is_cancellation = CAST('f' AS BOOLEAN)))
rows matching: 90 at gold_invoice_lines_mapping 1.1.2, silver_invoice_lines 1.3.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: 0, CAST('f' AS BOOLEAN)
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

- **Nothing has been sent.** The tool only prepares the message, so you need to send it to the data owners yourself.
- **Source for the claim:** the contract's expert context says negative quantity occurs on cancellation lines and on zero-unit-price stock-adjustment lines. It also says consumers must not infer cancellation from negative quantity alone. That is documentation, not a flag on the data.
- **Check against the data:** I ran a separate query on the 90 matching lines. All 90 have `unit_price = 0`, and all 90 have a null `customer_id`. Their quantities run from -1395 to -2.
- **The flag wording is mine.** The `is_stock_adjustment` column name is only a suggestion I added to your claim. Edit it if you'd rather leave the form of the fix to the owners.
