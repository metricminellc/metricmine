# cd-F3-r1
fixture: F3; repeat: 1

## user 1
Using the metricmine-gold tools, I want to tell the people who own this data that I depend on the wind_gust_mph field of airport_weather: my hourly wind report uses it, and relies on a null meaning that no gust was reported. Include the query that returns the hours my report uses, the ones with a reported gust, and show me the message exactly as it was returned.

## assistant 1
I'll look up the airport_weather schema, check the query that returns your report's hours, then prepare the feedback message.

The contract's expert context matches your reading: gust is null when no gust was reported, not zero. Preparing the message now.

The message is ready. Nothing has been sent, so you'll need to pass it to the data owners yourself. Here it is exactly as the tool returned it:

```
FEEDBACK
field: airport_weather.wind_gust_mph
kind: i_depend_on_this
claim: My hourly wind report uses wind_gust_mph, and relies on a null meaning that no gust was reported.
query: SELECT airport_code, observed_hour_utc, wind_gust_mph FROM gold.mart_airport_weather_typed WHERE (wind_gust_mph IS NOT NULL) ORDER BY airport_code, observed_hour_utc
rows matching: 3312 at gold_airport_weather_mapping 1.0.0, silver_airport_weather 1.0.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: none
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

- **The query was slightly reformatted.** The server put parentheses around the WHERE condition. It works the same as the query I sent.
- **The data owners already define the field your way.** Their notes on the field say it is "null when no gust was reported (not zero)." Filing this as `i_depend_on_this` puts on record that your report relies on that meaning. If they change it, they'll know your report is affected.
- **The count fits their notes.** 3,312 of the 13,014 airport-hours have a reported gust. That leaves about 75% null, which matches their note that gust is null on three quarters of rows.
