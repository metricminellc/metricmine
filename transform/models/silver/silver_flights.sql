-- Unified silver model: silver.silver_flights (the conformance table of the
-- flights category, D-41). Contract: contracts/silver_flights.odcs.yaml
-- v1.0.0. Human-owned SQL by design: every join here is declared in the
-- contract with the key it uses and the completeness floor it meets, and
-- the gold star maps this table as one category rather than joining in
-- gold. One row per flight (the silver_nyc_flights grain, 1:1 by
-- construction: every join is to a unique key or to a one-row-per-airport
-- aggregate). Reference attributes are null where the reference does not
-- know the entity (the PBI to DJT recoding; fleet numbers in place of tail
-- numbers), never dropped rows.

with longest_runway as (

    select
        airport_ident,
        max(length_ft) as longest_runway_ft
    from {{ ref('silver_ourairports_runways') }}
    where not is_closed and length_ft is not null
    group by airport_ident

),

airports as (

    select
        a.iata_code,
        a.airport_name,
        a.municipality,
        a.iso_region,
        a.elevation_ft,
        r.longest_runway_ft
    from {{ ref('silver_ourairports_airports') }} a
    left join longest_runway r on r.airport_ident = a.airport_ident

)

select
    f.flight_date,
    f.carrier_code,
    f.flight_number,
    f.origin_airport,
    f.sched_dep_hhmm,
    f.dest_airport,
    f.tail_number,
    f.is_cancelled,
    f.dep_hhmm,
    f.dep_delay_minutes,
    f.arr_hhmm,
    f.sched_arr_hhmm,
    f.arr_delay_minutes,
    f.air_time_minutes,
    f.distance_miles,
    f.sched_dep_hour_local,
    f.sched_dep_minute_local,
    f.departure_hour_utc,
    al.carrier_name,
    p.manufacturer            as aircraft_manufacturer,
    p.model                   as aircraft_model,
    p.manufacture_year        as aircraft_manufacture_year,
    p.seat_count              as aircraft_seat_count,
    p.engine_type             as aircraft_engine_type,
    o.airport_name            as origin_airport_name,
    o.municipality            as origin_municipality,
    o.elevation_ft            as origin_elevation_ft,
    o.longest_runway_ft       as origin_longest_runway_ft,
    d.airport_name            as dest_airport_name,
    d.municipality            as dest_municipality,
    d.iso_region              as dest_iso_region,
    d.elevation_ft            as dest_elevation_ft,
    d.longest_runway_ft       as dest_longest_runway_ft,
    f.captured_at
from {{ ref('silver_nyc_flights') }} f
left join {{ ref('silver_nyc_airlines') }} al on al.carrier_code = f.carrier_code
left join {{ ref('silver_nyc_planes') }} p on p.tail_number = f.tail_number
left join airports o on o.iata_code = f.origin_airport
left join airports d on d.iata_code = f.dest_airport
