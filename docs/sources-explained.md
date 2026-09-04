# The demo sources, explained

> Repo path: `docs/sources-explained.md`
> Companion to [docs/sources.md](sources.md) (the register: pins,
> licenses, digests) and [docs/adding-a-source.md](adding-a-source.md)
> (the procedure). This page is the reasoning: what each source is, why
> it is in the demo, what was decided about it and why, every join and
> its justification, how each source moved through the system, and how
> to read all of it as a pattern for your own data. Governing decisions:
> [D-15](decisions/decision-register.md#d-15) (committed samples),
> [D-41](decisions/decision-register.md#d-41) (the multi-source proof),
> [D-17](decisions/decision-register.md#d-17) (the star and its
> calendar), [D-30](decisions/decision-register.md#d-30) and
> [D-31](decisions/decision-register.md#d-31) (the registry and what it
> serves).

The data here is for demonstration. None of it is the point. The point
is what was done to it, why, and where each decision lives, because
those are the parts that carry over to a warehouse of your own.

## 1. Why these sources

The demo needed a set of public sources that would exercise the
problems a real multi-source warehouse meets, at a size that builds on
a laptop, under licenses that allow redistribution, pinned so that the
same commit builds the same star on any machine. The choice fell on two
families:

- The retail sample (Online Retail II, December 2009), the first source
  the pipeline ever landed, kept as the category that shares nothing
  with the others: no common key, no overlapping time. It proves that
  the star co-locates unrelated sources without pretending they relate.
- The aviation family (nycflights13 flights, hourly weather, carriers,
  and aircraft for New York City's three airports in the first half of
  2013; OurAirports airports and runways as a 2026 reference), chosen
  because it carries, in miniature, the situations that make
  multi-source work hard: an event table with cancellations and local
  clock times; a lookup whose names have aged; a registry that does not
  know some of the entities; a reference snapshot newer than the
  events, so a code has moved; hourly observations with gaps and
  reported-only-when-present measurements; and two tables that must
  meet on a shared calendar.

Every extract is public, cited, licensed for redistribution (CC0,
public domain, CC BY 4.0), fetched by a script pinned to a commit and a
raw digest, and held to its README by a gate. The register in
[docs/sources.md](sources.md) has the pins.

## 2. The family at a glance

| Source | What it is | Grain | Rows | Role in the star | What it teaches |
|---|---|---|---|---|---|
| `online_retail_ii` | Invoice lines of a UK online retailer, December 2009 | one invoice line | 45,228 in, 44,721 out | the `invoice_lines` category, alone | duplicates as capture artifacts; cancellations retained and flagged; a category with no relations |
| `nyc_flights` | Every scheduled departure from EWR, JFK, LGA, January to June 2013 | one scheduled departure | 166,158 | the event rows of the `flights` category | cancellations as nulls; local clocks and a UTC key; a half-year window |
| `nyc_weather` | Hourly ASOS observations at the three airports | one airport-hour | 13,014 | the event rows of the `airport_weather` category | gaps in a series; measurements that are null when not reported; units in names |
| `nyc_airlines` | The carrier code lookup | one carrier code | 16 | carrier names on `flights` | a lookup whose names have aged |
| `nyc_planes` | FAA registry rows for the tail numbers seen | one tail number | 3,322 | aircraft attributes on `flights` | a registry that does not know some entities |
| `ourairports_airports` | Every airport with an IATA code, 2026 | one airport | 9,057 | airport attributes on both aviation categories | a reference newer than the events; a code that moved |
| `ourairports_runways` | The runways of those airports, 2026 | one runway | 10,760 | one derived attribute per airport (the longest open runway) | an aggregate derived from a many-to-one reference |

Three categories reach the star: `invoice_lines` from the retail table
alone, `flights` from the five aviation tables unified in
`silver_flights`, and `airport_weather` from the weather and reference
tables unified in `silver_airport_weather`. Nothing else becomes a
gold object: no shared dimension, no hand-written mart.

## 3. Each source, from bytes to contract

Every source moved through the same four stations. The bytes land in
bronze exactly as published (the connector renames nothing and casts
nothing beyond its own inference). The profiler measures the landed
table into a committed artifact (null rates, distinct counts, ranges,
samples, a content hash). A person writes the cleanup contract from the
profile, and every judgment is a `decision*` property in that contract.
A hand-written SQL model realizes the contract, and the gates hold the
model to it at every build. What follows is what each source needed at
each station.

### 3.1 The retail sample (`online_retail_ii`, the `invoice_lines` category)

The oldest source and the simplest shape: one row per invoice line
with an invoice id, a stock code, a description, a quantity, a
timestamp, a unit price, a customer id, and a country.

What the profile showed: 1.1 percent of rows were exact duplicates;
one pair of rows differed only by one minute of timestamp; the
customer id was null on 29.8 percent of rows; invoice ids with a C
prefix carried negative quantities; some lines carried a zero price.

What the contract decided, and why. Exact duplicates are capture
artifacts and are excluded (the source is a register feed, and two
identical lines within one capture are the same line seen twice; the
contract says so and accepts that a legitimate identical re-scan is
indistinguishable and also excluded). The one-minute pair is a register
clock tick and collapses to the earlier timestamp. Cancellations are
retained and flagged (`is_cancellation`), never dropped, so the
arithmetic against bronze stays auditable and exclusion is the
consumer's decision at query time. Null customer ids are retained as
null (guest checkouts are sales). Zero-price lines are retained (they
are adjustments, not errors). The timestamp is cast strictly (a string
that does not parse fails the build rather than becoming null). The
grain is declared as the tuple that is unique after the exclusion and
enforced by an error-severity rule. The version history shows the
discipline: 1.2.0 declared `captured_at` optional because the model had
not populated it yet, and 1.3.0 tightened it to required once the
profile measured a zero null rate, through the amend stance.

Where it lands: 44,721 rows in `silver_invoice_lines`, mapped as the
`invoice_lines` category at minute grain with six dimensions (invoice
id, cancellation flag, stock code, description, customer id, country)
and two measures (quantity, unit price).

### 3.2 Flights (`nyc_flights`, the event rows of the `flights` category)

What it is: every scheduled departure from Newark, Kennedy, and
LaGuardia from January 1 to June 30, 2013, as the Bureau of
Transportation Statistics published it and the nycflights13 package
repackaged it: date parts, carrier, flight number, tail number, origin,
destination, scheduled and actual clock times as local HHMM integers,
delays in minutes, air time, distance, and `time_hour`, the scheduled
departure hour as a UTC instant.

How it landed: the code columns (carrier, tail number, origin,
destination, the hour string) are pinned to text at the reader so that
inference cannot turn a code into a number or a date.

What the profile showed: 166,158 rows and 166,158 distinct (date,
carrier, flight number, origin, scheduled time) tuples; `dep_time` null
on 4,883 rows; `arr_time` and `air_time` null on 5,480; `tailnum` null
on 1,521.

What the contract decided, and why. The grain is the five-column tuple
the publisher's own fields imply, declared as the primary key set and
enforced by the grain rule. A cancelled flight is a flight whose actual
departure time is null: `is_cancelled` is derived from exactly that,
and the contract states the consequence a consumer needs, that the
departure delay is null on exactly those 4,883 flights, so an average
of delays excludes cancellations by construction and a cancellation
rate must be counted from the flag, never from a null. Arrival delay
and air time are null on 597 more flights that departed and have no
arrival record (diverted or unreported); the contract says so because
an analyst who averages arrival delays needs to know the denominator.
Clock times stay as the published local HHMM integers, because they are
how the industry reads a schedule (517 is 05:17), and the UTC hour is
the join key, because a calendar shared across sources has to be in
one time base. No rows are dropped. Every null the profile measured has
a sentence in the usage text.

What the model does: casts, the `is_cancelled` derivation, a
`flight_date` from the date parts, and `departure_hour_utc` from the
publisher's UTC hour string. Nothing more.

### 3.3 Weather (`nyc_weather`, the event rows of the `airport_weather` category)

What it is: hourly surface observations at the three airports from the
Iowa Environmental Mesonet's ASOS feed, as the package converted them:
temperature and dew point in Fahrenheit, humidity in percent, wind
direction in degrees, wind speed and gust in miles per hour,
precipitation in inches for the hour, sea-level pressure in millibars,
visibility in statute miles, and the observation hour as a UTC instant.

What the profile showed: 13,014 rows against 13,026 airport-hours
between the first and the last observation, so 12 airport-hours are
absent (four per airport); wind gust null on 74.6 percent of rows,
pressure on 11.5 percent, wind direction on 1.7 percent.

What the contract decided, and why. Units go into the column names
(`temp_f`, `wind_speed_mph`, `precip_inches`, `pressure_mb`,
`visibility_miles`), because a unit that lives only in a description is
a unit that gets lost. A null gust means no gust was reported, not a
gust of zero; the contract says so, and the mapping repeats it, because
an agent that treats the null as zero would understate every windy
hour. The 12 missing airport-hours are declared as a limitation with
their count, so that when a flight finds no weather the reason is
already written. The local date and hour are kept for reading and never
for joining; the UTC hour is the key. The spring-forward day (March 10)
has 23 local hours, and the contract says that too.

### 3.4 Carriers (`nyc_airlines`) and aircraft (`nyc_planes`), the lookups

The carrier table is sixteen rows, one per two-letter code that flew
from New York in the window, with the name the Bureau published in
2013. The contract's one substantive sentence is about age: several of
those carriers have merged or renamed since (Endeavor, ExpressJet, US
Airways, AirTran, Virgin America), and the names are kept as published
because the flights are 2013 flights. Its join resolves 100 percent of
flights, and the contract declares the floor at 100 percent, so a
future extract that loses a carrier fails.

The aircraft table is the 2014 releasable FAA registry snapshot for the
tail numbers the window saw: 3,322 aircraft with manufacturer, model,
year, engines, seats, engine type, and a cruise speed that is missing
on 3,299 of them. What the contract decided: the speed column stays
(the profile is the evidence; dropping it would hide the fact) but the
usage text says it is not a usable measure; the year is missing for 70
aircraft, stated; and the reason the join resolves only 84 percent of
flights is written where the analyst will look for it, in this
contract and in the unified one: American Airlines and Envoy Air
reported fleet numbers rather than registrations in 2013, and 1,521
flights carry no tail number at all.

### 3.5 Airports and runways (OurAirports, the 2026 reference)

The airport table is every airport carrying an IATA code in the
OurAirports database at a commit from September 2026: identifier,
type, name, coordinates, elevation, region, municipality, codes, and a
free-text keywords column. The window is the fetch script's (airports
with an IATA code, because that is the code the flights carry). Two
columns are dropped in silver (an internal id and a home page link)
and the decision is recorded. The continent code for North America and
the country code for Namibia are the text `NA`, which the file
connector's reader would read as missing by default; the landing turns
the default markers off (finding F-50), and the README says so.

The runway table is every runway of those airports: length, width,
surface, lighting, closure, and end identifiers. The contract records
that a published length of 0 reads as unknown, never as a measurement,
and that the twelve runway-end coordinate and heading columns stay in
bronze because no downstream question uses them.

The reason these two tables matter is the vintage gap, which the next
section is about.

## 4. The unification: every join, and why it is the way it is

The gold star carries no shared business-entity dimension (D-41). Every
join between sources happens once, in silver, in human-owned SQL, and
the contract of the unified table declares each join with the key it
uses, the completeness that was measured, and the floor a rule
enforces. The two unified tables are `silver_flights` and
`silver_airport_weather`.

### 4.1 `silver_flights`: one row per flight, five references joined in

The grain is the flight (the `silver_nyc_flights` grain, one row per
scheduled departure), and it stays the grain after every join because
every join is to a unique key or to a one-row-per-airport aggregate.
Every join is a left join: a flight whose reference is unknown keeps
its row with null attributes, never disappears. That is the first
decision, and it is recorded as `decisionUnresolvedReferences`.

| Join | Key | Right table | Measured | Floor | Why the floor sits where it does |
|---|---|---|---|---|---|
| carrier | `carrier_code` | `silver_nyc_airlines` | 1.0000 | 1.00 | every code resolves; losing one is a defect |
| aircraft | `tail_number` | `silver_nyc_planes` | 0.8396 | 0.80 | fleet numbers and missing tail numbers leave 16 percent unresolved by the publisher's own data; the floor sits below the measurement so a registry refresh that adds coverage passes and one that loses it fails |
| origin | `origin_airport` | `silver_ourairports_airports` | 1.0000 | 1.00 | three airports, all present |
| destination | `dest_airport` | `silver_ourairports_airports` | 0.9791 | 0.97 | every unresolved flight is a Palm Beach flight (the vintage effect below); the floor sits just under the measurement for the same reason as the aircraft join |
| longest runway | `airport_ident` | an aggregate over `silver_ourairports_runways` | follows the airport join | | the longest open runway with a published length per airport, computed once and joined as one column for the origin and one for the destination |

The completeness numbers are not estimates. They were measured at the
committed samples, written into the contract, and are re-measured by
`tests/test_declared_joins.py` on every run of the local lane, which
fails if the warehouse disagrees with the contract by more than 0.0005
or if any join falls under its floor. A join completeness that was not
measured never enters a contract; the rule is in CLAUDE.md.

Why unify here and not in gold: the star's categories are meant to be
self-contained, wide rows that a typed surface can answer questions on
without further joins, and the place to settle "which carrier name,
which aircraft, which airport attributes" is the layer a person owns
and can read (silver SQL), under a contract that says what the joins
resolve. If the star carried a shared airport dimension, the
reconciliation would live in generated code, and the completeness
would be nobody's declaration.

Why the runway aggregate is derived the way it is: the reference has
many runways per airport, several closed, some without a published
length, and one published as zero. The longest open runway with a
published length is the one attribute of a runway table a flight
question is likely to ask for (can this airport take this aircraft),
and defining it once in the unified model keeps the definition in one
place with its contract.

### 4.2 `silver_airport_weather`: one row per airport-hour, the reference joined in

One join, `airport_code` to `iata_code`, measured 1.0000 with a floor
of 1.00, plus the same longest-runway aggregate. The grain is the
airport-hour and stays so. The reason this table exists as a unified
table rather than the weather table mapping straight into gold is
symmetry: both aviation categories carry the same airport attributes
from the same reference, joined on the same conformed code, so a
question about elevation and visibility can be asked of either.

### 4.3 The cross-category join: a flight's weather at departure

The star declares one cross-category join, `flights_to_origin_weather`:
`flights.origin_airport = airport_weather.airport_code AND
flights.departure_hour_utc = airport_weather.observed_hour_utc`. It is
declared on the star contract with the conformed key it uses
(`airport_iata`), the calendar grain (hour), the measured completeness
(0.9994: 97 of 166,158 flights fall in the airport-hours the weather
feed has no observation for), a floor (0.99), a worked example query,
and a note that says why destination weather is out of reach (the
weather feed covers the three New York airports only). The declared-join
gate re-measures it through the typed marts and through silver alike.

Why it is declared rather than left to the reader: the registry
carries the declaration into both categories' expert context, so an
agent asked "do flights run later in wet hours" can find the join, its
keys, its example, and its completeness without guessing, and a person
testing the agent can tell that the 0.9994 came from a measurement and
the join condition from a person.

## 5. Conformance: the keys that make the joins possible

Three keys are conformed across the family, each with a normalization
rule declared once on the star contract and cited by every silver
contract that carries the key:

| Key | Rule | Carried by |
|---|---|---|
| `airport_iata` | `VARCHAR`, `^[A-Z]{3}$` | `silver_nyc_flights` (origin, destination), `silver_nyc_weather`, `silver_ourairports_airports`, both unified tables |
| `carrier_code` | `VARCHAR`, `^[A-Z0-9]{2,3}$` | `silver_nyc_flights`, `silver_nyc_airlines`, `silver_flights` |
| `tail_number` | `VARCHAR`, `^[A-Z0-9]{2,6}$` | `silver_nyc_flights`, `silver_nyc_planes`, `silver_flights` |

Each carrying contract holds its column to the regex with an
error-severity rule, so gate 3 runs the normalization on every build,
and the K1 gate (`tests/test_conformed_keys.py`) holds the declarations
to each other: a key a silver contract names must be declared on the
star, a declared key must be carried by at least two contracts (a key
with one carrier is decoration, not a join), and every carrying column
must have the declared type and its rule. The retail category declares
no conformed key, and that absence is the honest statement that it
relates to nothing else.

Why upper case in the rules when the served values are lower case: the
silver plane keeps the codes as the publishers print them, and the
star's typed surface lowercases every string value by rule (D-18
Amendment M), so a literal in a query is written in lower case
(`origin_airport = 'jfk'`) and the registry, the query hint, and the
server instructions all say so.

## 6. The calendar: one time base for the whole star

Every category's time column is an instant in UTC, and the star's
timeframe dimension is one conformed calendar: a row per (grain,
period start) shared by every category that uses it. Flights use
`departure_hour_utc` at hour grain; weather uses `observed_hour_utc` at
hour grain; retail uses `invoiced_at` at minute grain. At the committed
samples the calendar has 6,345 rows, 2,004 of them retail minutes, and
every one of the 3,439 departure hours is a row the weather category
minted too, which is what makes the cross-category join a join on the
calendar rather than a date arithmetic exercise.

What was decided: local time is kept for reading (the HHMM columns,
the local date and hour on weather) and never for joining; the UTC hour
is the key; the DST change on March 10, 2013 is where this matters, and
the conservation gate checks that the local calendar day agrees with
the UTC hour under it. Retail and aviation never meet in time (December
2009 against 2013), and the star says so plainly: the calendar aligns
them in shape, not in time.

## 7. Gold: what the mapping contracts declare, and why

A mapping contract turns a silver table into a category. It names the
time column and its grain, the grain of the fact (transaction, with a
derived identity over the silver grain tuple), and a role for every
field: dimension, measure, or time. The engine does the rest.

The `flights` mapping puts the four on-time quantities (departure
delay, arrival delay, air time, distance) in the measure role and
everything else in the dimension role, including the HHMM clock times,
because a clock time is a label of the event, not a quantity to sum.
Cancellations flow through retained and flagged, so a rate is a query,
never a filter the engine applied. The dimension payload is wide (28
attributes plus the derived identity) on purpose: the typed mart is
meant to answer a flight question without a further join, and the cost
of that width is measured and recorded (finding F-44: the flights
values dimension is 59 MB of a 106 MB artifact).

The `airport_weather` mapping puts the nine observation quantities in
the measure role and the airport attributes in the dimension role, and
it carries the contract's warning that wind direction is a measure by
type and never additive by meaning.

The `invoice_lines` mapping is the original shape: six dimensions, two
measures, minute grain.

For each category the engine emits a values dimension (the wide
payload, deduplicated by content key), a columns dimension (the schema
key), a fact, a typed mart, and a projection view; once per star it
emits the shared source, run, and timeframe groups and the context
registry. Nothing in that emission is written by hand; the star
contract's three objects per category are rendered from the mapping by
`scripts/render_star_objects.py`, and a gate holds the committed
contract to the render.

## 8. Serving: what the agent sees, and where each word came from

Every registry entry keeps two things apart by name. `data` is derived:
the fields with their types and roles, the grain, the conformed keys
and who shares them, the typed surface to query, the lowercase rule.
`expert_context` is authored: the subject, how to read the table, its
limitations, its lineage and vintage, the joins with their measured
completeness, the cross-category joins with their example, the
decisions, and a meaning per field, carried from the contracts
unchanged and labeled as authored. The category listing names each
category's subject and its registry keys, and the server instructions
tell an agent to read the context before it queries and to say which of
the two an answer rests on.

Concretely, when the agent is asked about Palm Beach: the rows say
3,471 flights to `pbi` with no destination name (data), and the flights
category's limitations say why (the 2026 reference codes it DJT, the
keywords crosswalk was not applied because keywords are free text).
When it is asked about wet hours: the join condition, the example, and
the 0.9994 are in the star's declaration (expert context), and the
answer (29.44 minutes against 12.42, 8.95 percent cancelled against
2.41) is a measurement the demo question set holds through the serving
path. The seven questions in `tests/fixtures/serving_questions.json`
each name the context an answer leans on, so a person testing the
agent can check both halves.

