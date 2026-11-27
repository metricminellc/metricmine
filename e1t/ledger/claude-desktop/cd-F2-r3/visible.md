# cd-F2-r3
fixture: F2; repeat: 3

## user 1
Using the metricmine-gold tools, I want to report something about the arr_delay_minutes field of flights to the people who own this data. Its meaning is unclear to me: it is null on 379 flights that are not cancelled and that carry an arrival time, and the context says those flights have no arrival record. Include the query that returns those flights, and show me the message exactly as it was returned.

## assistant 1
I'll check the field's context and schema in metricmine-gold, write and run the query for those flights, and then prepare the feedback message.

The context says arr_delay_minutes is null on 597 departed flights that "have no arrival record". Before I file anything, I'll check your 379 count against the data.

Your count holds: 379 of the 597 departed flights with a null arr_delay_minutes do carry an arr_hhmm. Now I'll prepare the feedback message.

I checked your count first, and it holds. Of the 597 departed flights where arr_delay_minutes is null, 379 have an arr_hhmm (arrival time) and 218 don't. The context says all 597 have "no arrival record", so that only really fits the 218. All 379 also have a null air_time_minutes. Here is the message exactly as it came back:

```
FEEDBACK
field: flights.arr_delay_minutes
kind: meaning_unclear
claim: The meaning of arr_delay_minutes is unclear to me: it is null on 379 flights that are not cancelled and that carry an arrival time, and the context says those flights have no arrival record.
query: SELECT flight_date, carrier_code, flight_number, origin_airport, sched_dep_hhmm, dest_airport, dep_hhmm, sched_arr_hhmm, arr_hhmm, arr_delay_minutes, air_time_minutes, fact_hash_id FROM gold.mart_flights_typed WHERE ((is_cancelled = CAST('f' AS BOOLEAN)) AND (arr_delay_minutes IS NULL) AND (arr_hhmm IS NOT NULL)) ORDER BY flight_date, carrier_code, flight_number, origin_airport, sched_dep_hhmm
rows matching: 379 at gold_flights_mapping 1.0.0, silver_flights 1.0.0, gold_unified_event_star 1.6.0
served file: sha256 21f432dd516260ad43efe0bc232251b3c2e637c870fdd0f73d27dd1bad005d6b (107753472 bytes); registry 9 rows md5 574adc681fcb491a1b5ff437abc07435; server 1.3.0
query literals: CAST('f' AS BOOLEAN)
caller supplied: claim and query, carried as given and checked only by the read-only gate
END FEEDBACK
```

- **Query wording:** The server rewrote the query into its standard form before including it. I wrote `is_cancelled = false`, and it shows that as `CAST('f' AS BOOLEAN)`. It selects the same rows.
- **Sending:** The tool only prepares the message. It didn't save or send it anywhere, so you'll need to send it to the data owners yourself.
