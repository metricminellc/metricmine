## user 1
Using the metricmine-gold tools, how many flights went to Palm Beach (PBI), and why do they carry no destination airport name?

## assistant 1
**3,471 flights** went to PBI. That is about 2.1% of the 166,158 flights, which are New York City departures from January to June 2013. In the data, all 3,471 have null `dest_airport_name`, `dest_municipality` and `dest_iso_region`.

**Why the name is missing:** the contract documentation explains it. It is authored context, not something I measured, but the counts above are consistent with it.
- The flight records are from 2013. When the table is built, destination attributes are looked up by IATA code in an OurAirports reference that is a 2026 snapshot.
- Palm Beach International flew as **PBI** in 2013. In the 2026 reference it is coded **DJT**, so the lookup on "PBI" finds nothing.
- The pipeline keeps unresolved references as null attributes instead of dropping the rows. That is why the flights are still there, just without destination details.
- The contract's own join check says the destination join resolves for 97.9% of flights (162,687 of 166,158). Every unresolved flight is a PBI flight, so the unresolved count is 3,471, which matches.

If you need names for these flights, you can filter on `dest_airport = 'pbi'` and fill in "Palm Beach International" (Florida, US-FL) yourself. The table has no value for it.
