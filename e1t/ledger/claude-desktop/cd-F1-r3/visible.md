# cd-F1-r3
fixture: F1; repeat: 3

## user 1
Using the metricmine-gold tools, I want to report something about the quantity field of invoice_lines to the people who own this data. What I am asking for is a rule or a flag: negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Include the query that returns those lines, and show me the message exactly as it was returned.

## assistant 1
I'll check the invoice_lines schema, run the query, and then prepare the feedback.

The data matches the contract's own description: all 90 non-cancellation lines with a negative quantity have a zero unit price. Now I'll prepare the message.

The message is ready below. Nothing was sent; you send it to the data owners yourself.

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

I used the kind `rule_wanted`, since you're asking for a rule or a flag. The tool rewrote the query into its normalized form, but the logic is the same as what I sent. The `query literals: 0` line means the query contains one literal, the number `0`. It doesn't mean there are zero literals.

The data backs up your claim:

- **Every one of the 90 lines has a zero price.** Of all invoice_lines rows, 90 have a negative quantity and aren't cancellations, and all 90 have a unit price of zero. All 1,013 cancellation lines with a negative quantity have a non-zero price.
- **The owners already describe the pattern.** Their notes record it as a decision (`decisionNegativeQuantityCause: cancellation-or-zero-price-adjustment`). They also warn that "a negative quantity alone does not mean a cancellation." But the typed table only has an `is_cancellation` column and nothing that marks adjustments. That's exactly the gap your request points at.
