# cd-F3-r3
fixture: F3; repeat: 3

## user 1
Using the metricmine-gold tools, I want to tell the people who own this data that I depend on the wind_gust_mph field of airport_weather: my hourly wind report uses it, and relies on a null meaning that no gust was reported. Include the query that returns the hours my report uses, the ones with a reported gust, and show me the message exactly as it was returned.

## assistant 1
I'll pull the airport_weather schema, check the gust query against the gold data, and then prepare the dependency message for the data owners.

The contract's expert context says gust is "null when no gust was reported (not zero)." That matches your dependency. Next I'll check the data against that claim before drafting.

The data agrees: 3,312 hours carry a reported gust, 9,702 are null, and none are zero. Preparing the message now.

I've prepared the message. Here it is exactly as the tool returned it:

```
FEEDBACK
field: airport_weather.wind_gust_mph
kind: i_depend_on_this
claim: I depend on the wind_gust_mph field of airport_weather. My hourly wind report uses it, and relies on a null meaning that no gust was reported.
query: SELECT airport_code, observed_hour_utc, observed_date_local, observed_hour_local, wind_speed_mph, wind_gust_mph FROM gold.mart_airport_weather_typed WHERE (wind_gust_mph IS NOT NULL) ORDER BY airport_code, observed_hour_utc
rows matching: 3312 at gold_airport_weather_mapping 1.0.0, silver_airport_weather 1.0.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: none
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

The tool didn't send it or save it anywhere. You'll need to send it to the data owners yourself.

- **The query:** the tool reformatted my WHERE clause slightly by adding parentheses (`WHERE (wind_gust_mph IS NOT NULL)`). It returns the same rows.
- **Your assumption matches the contract:** the field definition says gust is "null when no gust was reported (not zero)."
- **The data matches too:** of 13,014 airport-hours, 3,312 have a reported gust and 9,702 are null. None are zero. Reported gusts run from about 16 to 62 mph, and none is below the sustained wind speed for its hour. So right now, nothing in the data uses a zero or other placeholder to mean "no gust."
- **A gap to know about:** 12 airport-hours (4 per airport) have no row at all. If your report lists every hour in the window, treat those as a separate case. They are missing observations, not "no gust" hours, so they shouldn't count as calm.
