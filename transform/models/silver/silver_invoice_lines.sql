-- Contracted silver model: silver.silver_invoice_lines.
-- Contract: contracts/silver_invoice_lines.odcs.yaml v1.1.0 (D-06); shape
-- enforced at build time via the hand-authored properties file (rules 3, 4,
-- 11). Dedup: one GROUP BY over every business column except the timestamp
-- collapses exact duplicate captures (506 rows at v0001) and within-invoice
-- clock-drift re-scans (1 pair at v0001, invoice 492807) in a single pass;
-- the earliest scan tick is retained via min(invoiced_at). Grain
-- (invoice_id, stock_code, quantity, unit_price) is unique by measurement at
-- v0001 and enforced by the contract's error-severity grain rule, never a
-- trusted constraint (rule 5).

with cleaned as (

    select
        invoice                        as invoice_id,
        invoice like 'C%'              as is_cancellation,
        stockcode                      as stock_code,
        trim(description)              as product_description,
        cast(quantity as integer)      as quantity,
        cast(invoicedate as timestamp) as invoiced_at,
        cast(price as decimal(10, 2))  as unit_price,
        cast(customer_id as integer)   as customer_id,
        country
    from {{ source('bronze', 'online_retail_ii') }}

)

select
    invoice_id,
    is_cancellation,
    stock_code,
    product_description,
    quantity,
    min(invoiced_at) as invoiced_at,
    unit_price,
    customer_id,
    country
from cleaned
group by
    invoice_id,
    is_cancellation,
    stock_code,
    product_description,
    quantity,
    unit_price,
    customer_id,
    country
