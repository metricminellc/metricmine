# cd-F1-r2
fixture: F1; repeat: 2

## user 1
Using the metricmine-gold tools, I want to report something about the quantity field of invoice_lines to the people who own this data. What I am asking for is a rule or a flag: negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Include the query that returns those lines, and show me the message exactly as it was returned.

## assistant 1
I'll check the invoice_lines schema and context first. Then I'll write and run the query for the non-cancellation negative-quantity lines and prepare the feedback message.

I prepared the feedback message. It matches 90 lines on the current served file. Here it is exactly as the tool returned it:

```
FEEDBACK
field: invoice_lines.quantity
kind: rule_wanted
claim: I am asking for a rule or a flag. Negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price.
query: SELECT invoice_id, stock_code, product_description, invoiced_at, quantity, unit_price, is_cancellation, fact_hash_id FROM gold.mart_invoice_lines_typed WHERE ((quantity < 0) AND (NOT is_cancellation)) ORDER BY invoiced_at, invoice_id, stock_code
rows matching: 90 at gold_invoice_lines_mapping 1.1.2, silver_invoice_lines 1.3.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: 0
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

The tool didn't save or send the message, so you'll need to send it to the data owners yourself.

**What I checked first:**
- **The claim holds.** All 90 matching lines have a unit_price of 0.00, with quantities from -2 to -1,395. The query doesn't filter on price, so the data owners can confirm the zero-price part themselves when they re-run it.
- **Cancellations are different.** All 1,013 cancellation lines have a negative quantity and a non-zero price, from 0.12 to 1,998.49.
- **The contract describes the pattern but doesn't flag it.** The mapping contract records negative quantities as coming from either a cancellation or a zero-price adjustment. It warns consumers not to read a negative quantity as a cancellation, but there's no field that marks the adjustment lines.

The data also gives one more argument you could add: 166 other lines have a zero price and a positive quantity, which the contract calls freebies. So a zero price alone doesn't identify an adjustment either. A consumer has to combine quantity, price and the cancellation flag to find these lines.
