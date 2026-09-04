# Sources: what the star is built from, and how each is pinned

> Repo path: `docs/sources.md`
> Governing decisions: [D-15](decisions/decision-register.md#d-15) as
> amended by Amendment T (committed samples, plural, each pinned to a
> commit and a digest), [D-41](decisions/decision-register.md#d-41) (the
> multi-source proof: co-location in gold, conformance in silver,
> service through typed surfaces).

Every table the pipeline lands is a committed extract of a public
dataset, cut by a fetch script that refuses to run on raw bytes with any
digest but the recorded one, serialized deterministically, and
documented in a README beside it. `tests/test_committed_samples.py`
holds each extract to its README (row count, digest, the pinned
source), and `make ingest` lands them keyless through the one PyAirbyte
file connector type (D-41: many files of that type are in scope, one
connector type is). Nothing here is fetched at build time.

## The seven extracts

| Extract | Publisher and license | Pinned source | Window | Rows | Extract sha256 |
|---|---|---|---|---|---|
| `online_retail_ii/online_retail_ii_2009-12.csv` | Online Retail II, UCI Machine Learning Repository (Chen, 2012); CC BY 4.0 | the UCI archive workbook, sheet "Year 2009-2010" | December 2009 | 45,228 | `81cde970…a71a1c` |
| `nyc_flights/nyc_flights_2013-01_2013-06.csv` | nycflights13 `flights` (Wickham; Posit); CC0 | tidyverse/nycflights13 at `df98ef21`, `data/flights.rda` | January to June 2013 | 166,158 | `ea3bce0b…7bef18` |
| `nyc_weather/nyc_weather_2013-01_2013-06.csv` | nycflights13 `weather` (ASOS via Iowa Environmental Mesonet); CC0 | tidyverse/nycflights13 at `df98ef21`, `data-raw/weather.csv` | January to June 2013 | 13,014 | `4092d00f…42fe77` |
| `nyc_airlines/nyc_airlines_df98ef215aa8.csv` | nycflights13 `airlines` (BTS carrier codes); CC0 | tidyverse/nycflights13 at `df98ef21`, `data-raw/airlines.csv` | whole table | 16 | `162551bd…c10609` |
| `nyc_planes/nyc_planes_df98ef215aa8.csv` | nycflights13 `planes` (FAA registry, 2014 release); CC0 | tidyverse/nycflights13 at `df98ef21`, `data-raw/planes.csv` | whole table | 3,322 | `778962ed…d04c1a` |
| `ourairports_airports/ourairports_airports_d27027ba4414.csv` | OurAirports `airports.csv`; public domain | davidmegginson/ourairports-data at `d27027ba` | airports with an IATA code | 9,057 | `34bbc671…8b3f91` |
| `ourairports_runways/ourairports_runways_d27027ba4414.csv` | OurAirports `runways.csv`; public domain | davidmegginson/ourairports-data at `d27027ba` | runways of those airports | 10,760 | `de597055…dfd52b` |

Full digests, raw-file digests, retrieval dates, serialization rules,
and the regenerate command live in each extract's README under
`data/samples/`. The budgets Amendment T sets (20 MB per event extract,
10 MB per other extract, 40 MB per arc) are enforced by
`tests/test_ingest_config.py` and `tests/test_committed_samples.py`.

## How the extracts become the star

Each extract lands as one bronze table, is settled by one hand-owned
silver contract and model (the cleanup plane), and the aviation family
is then unified in silver into two tables whose contracts declare
their joins with measured completeness:

| Category | Unified silver table | Built from | Declared joins (measured completeness, floor) |
|---|---|---|---|
| `invoice_lines` | `silver_invoice_lines` | `online_retail_ii` | none (one source) |
| `flights` | `silver_flights` | `silver_nyc_flights` + `silver_nyc_airlines` + `silver_nyc_planes` + `silver_ourairports_airports` + `silver_ourairports_runways` | carrier 1.0000 (1.00); aircraft 0.8396 (0.80); origin 1.0000 (1.00); destination 0.9791 (0.97) |
| `airport_weather` | `silver_airport_weather` | `silver_nyc_weather` + `silver_ourairports_airports` + `silver_ourairports_runways` | airport 1.0000 (1.00) |

Conformance is settled in silver and declared at the contract plane
(D-41): each silver contract that carries a conformed key names it
(`conformedKeys`), the star contract declares the normalization rule
per key (`conformedKeyRules`: `airport_iata`, `carrier_code`,
`tail_number`), and the K1 gate (`tests/test_conformed_keys.py`) holds
the two to each other. The star then co-locates the categories under
one conformed calendar, and the cross-category join the star declares
(`crossCategoryJoins`: flights to the weather at their origin airport
in their departure hour, measured 0.9994 over the typed surfaces, floor
0.99) is held to the warehouse by `tests/test_declared_joins.py`.

## Vintage, and what it does to the joins

The event tables are 2013; the airport reference is a 2026 snapshot;
the aircraft registry is the 2014 FAA release the package shipped. The
contracts say so, and the effects are measured rather than smoothed
over:

- Palm Beach International flew as `PBI` in 2013 and is coded `DJT` in
  the 2026 reference (its identifier `KPBI` and keywords still carry
  `PBI`). The 3,471 flights to PBI (2.1 percent) resolve no destination
  attributes; the contract does not apply the free-text keywords as a
  crosswalk. This is the vintage effect the demo shows on purpose.
- American Airlines and Envoy Air reported fleet numbers rather than
  registrations in 2013, and 1,521 flights carry no tail number, so
  about 16 percent of flights resolve no aircraft.
- Twelve airport-hours between the first and last observation have no
  weather row, so 97 flights find no weather at their origin in their
  departure hour.
- Carrier names are as BTS published them in 2013; several carriers
  have merged or renamed since.

`tests/test_aviation_conservation.py` pins these counts, the row
conservation through every plane, and the clock and calendar
arithmetic the contracts describe.

## Where the expert context comes from

Everything a serving agent reads under `expert_context` (Amendment W)
is authored in these contracts: the silver contract's purpose, usage,
and limitations; its `sourceLineage`, `vintage`, and structured
`joins`; the mapping contract's purpose and usage; the decision record
on both; and the star's `crossCategoryJoins`. The context compiler
carries them into the registry unchanged and keeps them apart, by
name, from the typed declarations (`data`). Change the knowledge by
amending the contract; the registry follows at the next `make context`.

## The reasoning, and adding a source of your own

This page is the register. The reasoning behind every decision the
extracts took, every join and its justification, and how to read them
as a pattern for your own data is
[docs/sources-explained.md](sources-explained.md). Every extract above
went through the same steps, and so can yours:
[docs/adding-a-source.md](adding-a-source.md) walks them with a source
that is not in the demo (the World Bank GDP series), measured end to
end in a fresh clone of v1.1.0.
