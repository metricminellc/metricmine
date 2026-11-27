# cd-F3-r2
fixture: F3; repeat: 2

## user 1
Using the metricmine-gold tools, I want to tell the people who own this data that I depend on the wind_gust_mph field of airport_weather: my hourly wind report uses it, and relies on a null meaning that no gust was reported. Include the query that returns the hours my report uses, the ones with a reported gust, and show me the message exactly as it was returned.

## assistant 1
I'll check the airport_weather schema, write and run the query for hours with a reported gust, and then prepare the feedback message for the data owners.

The message is ready. Here it is exactly as the tool returned it:

```
FEEDBACK
field: airport_weather.wind_gust_mph
kind: i_depend_on_this
claim: I depend on the wind_gust_mph field of airport_weather: my hourly wind report uses it, and relies on a null meaning that no gust was reported.
query: SELECT airport_code, observed_hour_utc, observed_date_local, observed_hour_local, wind_speed_mph, wind_gust_mph FROM gold.mart_airport_weather_typed WHERE (wind_gust_mph IS NOT NULL) ORDER BY airport_code, observed_hour_utc
rows matching: 3312 at gold_airport_weather_mapping 1.0.0, silver_airport_weather 1.0.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: none
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

The tool didn't send or save it anywhere, so you'll need to send it to the data owners yourself.

Your assumption about nulls is correct today:
- **What the contract says:** the field's meaning is "null when no gust was reported (not zero)."
- **What the data shows:** I counted all 13,014 rows. 3,312 have a gust, from 16.1 to 62.1 mph. The other 9,702 are null, and none are zero.

The owners' notes say the null means no gust was reported, but they also list 12 airport-hours with no observation at all. Those hours have no row in the table, so they won't show up as nulls in your report. If the report expects a row for every airport and hour, treat those as missing data, not calm hours.
