-- Contracted silver model: silver.silver_ourairports_airports.
-- Contract: contracts/silver_ourairports_airports.odcs.yaml v1.0.0 (D-06); shape enforced at
-- build time via the hand-authored properties file (rules 3, 4, 11). One
-- typed SELECT over the bronze landing, no rows dropped; the grain
-- (iata_code) is unique by measurement at profile
-- v0001 and enforced by the contract's error-severity grain rule, never a
-- trusted constraint (rule 5). Rendered from the Arc 6 prep's table
-- specification; every column here is declared in the contract.

select
    iata_code                                as iata_code,
    ident                                    as airport_ident,
    type                                     as airport_type,
    name                                     as airport_name,
    cast(latitude_deg as double)             as latitude_deg,
    cast(longitude_deg as double)            as longitude_deg,
    cast(elevation_ft as integer)            as elevation_ft,
    continent                                as continent_code,
    iso_country                              as iso_country,
    iso_region                               as iso_region,
    municipality                             as municipality,
    scheduled_service = 'yes'                as has_scheduled_service,
    icao_code                                as icao_code,
    gps_code                                 as gps_code,
    local_code                               as local_code,
    wikipedia_link                           as wikipedia_link,
    keywords                                 as keywords,
    cast(_airbyte_extracted_at as timestamp) as captured_at
from {{ source('bronze', 'ourairports_airports') }}
