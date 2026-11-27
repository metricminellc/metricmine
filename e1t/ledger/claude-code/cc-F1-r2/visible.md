## user 1
Using the metricmine-gold tools, I want to report something about the quantity field of invoice_lines to the people who own this data. What I am asking for is a rule or a flag: negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Include the query that returns those lines, and show me the message exactly as it was returned.

## assistant 1
Let me check the query before preparing the message.

Here is the message exactly as the tool returned it:

```
FEEDBACK
field: invoice_lines.quantity
kind: rule_wanted
claim: Negative quantities on lines that are not cancellations (is_cancellation = false) are zero-price stock adjustments. In the served data all 90 such lines have unit_price = 0.00, and none have a nonzero price. A consumer should not have to infer an adjustment from the price. Please add a rule or flag (for example an is_stock_adjustment column) that marks these lines explicitly.
query: SELECT * FROM gold.mart_invoice_lines_typed WHERE ((quantity < 0) AND (is_cancellation = CAST('f' AS BOOLEAN)))
rows matching: 90 at gold_invoice_lines_mapping 1.1.2, silver_invoice_lines 1.3.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: 0, CAST('f' AS BOOLEAN)
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

- **Not sent:** The tool wrote nothing and sent nothing. You need to send the message to the data owners yourself.
- **Check against the data:** Before preparing it, I grouped the table by cancellation, negative quantity and zero price. All 90 non-cancellation lines with negative quantity have a unit price of 0.00. Every other line with a negative quantity is a cancellation (1,013 of them, all with a nonzero price). The claim text states the 90 and the zero price as measured facts. That the lines are stock adjustments is your claim, not something the data states.
- **Query wording:** I left the zero-price condition out of the query, so it returns all 90 non-cancellation negatives. The tool rewrote the boolean literal as `CAST('f' AS BOOLEAN)`, which means the same as `is_cancellation = false`.
- **Sample rows:** Several of them have odd descriptions such as "short" or "85123a mixed", and many have no customer_id. That supports your point but is not in the message.
