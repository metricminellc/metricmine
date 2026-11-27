## user 1
Using the metricmine-gold tools, how many flights went to Palm Beach (PBI), and why do they carry no destination airport name?

## assistant 1
**3,471 flights** went to PBI in the data. They span 2013-01-01 to 2013-06-30 and make up about 2.1% of the 166,158 flights. Every one of them has a null `dest_airport_name`. The same is true of `dest_municipality`, `dest_elevation_ft`, `dest_iso_region` and `dest_longest_runway_ft`. I measured the count and the nulls directly in `gold.mart_flights_typed`.

**Why the name is missing:** the airport names come from a 2026 OurAirports reference snapshot, but the flights are from 2013. According to the contract's authored notes, Palm Beach International flew as PBI in 2013, and the 2026 reference lists it under the code **DJT**. The join on `dest_airport = iata_code` therefore finds no match for PBI. By design, unresolved references stay on the row as nulls instead of the row being dropped, so the flights are all still counted.

The contract also says that PBI accounts for every destination that failed to resolve. 162,687 of 166,158 flights resolve (97.9%), and the 3,471 that don't are exactly the PBI flights. That matches the count I got.

To get Palm Beach's attributes you would have to map PBI to DJT by hand. That mapping is not in the gold layer.
