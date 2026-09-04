-- Contracted silver model: silver.silver_nyc_planes.
-- Contract: contracts/silver_nyc_planes.odcs.yaml v1.0.0 (D-06); shape enforced at
-- build time via the hand-authored properties file (rules 3, 4, 11). One
-- typed SELECT over the bronze landing, no rows dropped; the grain
-- (tail_number) is unique by measurement at profile
-- v0001 and enforced by the contract's error-severity grain rule, never a
-- trusted constraint (rule 5). Rendered from the Arc 6 prep's table
-- specification; every column here is declared in the contract.

select
    tailnum                                  as tail_number,
    cast(year as integer)                    as manufacture_year,
    type                                     as aircraft_type,
    manufacturer                             as manufacturer,
    model                                    as model,
    cast(engines as integer)                 as engine_count,
    cast(seats as integer)                   as seat_count,
    cast(speed as integer)                   as cruise_speed_mph,
    engine                                   as engine_type,
    cast(_airbyte_extracted_at as timestamp) as captured_at
from {{ source('bronze', 'nyc_planes') }}
