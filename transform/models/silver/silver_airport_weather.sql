-- Unified silver model: silver.silver_airport_weather (the conformance table
-- of the airport_weather category, D-41). Contract:
-- contracts/silver_airport_weather.odcs.yaml v1.0.0. Human-owned SQL by
-- design: the hourly observation joined to its airport's 2026 reference
-- attributes on the conformed airport code. One row per airport per hour
-- (the silver_nyc_weather grain, 1:1 by construction).

with longest_runway as (

    select
        airport_ident,
        max(length_ft) as longest_runway_ft
    from {{ ref('silver_ourairports_runways') }}
    where not is_closed and length_ft is not null
    group by airport_ident

)

select
    w.airport_code,
    w.observed_hour_utc,
    w.observed_date_local,
    w.observed_hour_local,
    w.temp_f,
    w.dewpoint_f,
    w.humidity_pct,
    w.wind_dir_degrees,
    w.wind_speed_mph,
    w.wind_gust_mph,
    w.precip_inches,
    w.pressure_mb,
    w.visibility_miles,
    a.airport_name,
    a.municipality        as airport_municipality,
    a.elevation_ft        as airport_elevation_ft,
    r.longest_runway_ft   as airport_longest_runway_ft,
    w.captured_at
from {{ ref('silver_nyc_weather') }} w
left join {{ ref('silver_ourairports_airports') }} a on a.iata_code = w.airport_code
left join longest_runway r on r.airport_ident = a.airport_ident
