# E1T scores: claude-desktop

build: registry md5 574adc681fcb491a1b5ff437abc07435 (9 rows), sha256 e4b410efa6145a5b
complete: True (9 of 9 fixture conversations)
T1 9 of 9 | T 9 of 9 | V 9 of 9 | F 9 of 9 | R 0 | C 9 of 9 | K 9 of 9

CALLED 9 of 9: called every time
VERIFIES 9 of 9: every tool message verified on the producer's build
FIDELITY 9 of 9: rendered verbatim by the host
REPORTED any accepted call C 9 of 9; count equals the key K 9 of 9 (never a condition)

| fixture | n | T1 | T | V | F | R | C | K |
|---|---|---|---|---|---|---|---|---|
| F1 | 3 | 3 | 3 | 3 | 3 | 0 | 3 | 3 |
| F2 | 3 | 3 | 3 | 3 | 3 | 0 | 3 | 3 |
| F3 | 3 | 3 | 3 | 3 | 3 | 0 | 3 | 3 |

| id | fixture | T1 | T | C | field | kind | rows | V | outcome | K | F | lines | R | calls | 2nd turn | seconds | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cd-F1-r1 | F1 | True | True | True | invoice_lines.quantity | rule_wanted | 90 | True | reproduces at the same contract versions | True | True | 5 | 0 | 6 | False | 2.0 | None |
| cd-F1-r2 | F1 | True | True | True | invoice_lines.quantity | rule_wanted | 90 | True | reproduces at the same contract versions | True | True | 5 | 0 | 6 | False | 1.0 | None |
| cd-F1-r3 | F1 | True | True | True | invoice_lines.quantity | rule_wanted | 90 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 1.0 | None |
| cd-F2-r1 | F2 | True | True | True | flights.arr_delay_minutes | meaning_unclear | 379 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 1.0 | None |
| cd-F2-r2 | F2 | True | True | True | flights.arr_delay_minutes | meaning_unclear | 379 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 1.0 | None |
| cd-F2-r3 | F2 | True | True | True | flights.arr_delay_minutes | meaning_unclear | 379 | True | reproduces at the same contract versions | True | True | 5 | 0 | 5 | False | 1.0 | None |
| cd-F3-r1 | F3 | True | True | True | airport_weather.wind_gust_mph | i_depend_on_this | 3312 | True | reproduces at the same contract versions | True | True | 5 | 0 | 3 | False | 1.0 | None |
| cd-F3-r2 | F3 | True | True | True | airport_weather.wind_gust_mph | i_depend_on_this | 3312 | True | reproduces at the same contract versions | True | True | 5 | 0 | 5 | False | 1.0 | None |
| cd-F3-r3 | F3 | True | True | True | airport_weather.wind_gust_mph | i_depend_on_this | 3312 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 1.0 | None |

Canary (the October 21 reading rule):
- cd-C1 (C1): fail (tool calls 0)
- cd-C2 (C2): fail (tool calls 1)

Re-runs reported: none; first attempts kept: none
