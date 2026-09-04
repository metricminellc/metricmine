-- Contracted silver model: silver.silver_nyc_airlines.
-- Contract: contracts/silver_nyc_airlines.odcs.yaml v1.0.0 (D-06); shape enforced at
-- build time via the hand-authored properties file (rules 3, 4, 11). One
-- typed SELECT over the bronze landing, no rows dropped; the grain
-- (carrier_code) is unique by measurement at profile
-- v0001 and enforced by the contract's error-severity grain rule, never a
-- trusted constraint (rule 5). Rendered from the Arc 6 prep's table
-- specification; every column here is declared in the contract.

select
    carrier                                  as carrier_code,
    name                                     as carrier_name,
    cast(_airbyte_extracted_at as timestamp) as captured_at
from {{ source('bronze', 'nyc_airlines') }}
