## user 1
Using the metricmine-gold tools, I want to tell the people who own this data that I depend on the wind_gust_mph field of airport_weather: my hourly wind report uses it, and relies on a null meaning that no gust was reported. Include the query that returns the hours my report uses, the ones with a reported gust, and show me the message exactly as it was returned.

## assistant 1
Here is the message exactly as returned:

```
FEEDBACK
field: airport_weather.wind_gust_mph
kind: i_depend_on_this
claim: My hourly wind report depends on airport_weather.wind_gust_mph, and it relies on a null meaning that no gust was reported (not zero). The report uses the hours with a reported gust, i.e. where wind_gust_mph is not null.
query: SELECT airport_code, observed_date_local, observed_hour_local, observed_hour_utc, wind_speed_mph, wind_gust_mph FROM gold.mart_airport_weather_typed WHERE (wind_gust_mph IS NOT NULL)
rows matching: 3312 at gold_airport_weather_mapping 1.0.0, silver_airport_weather 1.0.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: none
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

- **Not sent:** The tool only prepares the message. It wrote nothing and sent nothing, so you need to send it to the data owners yourself.
- **Matches the contract:** The field's documented meaning is "null when no gust was reported (not zero)". That is the behavior your report relies on, so the message asks them to keep it.
- **Row count:** 3,312 rows match, which is about a quarter of the 13,014 rows. That fits the documented note that gust is null on about three quarters of rows.
- **Reformatted query:** The gate rewrote the `WHERE` clause with parentheses, `WHERE (wind_gust_mph IS NOT NULL)`. The logic is unchanged.
