-- Contracted silver model: silver.silver_nyc_weather.
-- Contract: contracts/silver_nyc_weather.odcs.yaml v1.0.0 (D-06); shape enforced at
-- build time via the hand-authored properties file (rules 3, 4, 11). One
-- typed SELECT over the bronze landing, no rows dropped; the grain
-- (airport_code, observed_hour_utc) is unique by measurement at profile
-- v0001 and enforced by the contract's error-severity grain rule, never a
-- trusted constraint (rule 5). Rendered from the Arc 6 prep's table
-- specification; every column here is declared in the contract.

select
    origin                                                                         as airport_code,
    cast(replace(time_hour, 'Z', '') as timestamp)                                 as observed_hour_utc,
    make_date(cast(year as integer), cast(month as integer), cast(day as integer)) as observed_date_local,
    cast(hour as integer)                                                          as observed_hour_local,
    cast(temp as double)                                                           as temp_f,
    cast(dewp as double)                                                           as dewpoint_f,
    cast(humid as double)                                                          as humidity_pct,
    cast(wind_dir as integer)                                                      as wind_dir_degrees,
    cast(wind_speed as double)                                                     as wind_speed_mph,
    cast(wind_gust as double)                                                      as wind_gust_mph,
    cast(precip as double)                                                         as precip_inches,
    cast(pressure as double)                                                       as pressure_mb,
    cast(visib as double)                                                          as visibility_miles,
    cast(_airbyte_extracted_at as timestamp)                                       as captured_at
from {{ source('bronze', 'nyc_weather') }}
