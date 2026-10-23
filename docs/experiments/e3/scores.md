# E3 scores

- ledger rows: 420; ledger total: $55.6640

| arm | model | fixture | n | written | failed | lint@1 | grounded@1 | machine@1 runs | judgment@1 runs | structural@1 runs | agreement median (min, max) | normalized median | shared median (min, max) | mismatches median | grain set equal | empty descriptions | out tokens median (first-attempt runs) | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | claude-sonnet-5 | silver-cleanup-nyc-airlines | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.0 (0.0, 1.0) | 0.0 | 0.0 (0, 1) | 5.0 | 1 | 0 | 2031.5 (2031.5) | $0.3283 |
| A0 | claude-sonnet-5 | silver-cleanup-nyc-flights | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0.0 (0, 0) | 38.0 | 0 | 0 | 6864.5 (6864.5) | $0.9042 |
| A0 | claude-sonnet-5 | silver-cleanup-nyc-weather | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0.0 (0, 0) | 29.0 | 0 | 0 | 6385.5 (6385.5) | $0.8069 |
| A1 | claude-sonnet-5 | silver-cleanup-nyc-airlines | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0.0 (0, 0) | 5.0 | 0 | 0 | 1630.0 (1630.0) | $0.2879 |
| A1 | claude-sonnet-5 | silver-cleanup-nyc-flights | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.0 (0.0, 1.0) | 0.0 | 0.0 (0, 1) | 38.0 | 0 | 0 | 6976.5 (6976.5) | $0.9021 |
| A1 | claude-sonnet-5 | silver-cleanup-nyc-weather | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0.0 (0, 0) | 29.0 | 0 | 0 | 6287.5 (6287.5) | $0.8399 |
| A | claude-sonnet-5 | mapping-propose-airport-weather | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.9853 (0.9852941176470589, 1.0) | 0.9853 | 17.0 (17, 17) | 4.0 | 0 | 0 | 5306.0 (5306.0) | $0.7238 |
| A | claude-sonnet-5 | mapping-propose-flights | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.9924 (0.9924242424242424, 1.0) | 0.9924 | 33.0 (33, 33) | 2.0 | 0 | 0 | 12280.5 (12280.5) | $1.4580 |
| A | claude-sonnet-5 | silver-cleanup-nyc-airlines | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 1.0 (1.0, 1.0) | 0.6667 | 2.0 (2, 2) | 1.0 | 10 | 0 | 1944.5 (1944.5) | $0.3329 |
| A | claude-sonnet-5 | silver-cleanup-nyc-flights | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.9417 (0.92, 0.9714285714285714) | 0.2684 | 5.5 (4, 8) | 29.5 | 0 | 0 | 11845.0 (11845.0) | $1.4144 |
| A | claude-sonnet-5 | silver-cleanup-nyc-planes | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 1.0 (1.0, 1.0) | 0.4 | 4.0 (3, 7) | 11.0 | 2 | 0 | 5039.0 (5039.0) | $0.6581 |
| A | claude-sonnet-5 | silver-cleanup-nyc-weather | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.8 (0.8, 0.8) | 0.1714 | 3.0 (3, 3) | 24.5 | 0 | 0 | 9919.0 (9919.0) | $1.1964 |
| A | claude-sonnet-5 | silver-cleanup-ourairports-airports | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.9556 (0.9333333333333333, 0.9692307692307692) | 0.4778 | 9.0 (7, 13) | 21.0 | 1 | 0 | 10110.5 (10110.5) | $1.2207 |
| A | claude-sonnet-5 | silver-cleanup-ourairports-runways | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.9 (0.8666666666666667, 1.0) | 0.33 | 3.5 (3, 8) | 24.0 | 10 | 0 | 11413.5 (11413.5) | $1.3423 |
| B-baseline | claude-sonnet-5 | amend-silver-invoice-lines-f28 | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 1.0 (1.0, 1.0) | 1.0 | 10.0 (10, 10) | 0.0 | 10 | 0 | 5132.5 (5132.5) | $0.7218 |
| B-baseline | claude-sonnet-5 | describe-silver-airport-weather | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 1.0 (1.0, 1.0) | 1.0 | 18.0 (18, 18) | 0.0 | 10 | 0 | 10990.0 (10990.0) | $1.2309 |
| B-baseline | claude-sonnet-5 | describe-silver-flights | 10 | 10 | 0 | 2 | 2 | 0 | 0 | 8 | 0.9882 (0.9764705882352941, 0.9882352941176471) | 0.9882 | 34.0 (34, 34) | 2.0 | 0 | 0 | 24363.5 (14716.5) | $3.1056 |
| B | claude-sonnet-5 | amend-silver-invoice-lines-f28 | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 1.0 (1.0, 1.0) | 1.0 | 10.0 (10, 10) | 0.0 | 10 | 0 | 2082.0 (2082.0) | $0.4017 |
| B | claude-sonnet-5 | describe-silver-airport-weather | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 1.0 (1.0, 1.0) | 1.0 | 18.0 (18, 18) | 0.0 | 10 | 0 | 11021.5 (11021.5) | $1.2676 |
| B | claude-sonnet-5 | describe-silver-flights | 10 | 10 | 0 | 4 | 4 | 0 | 0 | 6 | 0.9882 (0.9882352941176471, 0.9882352941176471) | 0.9882 | 34.0 (34, 34) | 2.0 | 0 | 0 | 22103.5 (15284.0) | $2.4133 |
| baseline | claude-fable-5 | mapping-propose-airport-weather | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.9853 (0.8235294117647058, 0.9852941176470589) | 0.9853 | 17 (17, 17) | 3 | 0 | 0 | 3687 (3687) | $1.3306 |
| baseline | claude-fable-5 | mapping-propose-flights | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.9773 (0.8863636363636364, 0.9772727272727273) | 0.9773 | 33 (33, 33) | 6 | 0 | 0 | 6185 (6185) | $2.0930 |
| baseline | claude-fable-5 | mapping-propose-invoice-lines | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0 (0, 0) | None | 0 | 0 | 2236 (2236) | $0.8929 |
| baseline | claude-fable-5 | silver-cleanup-messy-orders | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0 (0, 0) | None | 0 | 0 | 5732 (5732) | $1.8009 |
| baseline | claude-fable-5 | silver-cleanup-nyc-airlines | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.0 (0.0, 1.0) | 0.0 | 0 (0, 1) | 5 | 0 | 0 | 1403 (1403) | $0.6622 |
| baseline | claude-fable-5 | silver-cleanup-nyc-flights | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 1.0 (1.0, 1.0) | 0.0526 | 1 (1, 1) | 37 | 0 | 0 | 5535 (5535) | $1.8227 |
| baseline | claude-fable-5 | silver-cleanup-nyc-planes | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 1.0 (1.0, 1.0) | 0.2 | 2 (2, 3) | 15 | 0 | 0 | 2941 (2941) | $1.0862 |
| baseline | claude-fable-5 | silver-cleanup-nyc-weather | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0 (0, 0) | 29 | 0 | 0 | 4583 (4583) | $1.5728 |
| baseline | claude-fable-5 | silver-cleanup-online-retail | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0 (0, 0) | None | 0 | 0 | 4838 (4838) | $1.5266 |
| baseline | claude-fable-5 | silver-cleanup-ourairports-airports | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.9429 (0.9384615384615385, 0.9692307692307692) | 0.7 | 13 (13, 14) | 13 | 0 | 0 | 5330 (5330) | $1.8049 |
| baseline | claude-fable-5 | silver-cleanup-ourairports-runways | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.9429 (0.92, 1.0) | 0.46 | 5 (4, 7) | 22 | 3 | 0 | 5873 (5873) | $1.9006 |
| baseline | claude-opus-5 | mapping-propose-airport-weather | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.9853 (0.8235294117647058, 0.9852941176470589) | 0.9853 | 17 (17, 17) | 3 | 0 | 0 | 3943 (3943) | $0.6731 |
| baseline | claude-opus-5 | mapping-propose-flights | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.9924 (0.9166666666666666, 0.9924242424242424) | 0.9924 | 33 (33, 33) | 4 | 0 | 0 | 6923 (6923) | $1.1265 |
| baseline | claude-opus-5 | mapping-propose-invoice-lines | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0 (0, 0) | None | 0 | 0 | 2025 (2025) | $0.4273 |
| baseline | claude-opus-5 | silver-cleanup-messy-orders | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0 (0, 0) | None | 0 | 0 | 5416 (5416) | $0.8833 |
| baseline | claude-opus-5 | silver-cleanup-nyc-airlines | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.0 (0.0, 1.0) | 0.0 | 0 (0, 1) | 5 | 0 | 0 | 1595 (1595) | $0.3470 |
| baseline | claude-opus-5 | silver-cleanup-nyc-flights | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0 (0, 0) | 39 | 0 | 0 | 6087 (6087) | $0.9517 |
| baseline | claude-opus-5 | silver-cleanup-nyc-planes | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 1.0 (1.0, 1.0) | 0.2 | 2 (2, 2) | 16 | 0 | 0 | 3213 (3213) | $0.5735 |
| baseline | claude-opus-5 | silver-cleanup-nyc-weather | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0 (0, 0) | 29 | 0 | 0 | 4133 (4133) | $0.7217 |
| baseline | claude-opus-5 | silver-cleanup-online-retail | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0 (0, 0) | None | 0 | 0 | 4876 (4876) | $0.7928 |
| baseline | claude-opus-5 | silver-cleanup-ourairports-airports | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 0.9385 (0.9333333333333333, 0.9384615384615385) | 0.6778 | 13 (12, 13) | 15 | 0 | 0 | 6159 (6159) | $1.0229 |
| baseline | claude-opus-5 | silver-cleanup-ourairports-runways | 5 | 5 | 0 | 5 | 5 | 0 | 0 | 0 | 1.0 (1.0, 1.0) | 0.6 | 6 (4, 6) | 20 | 0 | 0 | 6863 (6863) | $1.0820 |
| baseline | claude-sonnet-5 | mapping-propose-airport-weather | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.9853 (0.9852941176470589, 1.0) | 0.9853 | 17.0 (17, 17) | 4.0 | 0 | 0 | 6192.0 (6192.0) | $0.7995 |
| baseline | claude-sonnet-5 | mapping-propose-flights | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.9924 (0.9924242424242424, 1.0) | 0.9924 | 33.0 (33, 33) | 3.0 | 0 | 0 | 11587.0 (11587.0) | $1.3777 |
| baseline | claude-sonnet-5 | mapping-propose-invoice-lines | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0.0 (0, 0) | None | 0 | 0 | 3064.5 (3064.5) | $0.4686 |
| baseline | claude-sonnet-5 | silver-cleanup-messy-orders | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0.0 (0, 0) | None | 0 | 0 | 8005.0 (8005.0) | $0.9772 |
| baseline | claude-sonnet-5 | silver-cleanup-nyc-airlines | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.0 (0.0, 1.0) | 0.0 | 0.0 (0, 1) | 5.0 | 0 | 0 | 2231.0 (2231.0) | $0.3280 |
| baseline | claude-sonnet-5 | silver-cleanup-nyc-flights | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0.0 (0, 0) | 38.0 | 0 | 0 | 7133.5 (7133.5) | $0.9025 |
| baseline | claude-sonnet-5 | silver-cleanup-nyc-planes | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 1.0 (1.0, 1.0) | 0.2 | 2.0 (2, 2) | 15.0 | 0 | 0 | 4160.5 (4160.5) | $0.5553 |
| baseline | claude-sonnet-5 | silver-cleanup-nyc-weather | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0.0 (0, 0) | 29.0 | 0 | 0 | 5621.0 (5621.0) | $0.7704 |
| baseline | claude-sonnet-5 | silver-cleanup-online-retail | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.0 (0.0, 0.0) | 0.0 | 0.0 (0, 0) | None | 0 | 0 | 6532.5 (6532.5) | $0.8284 |
| baseline | claude-sonnet-5 | silver-cleanup-ourairports-airports | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 0.9385 (0.9333333333333333, 0.9384615384615385) | 0.6778 | 13.0 (12, 13) | 15.0 | 0 | 0 | 6728.5 (6728.5) | $0.8852 |
| baseline | claude-sonnet-5 | silver-cleanup-ourairports-runways | 10 | 10 | 0 | 10 | 10 | 0 | 0 | 0 | 1.0 (0.92, 1.0) | 0.4 | 4.0 (4, 5) | 22.0 | 1 | 0 | 9557.0 (9557.0) | $1.1194 |

