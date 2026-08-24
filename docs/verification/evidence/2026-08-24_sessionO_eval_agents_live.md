# eval-agents report

- created_at: 2026-08-24T14:49:39.030979+00:00
- model: claude-sonnet-5 (default); rates 2.0/10.0 USD per MTok; sdk 1.0.0
- fixtures: 3; drafts written: 3
- first-attempt lint pass rate: 1/3
- first-attempt groundedness pass rate: 1/3
- tokens: in 40416, out 25122; cost ~$0.3321

| label | proposer | stance | disposition | attempts | lint@1 | grounded@1 | in | out | cost |
|---|---|---|---|---|---|---|---|---|---|
| silver-cleanup-online-retail | silver-cleanup-proposer | cleanup | draft_written | 2 | no | no | 16565 | 10934 | $0.1425 |
| mapping-propose-invoice-lines | gold-mapping-proposer | propose | draft_written | 1 | yes | yes | 6866 | 2777 | $0.0415 |
| silver-cleanup-messy-orders | silver-cleanup-proposer | cleanup | draft_written | 2 | no | no | 16985 | 11411 | $0.1481 |