## 9. The vintage effect, as a worked lesson

The events are 2013. The aircraft registry is the 2014 release. The
airport reference is a 2026 snapshot. That gap was not an accident to
apologize for; it was kept because it is the normal condition of a
warehouse: reference data is refreshed, event data is not. Its effects
were measured and written where they belong. Palm Beach International
flew as PBI in 2013 and is coded DJT in the reference (its identifier
KPBI and its keywords still say PBI), so 3,471 flights resolve no
destination attributes; the contract declines to apply the keywords as
a crosswalk because keywords are free text, and the demo asks the agent
about it on purpose (question Q4). Carrier names are the 2013 names.
The aircraft registry does not know two carriers' fleets. Each of these
is a limitation sentence in a contract, a measured completeness on a
join, a floor in a rule, and a line in a gate.

## 10. Reading this for your own data

Each pattern above maps to a situation you will recognize.

- **Rows you are tempted to drop** (cancellations, returns, voids,
  soft deletes): retain and flag, state the consequence for every
  aggregate in the usage text, and let the consumer filter. Conservation
  against bronze then stays auditable.
- **Duplicates**: decide whether they are capture artifacts or events,
  write the decision as a `decision*` property with the measured rate,
  and enforce the residual grain with an error-severity rule.
- **A reference newer than your events** (a customer master, a product
  catalog, a location table refreshed after the transactions): declare
  the vintage on both contracts, measure the join completeness, set the
  floor just under it so a refresh that adds coverage passes and one
  that loses it fails, and keep unresolved rows with null attributes.
