# The 86-flag operating point

The flag is set at whatever threshold flags the MF-9 schema judge's 86 rows, ties at
the boundary INCLUDED, on the primary statistic `min_token_logprob`. The realized
count is reported, never the requested one: it landed on exactly 86, at a cutoff of
`min_token_logprob <= -0.792173`.

The schema and legality judges are RECOMPUTED ON THIS ARM'S OWN ROWS under this
probe's own stricter definition, so the three are comparable like for like. The
owner-fixed external bar (72.09 % at 86 flags, KC-S1b's number on the two-stage slot
arm) is a different arm's measurement and is carried as a bar, never as a row here.

## `intent_error`

| judge | flagged | caught | errors | precision % | recall % |
|---|---:|---:|---:|---:|---:|
| confidence flag (`min_token_logprob`) | 86 | 44 | 265 | 51.16 | 16.60 |
| schema judge, recomputed here | 13 | 4 | 265 | 30.77 | 1.51 |
| legality judge, recomputed here | 42 | 28 | 265 | 66.67 | 10.57 |
| union: confidence + schema | 97 | 46 | 265 | 47.42 | 17.36 |
| union: all three | 123 | 62 | 265 | 50.41 | 23.40 |

## `slot_error`

| judge | flagged | caught | errors | precision % | recall % |
|---|---:|---:|---:|---:|---:|
| confidence flag (`min_token_logprob`) | 86 | 69 | 638 | 80.23 | 10.82 |
| schema judge, recomputed here | 13 | 9 | 638 | 69.23 | 1.41 |
| legality judge, recomputed here | 42 | 29 | 638 | 69.05 | 4.55 |
| union: confidence + schema | 97 | 76 | 638 | 78.35 | 11.91 |
| union: all three | 123 | 93 | 638 | 75.61 | 14.58 |

## `unmatched_gold`

| judge | flagged | caught | errors | precision % | recall % |
|---|---:|---:|---:|---:|---:|
| confidence flag (`min_token_logprob`) | 86 | 56 | 559 | 65.12 | 10.02 |
| schema judge, recomputed here | 13 | 9 | 559 | 69.23 | 1.61 |
| legality judge, recomputed here | 42 | 26 | 559 | 61.90 | 4.65 |
| union: confidence + schema | 97 | 63 | 559 | 64.95 | 11.27 |
| union: all three | 123 | 78 | 559 | 63.41 | 13.95 |

## The deterministic pair on its own

The one union the registered read does not compute, added so the verdict's claim that the
confidence flag lowers the deterministic judges' precision is MEASURED rather than inferred
(`deterministic-pair.json`, zero contacts).

| target | schema OR legality alone | ... plus the confidence flag |
|---|---|---|
| `intent_error` | 52 flags, 29 caught, **55.77 %** / 10.94 % | 123 flags, 62 caught, **50.41 %** / 23.40 % |
| `slot_error` | 52 flags, 35 caught, **67.31 %** / 5.49 % | 123 flags, 93 caught, **75.61 %** / 14.58 % |
| `unmatched_gold` | 52 flags, 32 caught, **61.54 %** / 5.72 % | 123 flags, 78 caught, **63.41 %** / 13.95 % |

On intent error the flag costs 5.36 pp of precision to buy 12.45 pp of recall. On the two slot
targets it RAISES precision as well. That asymmetry is the same one section 3.1 reports: the
whole-answer minimum is a slot signal, and the rule asked it an intent question.

## The rule's arm B

| | value |
|---|---:|
| precision at 86 flags, intent error | **51.1628 %** |
| speaker-cluster bootstrap CI90 | [42.5287, 59.0909] |
| the bar it must exceed | 72.09 % |
| clears it | **no** -- the point estimate is 20.93 pp below the bar and the whole interval sits under it |

The flag budget is rescaled to each replicate's own size, so a replicate that draws
fewer rows flags proportionally fewer of them.

