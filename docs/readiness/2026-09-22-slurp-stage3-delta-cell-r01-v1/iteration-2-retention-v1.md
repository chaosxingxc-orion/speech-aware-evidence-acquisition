# Stage-3 delta store: retention for version 2 (owner decision 83)

Model-free. Counts, ids and percentages only -- no statement text, utterance text, gold label or model output.

## 1. What was decided

- predecessor store: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/prepared/SAEA-SLURP-STAGE3-DELTAS-V1/authored-stage3-deltas-v1r.json` (379 values, sha256 `092dd386bb45`)
- kept: **200**, retired: **179**
- tie threshold: 0.0 pp; unreached policy: `keep`
- values the flight never supplied: 123; values resolving no scenario: 0

## 2. Per node

| node | kept | retired | total |
| --- | ---: | ---: | ---: |
| perception | 80 | 39 | 119 |
| planner | 4 | 10 | 14 |
| reviewer | 40 | 55 | 95 |
| solver | 76 | 75 | 151 |

## 3. Per rule

| rule | kept | retired | total |
| --- | ---: | ---: | ---: |
| frontier-slope-tie | 117 | 61 | 178 |
| scenario | 83 | 118 | 201 |

## 4. Per scenario

Band = max(|PLANr - PLAN per-scenario pooled SLU delta|, 1.2485 pp floor). Floor source: `docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/registered-facts-v1.json`.

| scenario | n | CELL-1 delta pp | own-null delta pp | band pp | signal | values | kept | retired |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| alarm | 60 | -6.7822 | +0.6313 | 1.2485 | harm-beyond-band | 21 | 0 | 21 |
| audio | 60 | +8.9440 | +12.1721 | 12.1721 | inside-band | 3 | 1 | 2 |
| calendar | 60 | +0.2394 | -1.1285 | 1.2485 | inside-band | 46 | 29 | 17 |
| cooking | 60 | -1.0645 | +1.2929 | 1.2929 | inside-band | 16 | 16 | 0 |
| datetime | 60 | +4.1496 | +3.7738 | 3.7738 | gain-beyond-band | 29 | 29 | 0 |
| email | 60 | +2.1595 | +5.2555 | 5.2555 | inside-band | 34 | 18 | 16 |
| general | 60 | -12.3723 | -1.0193 | 1.2485 | harm-beyond-band | 3 | 1 | 2 |
| iot | 60 | -3.4235 | -1.0199 | 1.2485 | harm-beyond-band | 19 | 0 | 19 |
| lists | 60 | -1.8162 | -5.4841 | 5.4841 | inside-band | 25 | 12 | 13 |
| music | 60 | -2.7542 | -0.8972 | 1.2485 | harm-beyond-band | 0 | 0 | 0 |
| news | 60 | -6.5629 | -1.5961 | 1.5961 | harm-beyond-band | 23 | 0 | 23 |
| play | 60 | -5.7785 | -4.0106 | 4.0106 | harm-beyond-band | 25 | 1 | 24 |
| qa | 60 | +0.6572 | -4.4167 | 4.4167 | inside-band | 11 | 5 | 6 |
| recommendation | 60 | +1.8173 | +0.0129 | 1.2485 | gain-beyond-band | 25 | 25 | 0 |
| social | 60 | -2.1198 | -1.2087 | 1.2485 | harm-beyond-band | 30 | 0 | 30 |
| takeaway | 60 | -0.0230 | -2.3881 | 2.3881 | inside-band | 35 | 28 | 7 |
| transport | 60 | +1.5291 | -0.7447 | 1.2485 | gain-beyond-band | 29 | 29 | 0 |
| weather | 60 | +8.3387 | +9.0459 | 9.0459 | inside-band | 22 | 21 | 1 |

## 5. The rule, in the preregistered words

Owner decision 83: "the per-scenario effect x prefilled-token frontier decides which deltas survive -- a delta whose target scenario shows a net harm beyond the null band is retired in version t+1, one whose scenario gains is kept, and the cost weight is the frontier slope."

1. RETIRE when every targeted scenario is harmed beyond its own band.
2. KEEP when any targeted scenario gains beyond its own band.
3. Otherwise the frontier-slope weighting decides: the CELL-1 arm sits off the prefilled-token frontier (+912 prefilled tokens per row, +2.5 % GPU-h, pooled SLU -0.48 pp), so a row is kept only if its own per-delta paired SLU mean over the rows it reached exceeds 0.0 pp.

