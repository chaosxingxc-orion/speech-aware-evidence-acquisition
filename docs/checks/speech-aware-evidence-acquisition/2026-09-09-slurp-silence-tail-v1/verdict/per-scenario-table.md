# Per-scenario intent accuracy — `SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1`

All 18 gold scenarios, sorted by intent delta. `intent` is the official projected-v2
scenario+action exact accuracy; `SLU-F1` is the per-row mean of the official per-sample
SLU-F1, which is what the paired contrast is computed on (the paper-facing SLU-F1 is the
micro aggregate and is reported in the verdict note).

| scenario | n | intent, comparator | intent, cell | intent delta | saves | harms | SLU-F1 delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| `general` | 61 | 36.07 | 44.26 | +8.1967 | 6 | 1 | -0.2530 |
| `audio` | 30 | 73.33 | 80.00 | +6.6667 | 2 | 0 | +2.3744 |
| `datetime` | 61 | 81.97 | 88.52 | +6.5574 | 4 | 0 | +1.4298 |
| `cooking` | 37 | 59.46 | 64.86 | +5.4054 | 2 | 0 | +0.4505 |
| `calendar` | 61 | 65.57 | 70.49 | +4.9180 | 3 | 0 | +3.2293 |
| `play` | 60 | 40.00 | 43.33 | +3.3333 | 3 | 1 | +3.2591 |
| `qa` | 60 | 58.33 | 61.67 | +3.3333 | 2 | 0 | +5.1330 |
| `alarm` | 58 | 87.93 | 89.66 | +1.7241 | 1 | 0 | -2.3895 |
| `social` | 60 | 80.00 | 81.67 | +1.6667 | 1 | 0 | +2.3679 |
| `email` | 61 | 83.61 | 85.25 | +1.6393 | 1 | 0 | -0.0584 |
| `lists` | 60 | 86.67 | 86.67 | +0.0000 | 0 | 0 | +0.2712 |
| `transport` | 60 | 71.67 | 71.67 | +0.0000 | 2 | 2 | +5.5386 |
| `weather` | 60 | 93.33 | 93.33 | +0.0000 | 0 | 0 | +1.4803 |
| `news` | 60 | 78.33 | 76.67 | -1.6667 | 0 | 1 | -0.1992 |
| `music` | 51 | 84.31 | 82.35 | -1.9608 | 1 | 2 | +0.6133 |
| `iot` | 61 | 85.25 | 81.97 | -3.2787 | 1 | 3 | +1.1784 |
| `recommendation` | 60 | 71.67 | 68.33 | -3.3333 | 0 | 2 | -2.0146 |
| `takeaway` | 39 | 76.92 | 66.67 | -10.2564 | 0 | 4 | +0.4353 |

**Section 4.1 clause 3, as written: no scenario loses more than 3.0 pp of intent accuracy, and at most 2 of the 18 scenarios lose anything at all.** Measured: 5 scenarios lose intent and the worst loses -10.2564 pp. The clause FAILS on both halves.
