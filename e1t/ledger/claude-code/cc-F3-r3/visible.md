## user 1
Using the metricmine-gold tools, I want to tell the people who own this data that I depend on the wind_gust_mph field of airport_weather: my hourly wind report uses it, and relies on a null meaning that no gust was reported. Include the query that returns the hours my report uses, the ones with a reported gust, and show me the message exactly as it was returned.

## assistant 1
Let me read the measures context to understand how nulls in wind_gust_mph are documented.

The message was prepared. It has not been sent, because the tool only writes the text and you send it. This is the message exactly as returned:

```
FEEDBACK
field: airport_weather.wind_gust_mph
kind: i_depend_on_this
claim: My hourly wind report depends on wind_gust_mph. It relies on a null meaning that no gust was reported (not zero), as documented in the field's meaning. The report uses the hours that have a reported gust (wind_gust_mph is not null). Please tell me before changing the meaning, type, units, or null semantics of this field.
query: SELECT airport_code, observed_date_local, observed_hour_local, observed_hour_utc, wind_speed_mph, wind_gust_mph FROM gold.mart_airport_weather_typed WHERE (wind_gust_mph IS NOT NULL)
rows matching: 3312 at gold_airport_weather_mapping 1.0.0, silver_airport_weather 1.0.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: none
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

- **Rows matching:** 3,312 airport-hours have a reported gust. That is about a quarter of the 13,014 rows, which fits the contract's note that gust is null on about three quarters of rows.
- **Null meaning:** The field's documented meaning is "null when no gust was reported (not zero)". That is the behaviour your report relies on, and the claim says so.
- **Wording:** I wrote the claim and the query myself. The tool carries them as given. It only checked that the query is a read-only SELECT. I picked the columns in the query (airport, local date and hour, UTC hour, wind speed and gust) as a guess at what an hourly wind report needs. Tell me if your report uses different ones and I'll prepare it again.
