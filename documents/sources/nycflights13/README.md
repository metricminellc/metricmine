# nycflights13: the `flights` help page (a governed document, D-43)

`flights.Rd` is a byte-for-byte copy of `man/flights.Rd` from
tidyverse/nycflights13 at commit
`df98ef215aa8216fe0838a0b8ac5bada646d814c`, the commit the committed
flight samples are pinned to (`data/samples/nyc_flights/README.md`).

- Upstream: https://raw.githubusercontent.com/tidyverse/nycflights13/df98ef215aa8216fe0838a0b8ac5bada646d814c/man/flights.Rd
- Bytes: 1,496; sha256 `5bdc5b7ee76e25a26d7c7a333c6d5d0c1a9f06d759726914ac369d970ebecb4e`
  (recorded as `upstream_sha256` in `documents/register/standing.yaml`;
  `.gitattributes` keeps the bytes verbatim).
- License: CC0, the package's declared license.
- Format: Rd markup (roxygen2 output), read by the text extractor as plain
  text. Its text digest under `metricmine.documents@1.0.0` is the standing
  row's `text_sha256`.

What it governs: `silver_nyc_flights.dep_delay_minutes` rests on the
sentence "Departure and arrival delays, in minutes. Negative times represent
early departures/arrivals." The quote spans two lines of the file and
matches after whitespace normalization; the binding is
`documents/register/bindings.yaml`. The copy changes only by pull request,
and the scan reads it on every run (`make scan`, the Governed documents
section).

Re-fetch to compare, never to overwrite in place:

    curl -sSL -o /tmp/flights.Rd "https://raw.githubusercontent.com/tidyverse/nycflights13/df98ef215aa8216fe0838a0b8ac5bada646d814c/man/flights.Rd"
    shasum -a 256 /tmp/flights.Rd documents/sources/nycflights13/flights.Rd
