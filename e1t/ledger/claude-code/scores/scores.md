# E1T scores: claude-code

build: registry md5 574adc681fcb491a1b5ff437abc07435 (9 rows), sha256 e4b410efa6145a5b
complete: True (15 of 15 fixture conversations)
T1 15 of 15 | T 15 of 15 | V 15 of 15 | F 15 of 15 | R 0 | C 15 of 15 | K 15 of 15

CALLED 15 of 15: called every time
VERIFIES 15 of 15: every tool message verified on the producer's build
FIDELITY 15 of 15: rendered verbatim by the host
REPORTED any accepted call C 15 of 15; count equals the key K 15 of 15 (never a condition)

| fixture | n | T1 | T | V | F | R | C | K |
|---|---|---|---|---|---|---|---|---|
| F1 | 5 | 5 | 5 | 5 | 5 | 0 | 5 | 5 |
| F2 | 5 | 5 | 5 | 5 | 5 | 0 | 5 | 5 |
| F3 | 5 | 5 | 5 | 5 | 5 | 0 | 5 | 5 |

| id | fixture | T1 | T | C | field | kind | rows | V | outcome | K | F | lines | R | calls | 2nd turn | seconds | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cc-F1-r1 | F1 | True | True | True | invoice_lines.quantity | rule_wanted | 90 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 12.93 | 0.044273 |
| cc-F1-r2 | F1 | True | True | True | invoice_lines.quantity | rule_wanted | 90 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 13.17 | 0.046541 |
| cc-F1-r3 | F1 | True | True | True | invoice_lines.quantity | rule_wanted | 90 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 14.23 | 0.051488 |
| cc-F1-r4 | F1 | True | True | True | invoice_lines.quantity | rule_wanted | 90 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 13.91 | 0.051433 |
| cc-F1-r5 | F1 | True | True | True | invoice_lines.quantity | rule_wanted | 90 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 13.47 | 0.050039 |
| cc-F2-r1 | F2 | True | True | True | flights.arr_delay_minutes | meaning_unclear | 379 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 12.28 | 0.063247 |
| cc-F2-r2 | F2 | True | True | True | flights.arr_delay_minutes | meaning_unclear | 379 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 12.7 | 0.064202 |
| cc-F2-r3 | F2 | True | True | True | flights.arr_delay_minutes | meaning_unclear | 379 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 13.22 | 0.063792 |
| cc-F2-r4 | F2 | True | True | True | flights.arr_delay_minutes | meaning_unclear | 379 | True | reproduces at the same contract versions | True | True | 5 | 0 | 5 | False | 14.09 | 0.072422 |
| cc-F2-r5 | F2 | True | True | True | flights.arr_delay_minutes | meaning_unclear | 379 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 13.44 | 0.063923 |
| cc-F3-r1 | F3 | True | True | True | airport_weather.wind_gust_mph | i_depend_on_this | 3312 | True | reproduces at the same contract versions | True | True | 5 | 0 | 3 | False | 12.44 | 0.054409 |
| cc-F3-r2 | F3 | True | True | True | airport_weather.wind_gust_mph | i_depend_on_this | 3312 | True | reproduces at the same contract versions | True | True | 5 | 0 | 2 | False | 10.5 | 0.036866 |
| cc-F3-r3 | F3 | True | True | True | airport_weather.wind_gust_mph | i_depend_on_this | 3312 | True | reproduces at the same contract versions | True | True | 5 | 0 | 4 | False | 14.05 | 0.057193 |
| cc-F3-r4 | F3 | True | True | True | airport_weather.wind_gust_mph | i_depend_on_this | 3312 | True | reproduces at the same contract versions | True | True | 5 | 0 | 2 | False | 9.52 | 0.035395 |
| cc-F3-r5 | F3 | True | True | True | airport_weather.wind_gust_mph | i_depend_on_this | 3312 | True | reproduces at the same contract versions | True | True | 5 | 0 | 3 | False | 11.96 | 0.053646 |

Controls, observed and never scored (prepare_feedback calls / tool calls / offer words in the reply):
- cc-P2-r1 (P2): 0 / 4 / 0
- cc-P2-r2 (P2): 0 / 3 / 0
- cc-P2-r3 (P2): 0 / 4 / 0
- cc-P3-r1 (P3): 0 / 3 / 0
- cc-P3-r2 (P3): 0 / 3 / 0
- cc-P3-r3 (P3): 0 / 3 / 0
- cc-P4-r1 (P4): 0 / 3 / 0
- cc-P4-r2 (P4): 0 / 4 / 0
- cc-P4-r3 (P4): 0 / 4 / 0

Canary (the October 21 reading rule):
- cc-C1 (C1): pass (tool calls 0)
- cc-C2 (C2): pass (tool calls 1)

Re-runs reported: none; first attempts kept: none
