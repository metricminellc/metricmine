Here is the feedback message, ready for you to send:

```
FEEDBACK
field: invoice_lines.quantity
kind: meaning_wrong
claim: The description "Units on the line; negative only on cancellations." does not hold: negative quantities also appear on non-cancellation lines at a zero unit price.
query: select *
from gold.mart_invoice_lines_typed
where not is_cancellation and quantity < 0
rows matching: 90 at gold_invoice_lines_mapping v1.1.1, silver_invoice_lines v1.3.0, gold_unified_event_star v1.6.0
reference: none
END FEEDBACK
```

Let me know if you want changes.
