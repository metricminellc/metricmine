## user 1
Using the metricmine-gold tools, I want to tell the people who own this data that I depend on the wind_gust_mph field of airport_weather: my hourly wind report uses it, and relies on a null meaning that no gust was reported. Include the query that returns the hours my report uses, the ones with a reported gust, and show me the message exactly as it was returned.

## assistant 1
The message is prepared. It has not been sent. This is exactly what the tool returned:

```
FEEDBACK
field: airport_weather.wind_gust_mph
kind: i_depend_on_this
claim: My hourly wind report depends on wind_gust_mph, and relies on a null meaning that no gust was reported (not zero). The report uses the hours with a reported gust, i.e. wind_gust_mph is not null.
query: SELECT airport_code, observed_date_local, observed_hour_local, observed_hour_utc, wind_speed_mph, wind_gust_mph FROM gold.mart_airport_weather_typed WHERE (wind_gust_mph IS NOT NULL)
rows matching: 3312 at gold_airport_weather_mapping 1.0.0, silver_airport_weather 1.0.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: none
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

- **Rows matching:** 3,312 of the 13,014 airport-hours have a reported gust.
- **Null meaning:** The contract's field meaning says "null when no gust was reported (not zero)". Your reliance on null matches the documented meaning.
- **Wording:** The tool added parentheses around the `WHERE` condition. The query is otherwise as I wrote it.
- **Sending:** The tool only prepares the message. It wrote nothing and sent nothing, so you need to send it to the data owners yourself.
