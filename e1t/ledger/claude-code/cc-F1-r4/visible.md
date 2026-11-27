## user 1
Using the metricmine-gold tools, I want to report something about the quantity field of invoice_lines to the people who own this data. What I am asking for is a rule or a flag: negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Include the query that returns those lines, and show me the message exactly as it was returned.

## assistant 1
Let me check the context and verify the claim with data first.

The data confirms the claim: 90 non-cancellation negative lines, all zero-price. Preparing the message.

Here is the message exactly as returned:

```
FEEDBACK
field: invoice_lines.quantity
kind: rule_wanted
claim: Negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Please add a rule or a flag (e.g. an is_stock_adjustment column) so adjustments are identified explicitly. Measured: of 90 non-cancellation lines with quantity < 0, all 90 have unit_price = 0.
query: SELECT * FROM gold.mart_invoice_lines_typed WHERE ((quantity < 0) AND (is_cancellation = CAST('f' AS BOOLEAN)))
rows matching: 90 at gold_invoice_lines_mapping 1.1.2, silver_invoice_lines 1.3.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: 0, CAST('f' AS BOOLEAN)
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

Notes:
- **Verified before preparing:** 90 lines have a negative quantity and are not cancellations, and all 90 have `unit_price = 0`. The 1,013 negative-quantity cancellation lines all have a positive price. That matches your claim.
- **Already documented, but not flagged:** the contract's `decisionNegativeQuantityCause` is "cancellation-or-zero-price-adjustment". Its quantity meaning also warns that a negative quantity alone doesn't mean a cancellation. There is no column that marks an adjustment, so the request is for a flag.
- **Wording I added:** the claim text includes a suggested column name (`is_stock_adjustment`) and the 90/90 measurement. Both were my additions to your request.
- **Not sent:** the tool only prepares the message. It wrote nothing and sent nothing, so you need to send it to the data owners.
