-- Contracted silver model: silver.silver_ourairports_runways.
-- Contract: contracts/silver_ourairports_runways.odcs.yaml v1.0.0 (D-06); shape enforced at
-- build time via the hand-authored properties file (rules 3, 4, 11). One
-- typed SELECT over the bronze landing, no rows dropped; the grain
-- (runway_id) is unique by measurement at profile
-- v0001 and enforced by the contract's error-severity grain rule, never a
-- trusted constraint (rule 5). Rendered from the Arc 6 prep's table
-- specification; every column here is declared in the contract.

select
    id                                       as runway_id,
    airport_ident                            as airport_ident,
    nullif(cast(length_ft as integer), 0)    as length_ft,
    cast(width_ft as integer)                as width_ft,
    surface                                  as surface,
    cast(lighted as integer) = 1             as is_lighted,
    cast(closed as integer) = 1              as is_closed,
    le_ident                                 as low_end_ident,
    he_ident                                 as high_end_ident,
    cast(_airbyte_extracted_at as timestamp) as captured_at
from {{ source('bronze', 'ourairports_runways') }}
