-- Contracted silver model: silver.silver_nyc_flights.
-- Contract: contracts/silver_nyc_flights.odcs.yaml v1.0.0 (D-06); shape enforced at
-- build time via the hand-authored properties file (rules 3, 4, 11). One
-- typed SELECT over the bronze landing, no rows dropped; the grain
-- (flight_date, carrier_code, flight_number, origin_airport, sched_dep_hhmm) is unique by measurement at profile
-- v0001 and enforced by the contract's error-severity grain rule, never a
-- trusted constraint (rule 5). Rendered from the Arc 6 prep's table
-- specification; every column here is declared in the contract.

select
    make_date(cast(year as integer), cast(month as integer), cast(day as integer)) as flight_date,
    carrier                                                                        as carrier_code,
    cast(flight as integer)                                                        as flight_number,
    origin                                                                         as origin_airport,
    cast(sched_dep_time as integer)                                                as sched_dep_hhmm,
    dest                                                                           as dest_airport,
    tailnum                                                                        as tail_number,
    dep_time is null                                                               as is_cancelled,
    cast(dep_time as integer)                                                      as dep_hhmm,
    cast(dep_delay as integer)                                                     as dep_delay_minutes,
    cast(arr_time as integer)                                                      as arr_hhmm,
    cast(sched_arr_time as integer)                                                as sched_arr_hhmm,
    cast(arr_delay as integer)                                                     as arr_delay_minutes,
    cast(air_time as integer)                                                      as air_time_minutes,
    cast(distance as integer)                                                      as distance_miles,
    cast(hour as integer)                                                          as sched_dep_hour_local,
    cast(minute as integer)                                                        as sched_dep_minute_local,
    cast(replace(time_hour, 'Z', '') as timestamp)                                 as departure_hour_utc,
    cast(_airbyte_extracted_at as timestamp)                                       as captured_at
from {{ source('bronze', 'nyc_flights') }}
