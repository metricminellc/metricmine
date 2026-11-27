# cd-F1-r1
fixture: F1; repeat: 1

## user 1
Using the metricmine-gold tools, I want to report something about the quantity field of invoice_lines to the people who own this data. What I am asking for is a rule or a flag: negative quantities on lines that are not cancellations are zero-price stock adjustments, and a consumer should not have to infer an adjustment from the price. Include the query that returns those lines, and show me the message exactly as it was returned.

## assistant 1
I'll look at the invoice_lines schema and data in metricmine-gold, write the query that finds these lines, then prepare the feedback message.

The contract already says negative quantities come from cancellations or zero-price adjustments, with no flag for the second case. I'll check that the data matches the claim before writing the query.

I prepared the message and nothing has been sent; you send it yourself. Here it is exactly as the tool returned it:

```
FEEDBACK
field: invoice_lines.quantity
kind: rule_wanted
claim: Negative quantities on lines that are not cancellations are zero-price stock adjustments. A consumer should not have to infer an adjustment from the price. I am asking for a rule or a flag.
query: SELECT invoice_id, stock_code, product_description, customer_id, quantity, unit_price, invoiced_at, fact_hash_id FROM gold.mart_invoice_lines_typed WHERE ((NOT is_cancellation) AND (quantity < 0)) ORDER BY invoiced_at, invoice_id, stock_code
rows matching: 90 at gold_invoice_lines_mapping 1.1.2, silver_invoice_lines 1.3.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: 0
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

The tool reformatted my query: uppercase keywords and added parentheses. The logic is the same. This is the query as I wrote it:

```sql
select invoice_id, stock_code, product_description, customer_id, quantity, unit_price, invoiced_at, fact_hash_id
from gold.mart_invoice_lines_typed
where not is_cancellation and quantity < 0
order by invoiced_at, invoice_id, stock_code
```

Before writing it, I checked your claim against the data:

- **Your claim holds.** All 90 negative-quantity lines that aren't cancellations have a unit price of 0.00. None of them has a customer ID, and their descriptions read like adjustments: "lost", "damages", "short", "sold as gold".
- **Cancellations look different.** All 1,013 cancellation lines are negative and none has a zero price.
- **Price alone can't identify adjustments.** There are another 166 zero-price lines with positive quantities. A consumer who used "price is zero" as the test would pick those up too. You could add that to the message if you want a stronger case for a flag.
- **The contract already describes this case.** The silver contract's description of `quantity` says negative values come from cancellations or zero-price adjustments. It also has a decision, `decisionNegativeQuantityCause: cancellation-or-zero-price-adjustment`. But adjustments get no column of their own, while cancellations have `is_cancellation`. Your request fills that gap.
