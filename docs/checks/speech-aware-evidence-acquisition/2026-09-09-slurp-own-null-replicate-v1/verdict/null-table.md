# The null table — SLURP's own greedy replicate

Signed **replicate minus comparator**. 10,000 replicates, seed 20260903, CI90. The speaker-clustered family is the honest one; the scenario-stratified family is beside it. **The half-width is the margin.**

## Paper-facing micro (pooled) metrics

| metric | comparator | replicate | delta | speaker-clustered CI90 | **half-width** | scenario-stratified CI90 | half-width |
|---|---:|---:|---:|---|---:|---|---:|
| entities strict F1 (micro) | 21.9105 | 22.6667 | **+0.7562** | [-0.5225, +1.9988] | **1.2607** | [-0.5208, +2.0538] | 1.2873 |
| Word-F1 (micro) | 33.6868 | 34.1168 | **+0.4300** | [-0.7093, +1.5541] | **1.1317** | [-0.5935, +1.5050] | 1.0493 |
| Char-F1 (micro) | 38.2007 | 38.3040 | **+0.1033** | [-1.1904, +1.3582] | **1.2743** | [-1.0958, +1.3089] | 1.2024 |
| SLU-F1 (micro) | 35.8020 | 36.0893 | **+0.2873** | [-0.9088, +1.4521] | **1.1804** | [-0.8003, +1.4046] | 1.1025 |

## Per-row metrics

| metric | comparator | replicate | delta | speaker-clustered CI90 | **half-width** | scenario-stratified CI90 | saves | harms | ties | sign p |
|---|---:|---:|---:|---|---:|---|---:|---:|---:|---:|
| intent (scenario+action) | 73.1000 | 73.6000 | **+0.5000** | [-0.4049, +1.4341] | **0.9195** | [-0.4000, +1.4000] | 18 | 13 | 969 | 0.4731 |
| scenario | 82.6000 | 83.0000 | **+0.4000** | [-0.4188, +1.2322] | **0.8255** | [-0.4000, +1.2000] | 15 | 11 | 974 | 0.5572 |
| action | 74.6000 | 75.0000 | **+0.4000** | [-0.5882, +1.3699] | **0.9790** | [-0.5000, +1.3000] | 19 | 15 | 966 | 0.6076 |
| entities strict F1 (per row) | 12.9593 | 13.2440 | **+0.2848** | [-0.5063, +1.0329] | **0.7696** | [-0.5186, +1.0981] | 24 | 17 | 959 | 0.3489 |
| Word-F1 (per row) | 18.8716 | 19.0595 | **+0.1879** | [-0.6313, +0.9653] | **0.7983** | [-0.6100, +0.9868] | 39 | 34 | 927 | 0.64 |
| Char-F1 (per row) | 21.1274 | 21.1872 | **+0.0599** | [-0.8437, +0.9050] | **0.8743** | [-0.8029, +0.9452] | 45 | 31 | 924 | 0.1354 |
| SLU-F1 (per row) | 19.7464 | 19.8857 | **+0.1393** | [-0.6963, +0.9413] | **0.8188** | [-0.6764, +0.9633] | 43 | 33 | 924 | 0.3019 |

## The normalized secondary, same rows

| metric | official delta | normalized delta | official half-width | normalized half-width |
|---|---:|---:|---:|---:|
| entities strict F1 (micro) | +0.7562 | +0.6167 | 1.2607 | 1.4311 |
| Word-F1 (micro) | +0.4300 | +0.2861 | 1.1317 | 1.2557 |
| Char-F1 (micro) | +0.1033 | +0.0918 | 1.2743 | 1.2992 |
| SLU-F1 (micro) | +0.2873 | +0.1996 | 1.1804 | 1.2549 |
| intent (scenario+action) | +0.5000 | +0.7000 | 0.9195 | 1.0139 |
| scenario | +0.4000 | +0.6000 | 0.8255 | 0.8908 |
| action | +0.4000 | +0.6000 | 0.9790 | 1.0671 |
| entities strict F1 (per row) | +0.2848 | +0.1948 | 0.7696 | 0.9193 |
| Word-F1 (per row) | +0.1879 | +0.0651 | 0.7983 | 0.8941 |
| Char-F1 (per row) | +0.0599 | +0.0386 | 0.8743 | 0.9102 |
| SLU-F1 (per row) | +0.1393 | +0.0524 | 0.8188 | 0.8889 |