## Verdict

```json
{
  "E3a": {
    "a1_docs_only_checked_median": {
      "silver-cleanup-nyc-airlines": 0.0,
      "silver-cleanup-nyc-flights": 0.0,
      "silver-cleanup-nyc-weather": 0.0
    },
    "a1_docs_only_shared_median": {
      "silver-cleanup-nyc-airlines": 0.0,
      "silver-cleanup-nyc-flights": 0.0,
      "silver-cleanup-nyc-weather": 0.0
    },
    "earned": false,
    "measured": true,
    "rule1": true,
    "rule1_fixtures_off_zero": [
      "silver-cleanup-nyc-flights",
      "silver-cleanup-nyc-weather",
      "silver-cleanup-nyc-airlines"
    ],
    "rule1_shared_median": {
      "silver-cleanup-nyc-airlines": 2.0,
      "silver-cleanup-nyc-flights": 5.5,
      "silver-cleanup-nyc-weather": 3.0
    },
    "rule1_shared_range": {
      "silver-cleanup-nyc-airlines": [
        2,
        2
      ],
      "silver-cleanup-nyc-flights": [
        4,
        8
      ],
      "silver-cleanup-nyc-weather": [
        3,
        3
      ]
    },
    "rule2": false,
    "rule2_compared": [
      "silver-cleanup-nyc-planes",
      "silver-cleanup-ourairports-airports",
      "silver-cleanup-ourairports-runways",
      "mapping-propose-flights",
      "mapping-propose-airport-weather"
    ],
    "rule2_fixtures_below_baseline": [
      "silver-cleanup-ourairports-airports",
      "silver-cleanup-ourairports-runways"
    ],
    "rule3": true,
    "rule3_grounded": [
      [
        80,
        80
      ],
      [
        80,
        80
      ]
    ],
    "rule3_lint": [
      [
        80,
        80
      ],
      [
        80,
        80
      ]
    ],
    "rule4": true,
    "rule4_a0_alone_satisfies_rule1": false,
    "rule4_a0_checked_median": {
      "silver-cleanup-nyc-airlines": 0.0,
      "silver-cleanup-nyc-flights": 0.0,
      "silver-cleanup-nyc-weather": 0.0
    },
    "unresolved_cells": []
  },
  "E3b": {
    "earned": true,
    "empty_descriptions": {
      "amend-silver-invoice-lines-f28": [
        0,
        0
      ],
      "describe-silver-airport-weather": [
        0,
        0
      ],
      "describe-silver-flights": [
        0,
        0
      ]
    },
    "measured": true,
    "rule1": true,
    "rule1_machine_errors_B": 0,
    "rule1_machine_errors_B_baseline": 0,
    "rule1_machine_runs_B_baseline": 0,
    "rule2": true,
    "rule2_judgment_runs": {
      "amend": [
        [
          0,
          10
        ],
        [
          0,
          10
        ]
      ],
      "describe": [
        [
          0,
          20
        ],
        [
          0,
          20
        ]
      ]
    },
    "rule3": true,
    "rule3_fixtures_below_B_baseline": [],
    "rule3_grain_set_equal": {
      "amend-silver-invoice-lines-f28": [
        10,
        10
      ],
      "describe-silver-airport-weather": [
        10,
        10
      ],
      "describe-silver-flights": [
        0,
        0
      ]
    },
    "rule4": true,
    "rule4_token_split": {
      "amend-silver-invoice-lines-f28": {
        "B_baseline_first_attempt_runs": 10,
        "B_baseline_output_tokens_first_attempt_median": 5132.5,
        "B_first_attempt_runs": 10,
        "B_output_tokens_first_attempt_median": 2082.0,
        "output_token_saving": 0.5943,
        "structure_share_chars_median": 0.1395
      },
      "describe-silver-airport-weather": {
        "B_baseline_first_attempt_runs": 10,
        "B_baseline_output_tokens_first_attempt_median": 10990.0,
        "B_first_attempt_runs": 10,
        "B_output_tokens_first_attempt_median": 11021.5,
        "output_token_saving": -0.0029,
        "structure_share_chars_median": 0.1532
      },
      "describe-silver-flights": {
        "B_baseline_first_attempt_runs": 2,
        "B_baseline_output_tokens_first_attempt_median": 14716.5,
        "B_first_attempt_runs": 4,
        "B_output_tokens_first_attempt_median": 15284.0,
        "output_token_saving": -0.0386,
        "structure_share_chars_median": 0.2292
      }
    },
    "unresolved_cells": []
  }
}
```
