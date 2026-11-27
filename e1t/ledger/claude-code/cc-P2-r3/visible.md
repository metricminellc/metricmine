## user 1
Using the metricmine-gold tools, how many flights went to Palm Beach (PBI), and why do they carry no destination airport name?

## assistant 1
**3,471 flights** went to Palm Beach (PBI). That is about 2.1% of the 166,158 flights in the table. None of them has a destination airport name. The same goes for destination municipality and ISO region, which are also null on all 3,471 rows.

**Why the name is missing:** the flights table takes its airport attributes from the OurAirports reference, which is a 2026 snapshot. The flight data itself is from January to June 2013. The reference now lists Palm Beach International under the code **DJT**, but the 2013 flights still use **PBI**. The join on the destination code therefore finds nothing for PBI, and the destination attributes stay null.

- **Rows kept:** the contract says unresolved references are kept as null attributes and the flight rows are not dropped.
- **Where it shows:** the join documentation says destination attributes resolve for 97.9% of flights (162,687 of 166,158). Every unresolved flight is a PBI flight, and 166,158 − 162,687 = 3,471, which matches my count.
- **Other nulls:** `dest_elevation_ft` and `dest_longest_runway_ft` are also null for PBI, because they come from the same failed join. I only checked name, municipality and region directly.

The table doesn't recode PBI to DJT. If you want PBI's name in a report, you'd need to map it yourself, for example by treating PBI as DJT.

The explanation comes from the contract's authored notes, not from a measurement. The counts above come from the warehouse and agree with it.
