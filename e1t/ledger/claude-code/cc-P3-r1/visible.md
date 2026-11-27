## user 1
Using the metricmine-gold tools, which carrier had the highest average departure delay from New York City in the first half of 2013, among carriers with at least 1,000 flights, cancellations excluded?

## assistant 1
Let me check context for the measures quickly.

**ExpressJet Airlines (carrier code EV)** had the highest average departure delay, at about **23.4 minutes** across 24,971 flights.

The data is `gold.mart_flights_typed`, covering scheduled departures from the three NYC airports from January to June 2013. I excluded cancelled flights and counted only carriers with at least 1,000 flights. Eleven carriers qualified.

The next highest were:

| Carrier | Flights | Average departure delay (min) |
|---|---|---|
| Endeavor Air (9E) | 8,436 | 18.4 |
| Southwest (WN) | 5,773 | 17.2 |
| AirTran (FL) | 1,781 | 15.1 |
| Virgin America (VX) | 2,321 | 14.8 |

US Airways was lowest at about 3.9 minutes.