- **Codes shared across systems** (customer ids, SKUs, site codes):
  conform them in silver with one normalization rule declared once and
  cited by every carrier, and let the gate refuse a key that only one
  table carries.
- **A series with gaps** (sensor readings, hourly rates, daily
  balances): declare the coverage with its count, and let the join
  completeness, not a silent inner join, show the effect.
- **Measurements that are absent when not observed** (a gust, a
  discount, a reason code): say that null means not reported, not zero,
  in the field's meaning, because an agent will read it.
- **Units and time zones**: units in column names; one UTC key for
  joining; local time as reading columns; the conformed calendar does
  the alignment.
- **A table that mixes detail and roll-ups** (economies and regional
  aggregates, accounts and their parents, SKUs and bundles): flag the
  roll-ups by an explicit list, never a name pattern, and say in the
  usage text what double counts. The walkthrough's worked example (the
  World Bank GDP series) is exactly this case.
- **When to unify and when to stand alone**: unify in silver when two
  sources describe the same entity and a question will need both
  columns on one row; leave a category alone when it shares nothing,
  and let the star's calendar align it in shape only.
- **What not to do**: no shared entity dimension in gold; no join
  completeness that was not measured; no rows dropped without a
  recorded decision; no pattern-derived flags; no unit or null semantics
  that live only in someone's head.

