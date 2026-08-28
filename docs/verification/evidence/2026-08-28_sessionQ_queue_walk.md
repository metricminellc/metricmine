# Session Q recorded driver walk (D-35): one call off the derived queue

Environment: the Mac, the adoption fixture staged, one live describe call driven by make propose-queue MAX=1 in Shell B; fully reverted after recording.

[0m14:44:08  Done. PASS=1 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=1
wrote profiles/bronze.online_retail_ii/v0002.json (sha256:96360e9648c7cce05ad0be51940f126a9e10e18ac1812da3486bbf7822e2865d)
unchanged: profiles/silver.silver_invoice_lines already holds sha256:e65bee8117b65958b8c4741b43509ece19a581dd1d6bad9a7e1da9b67b0b5fcd
wrote profiles/silver.silver_country_daily_sales/v0001.json (sha256:0c1b052ccbd9ca0fb776b2c9de6c3c4f7251b0d64c5ab7c8bcd2b865e576bcbf)
## The queue

1. **`silver_country_daily_sales`**: `adopt`  
   why: relation and profile present, no contract governs it.  
   next: `make propose-describe TABLE=silver_country_daily_sales  &&  make verify-grain TABLE=silver_country_daily_sales KEYS=...`

uv run python -m metricmine.adoption verify-grain --table "silver_country_daily_sales" --keys "country,sales_date"
duplicate rows over ['country', 'sales_date']: 0
duplicate rows over ['country']: 63
duplicate rows over ['sales_date']: 64
verify-grain: PASS (silver.silver_country_daily_sales is unique over (country, sales_date))

## The driver walk
uv run python -m metricmine.agents propose-queue --max "1" --intent "" 
queue: 1 item(s); driven states: 1
item 1/1: silver_country_daily_sales (adopt -> describe stance)
  draft: proposals/silver-cleanup-proposer/20260828T144715247852Z_0c1b052c/draft.odcs.yaml
  tokens in 6899, out 4684; cost ~$0.0606; attempts 1
walked 1 item(s); tokens in 6899, out 4684; total cost ~$0.0606
review each draft in the editor; approval stays one contract per PR (D-24: merge is approval).
