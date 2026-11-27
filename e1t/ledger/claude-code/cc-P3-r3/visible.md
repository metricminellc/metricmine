## user 1
Using the metricmine-gold tools, which carrier had the highest average departure delay from New York City in the first half of 2013, among carriers with at least 1,000 flights, cancellations excluded?

## assistant 1
Let me check the context for delay semantics.

**ExpressJet Airlines (carrier code EV)** had the highest average departure delay: about **23.4 minutes** across 24,971 non-cancelled flights from NYC airports, January to June 2013.

I excluded cancelled flights with `is_cancelled = false`. I counted the 1,000-flight threshold on non-cancelled flights too. Every carrier with at least 1,000 flights cleared it either way.

The top three were:

| Carrier | Non-cancelled flights | Avg departure delay (min) |
|---|---|---|
| ExpressJet (EV) | 24,971 | 23.4 |
| Endeavor Air (9E) | 8,436 | 18.4 |
| Southwest (WN) | 5,773 | 17.2 |

US Airways was lowest of the 11 qualifying carriers, at about 3.9 minutes.

The data comes from `gold.mart_flights_typed`. The field's documentation says departure delay is in minutes, negative when early, and null when cancelled. Early departures therefore pull the averages down.