## 11. Where each claim is enforced

| Claim | Where it is held |
|---|---|
| No rows dropped through the cleanup and unified planes; every fact row reaches the mart | `tests/test_aviation_conservation.py`; the star's C1 and C5 rules |
| The five silver joins and the cross-category join at their declared completeness and above their floors | `tests/test_declared_joins.py`; the error-severity rules in the unified contracts |
| The conformed keys, their rules, and their carriers agree | `tests/test_conformed_keys.py` (K1); the regex rules in every carrying contract |
| Departure delay null exactly on cancellations; arrival delay and air time null on the 5,480; the null patterns the usage text states | `tests/test_aviation_conservation.py` |
| The clock arithmetic and the local calendar against the UTC hour under DST | `tests/test_aviation_conservation.py` |
| The reference coverage (PBI, the aircraft registry) and the weather coverage the limitations state | `tests/test_aviation_conservation.py` |
| The seven demo answers through the serving path | `tests/test_serving_questions.py` over `tests/fixtures/serving_questions.json` |
| The registry keeps data and expert context apart and carries every join | `tests/test_context_compiler.py` |
| The committed extracts are the bytes their READMEs state | `tests/test_committed_samples.py` |
| Every contract's provenance is honest | `tests/test_contract_provenance.py` |
| The star contract's objects are the rendered pattern | `tests/test_render_star_objects.py` |
| The emitted models are the fixed point the oracle holds | `tests/test_engine_emission.py` |
| The demo artifact is the built warehouse's content | `scripts/check_demo_digest.py` in CI |
