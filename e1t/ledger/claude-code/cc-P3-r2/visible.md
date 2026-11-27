## user 1
Using the metricmine-gold tools, which carrier had the highest average departure delay from New York City in the first half of 2013, among carriers with at least 1,000 flights, cancellations excluded?

## assistant 1
Let me check context for the flights measures before querying.

**ExpressJet Airlines (carrier code EV)** had the highest average departure delay, at about **23.4 minutes** across 24,971 flights.

This covers scheduled departures from NYC (JFK, LGA, EWR) in January through June 2013. Cancelled flights are excluded, and only carriers with at least 1,000 flights are included. The runners-up were:

| Carrier | Flights | Avg departure delay (min) |
|---|---|---|
| ExpressJet (EV) | 24,971 | 23.41 |
| Endeavor Air (9E) | 8,436 | 18.42 |
| Southwest (WN) | 5,773 | 17.16 |
| AirTran (FL) | 1,781 | 15.14 |
| Virgin America (VX) | 2,321 | 14.78 |

The lowest of the 11 qualifying carriers was US Airways, at about 3.9 minutes.

The data is from `gold.mart_flights_typed`. The dataset's documentation says `dep_delay_minutes` is null for cancelled flights. I also filtered on `is_cancelled = false` explicitly.
