# VAR-1 complete construction evidence

Source: `SLURP-VAR1-VARIANT-READ-V1-CORRECTED-V2` under the external data root, recipe `slurp-stage3-var1-construction-variant-read-v1`. Six sealed arms each use the same 625-row R01C TRAIN construction roster (discovery role, 625 utterance clusters). This is an aggregate data extraction without an admission or test claim.

The source analysis made zero ASR, encoder, model, network, scorer, server, or tokenizer contacts. Paired whole-utterance bootstrap: 10,000 draws, seed 20260915. Differences below are variant minus VAR1-PLAN in percentage points.

## Official pooled outcomes and primary contrasts

| Arm | Rows | SLU-F1 (%) | Intent (%) | SLU-F1 difference (pp) | CI95 (pp) | CI90 (pp) |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| plan | 625 | 58.51 | 70.56 | -- | -- | -- |
| exdiv | 625 | 58.68 | 70.88 | +0.17 | [-1.50, 1.88] | [-1.24, 1.59] |
| exk10 | 625 | 60.44 | 69.76 | +1.94 | [0.36, 3.52] | [0.61, 3.26] |
| exk30 | 625 | 60.46 | 70.72 | +1.95 | [0.48, 3.45] | [0.72, 3.21] |
| perk16c5 | 625 | 58.67 | 70.88 | +0.16 | [-1.36, 1.69] | [-1.09, 1.43] |
| planr | 625 | 60.38 | 69.28 | +1.87 | [0.41, 3.36] | [0.64, 3.13] |

Own-null cross-flight R01C CI95 half-widths: pooled SLU-F1 1.4739 pp; intent 1.7600 pp. Original analysis h is a CI95 quantity. Root CI90 calibration is a different interval; no root-calibrated value is asserted here.

## Candidate coverage and failures

Candidate coverage joins gold intent to sealed Perception candidates offline. Union and first-list rates coincide in these data.

| Arm | Gold intent in union / first list (%) | Mean width | Width histogram (width:rows) | Distinct IDs (%) | Candidate parse failures | MALFORMED | INTENT-UNCOVERED | INTENT-COVERED |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| plan | 77.76 / 77.76 | 2.664 | 1:30, 2:150, 3:445 | 96.64 | 0 | 0 | 131 | 53 |
| exdiv | 77.28 / 77.28 | 2.664 | 1:33, 2:144, 3:448 | 96.16 | 0 | 0 | 132 | 50 |
| exk10 | 76.80 / 76.80 | 2.694 | 1:27, 2:137, 3:461 | 96.64 | 0 | 1 | 138 | 50 |
| exk30 | 77.60 / 77.60 | 2.664 | 1:30, 2:150, 3:445 | 96.80 | 0 | 1 | 135 | 47 |
| perk16c5 | 80.32 / 80.32 | 3.030 | 1:47, 2:122, 3:332, 4:13, 5:111 | 93.60 | 0 | 1 | 119 | 62 |
| planr | 77.28 / 77.28 | 2.658 | 1:35, 2:144, 3:446 | 96.00 | 0 | 1 | 136 | 55 |

| Arm | ENTITY-FN-ONLY | ENTITY-FP-ONLY | ENTITY-MIXED | CORRECT |
| --- | ---: | ---: | ---: | ---: |
| plan | 37 | 80 | 172 | 152 |
| exdiv | 40 | 77 | 175 | 151 |
| exk10 | 40 | 76 | 161 | 159 |
| exk30 | 34 | 68 | 170 | 170 |
| perk16c5 | 42 | 83 | 169 | 149 |
| planr | 34 | 75 | 166 | 158 |

## Exact entity and empty-gold counts

Slot TP/FP/FN below are integer exact (type, filler) entity matches. Official pooled SLU-F1 instead uses fractional word/character TP/FP/FN; these integer counts cannot be substituted into that F1.

| Arm | Exact TP | FP | FN | Empty-gold rows | Empty-gold emitting | Emission (%) | Omission | Over-emission | Wrong filler, same type | Type swap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| plan | 345 | 454 | 399 | 191 | 114 | 59.69 | 192 | 247 | 187 | 20 |
| exdiv | 344 | 445 | 400 | 191 | 113 | 59.16 | 191 | 236 | 185 | 24 |
| exk10 | 368 | 433 | 376 | 191 | 113 | 59.16 | 183 | 240 | 172 | 21 |
| exk30 | 364 | 432 | 380 | 191 | 108 | 56.54 | 182 | 234 | 181 | 17 |
| perk16c5 | 352 | 465 | 392 | 191 | 119 | 62.30 | 186 | 259 | 183 | 23 |
| planr | 366 | 439 | 378 | 191 | 115 | 60.21 | 186 | 247 | 175 | 17 |

## All scenario rows

Each cell is scenario pooled SLU-F1 difference / intent accuracy difference (pp) versus VAR1-PLAN. Descriptive only: no per-scenario confidence interval is available.

| Scenario | n | exdiv | exk10 | exk30 | perk16c5 | planr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 26 | -0.37 / -3.85 | +1.98 / -3.85 | -0.36 / -3.85 | +2.35 / -7.69 | +0.02 / -7.69 |
| audio | 30 | +3.95 / +10.00 | +8.72 / +3.33 | +18.97 / +10.00 | +1.89 / -3.33 | +15.97 / +3.33 |
| calendar | 42 | -1.26 / +0.00 | +6.03 / +0.00 | +3.82 / +0.00 | -0.71 / +0.00 | +3.92 / +0.00 |
| cooking | 31 | -2.07 / +0.00 | +1.67 / +6.45 | -5.03 / +3.23 | -1.37 / +6.45 | -3.18 / +3.23 |
| datetime | 39 | +2.63 / +0.00 | +1.79 / -2.56 | +2.68 / +0.00 | -0.24 / +2.56 | +4.35 / -2.56 |
| email | 33 | -5.94 / -3.03 | -6.15 / +0.00 | +2.87 / +0.00 | +3.99 / +3.03 | +4.01 / -3.03 |
| general | 42 | +1.39 / -2.38 | +1.39 / -9.52 | -0.35 / -7.14 | -5.19 / -11.90 | -2.71 / -11.90 |
| iot | 33 | +1.99 / +0.00 | +0.77 / -3.03 | +2.48 / +0.00 | +0.57 / +0.00 | +5.93 / +0.00 |
| lists | 37 | -6.78 / -2.70 | -5.32 / -5.41 | -6.68 / -2.70 | -2.94 / -5.41 | -4.79 / -2.70 |
| music | 27 | +2.61 / +3.70 | +3.66 / +0.00 | +6.14 / +0.00 | +0.79 / +3.70 | +0.79 / +0.00 |
| news | 36 | +3.96 / +2.78 | +6.22 / +2.78 | +5.31 / +5.56 | -3.57 / -2.78 | +3.48 / +2.78 |
| play | 37 | -0.32 / +2.70 | +3.21 / +2.70 | +2.30 / +0.00 | -1.04 / +10.81 | +0.27 / +2.70 |
| qa | 38 | +2.73 / +0.00 | -2.08 / -2.63 | +4.82 / +2.63 | +3.04 / +5.26 | +6.21 / +2.63 |
| recommendation | 29 | +6.14 / +0.00 | +5.36 / +0.00 | +1.73 / +0.00 | +7.09 / +0.00 | +5.85 / +0.00 |
| social | 35 | +0.45 / +0.00 | +4.11 / +2.86 | +3.91 / +0.00 | +0.12 / +5.71 | +1.76 / -5.71 |
| takeaway | 37 | +0.02 / +0.00 | -0.10 / +0.00 | +2.64 / +0.00 | +1.78 / +2.70 | -0.45 / -2.70 |
| transport | 32 | -2.56 / +0.00 | -0.30 / -3.12 | +1.40 / +0.00 | -0.36 / -3.12 | -0.43 / +0.00 |
| weather | 41 | -0.78 / +0.00 | +0.32 / +0.00 | -1.85 / -2.44 | -0.72 / +0.00 | -0.96 / +0.00 |

Natural mixture is the pooled full-roster difference; equal scenario is the unweighted mean of the 18 per-scenario differences.

| Weighting | exdiv | exk10 | exk30 | perk16c5 | planr |
| --- | ---: | ---: | ---: | ---: | ---: |
| natural_mixture | +0.17 / +0.32 | +1.94 / -0.80 | +1.95 / +0.16 | +0.16 / +0.32 | +1.87 / -1.28 |
| equal_scenario | +0.32 / +0.40 | +1.74 / -0.67 | +2.49 / +0.29 | +0.30 / +0.33 | +2.23 / -1.20 |

## Actual inputs and cost per 625-row arm

| Arm | Generation contacts | Contacts/row | Prompt tokens/row | Completion tokens/row | GPU-h | Repeated speech seconds | Tool calls | Exemplars/row | Slot cards/row | Compacted rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| plan | 2590 | 4.144 | 35049.2 | 261.6 | 1.059 | 11314.6 | 0 | 20.00 | 12.21 | 0 |
| exdiv | 2598 | 4.157 | 33797.9 | 266.3 | 1.000 | 11317.2 | 0 | 10.29 | 12.10 | 0 |
| exk10 | 2576 | 4.122 | 33660.5 | 260.9 | 1.002 | 11283.1 | 0 | 10.00 | 12.30 | 0 |
| exk30 | 2572 | 4.115 | 35746.4 | 257.5 | 1.044 | 11222.9 | 0 | 30.00 | 12.17 | 0 |
| perk16c5 | 2576 | 4.122 | 39761.1 | 263.8 | 1.147 | 11269.3 | 0 | 20.00 | 12.67 | 0 |
| planr | 2591 | 4.146 | 34913.6 | 259.0 | 1.029 | 11327.3 | 0 | 20.00 | 12.13 | 0 |

Candidate cards per row equal the mean widths in the coverage table. Source files: `stop.json`, `own-null.json`, `variant-contrasts.json`, `perception-coverage.json`, `slot-type-decomposition.json`, `per-scenario.json`, `cost.json`.

## Root interpretation and action catalog

Recorded after the registered complete-family read. Preserve the registered
contrasts above. The following comparison with PLANR is a post-read descriptive
sensitivity, not a new preregistered efficacy test.

1. K10 and K30 improve pooled SLU-F1 by 1.9373 and 1.9540 pp versus PLAN,
   while the unchanged PLANR improves by 1.8689 pp. Their point differences
   versus PLANR are only 0.0684 and 0.0851 pp. No interval for either PLANR
   contrast has been computed here. The original positive PLAN contrasts
   alone therefore do not establish a repeatable optimization benefit.
   Keep both executable actions for matched-prefix VAR-2 discovery; do not
   promote either as an effective learned system action.
2. EX-DIV supplies 10.29 exemplars on average versus PLAN's 20. Its small
   unsupported pooled gain cannot isolate diversity from supply count.
   Use K10 and actual supplied counts to interpret it. This family provides
   no reason to deploy diversity selection yet.
3. K16/C5 increases candidate coverage from 77.76% to 80.32%, but final
   intent moves only 0.32 pp and pooled SLU-F1 only 0.16 pp. It changes both
   Perception knowledge volume and allowed candidate width. Only 5/625
   rows have the correct intent at positions four or five; that 0.8 pp
   is not the causal effect of widening. The final arm also ran across a
   documented serving-process boundary after the earlier queue stopped.
   Coverage remains far below the owner's 95% priority. Do not mechanically
   increase N again without analyzing uncovered intent pairs and evidence.
4. Empty-entity behavior is a large remaining optimization surface:
   191/625 rows have no gold entities, and 108-119 of them receive entities
   across these arms (56.54%-62.30%). Even K30's lowest observed count
   is descriptive and not a proven improvement. Test explicit empty-set
   representation through the separately registered F10 path, and use
   official-count feedback that penalizes false positives on empty rows.
5. Gold intent in the candidate set is necessary for some downstream
   choices but does not guarantee correct selection. In K16/C5 there are
   62 covered-intent failures and 119 uncovered-intent failures in the
   registered exclusive taxonomy. This supports retaining both research
   lines: better proposal coverage and better evidence-driven selection.
6. Prompt-token totals are summed across contacts, not one request's
   context-window occupancy. GPU-hour entries are the report's measured
   cost convention, not a promise of wall-clock completion time.

Action status: default20 remains the fallback; K10, K30 and EX-DIV remain
executable discovery actions for VAR-2, not qualified winners. K16/C5 stays
a combined Perception intervention that VAR-2 cannot express. F10 changes
knowledge representation and therefore uses a separate complete-system cell.

The original reader's pooled CI95 half-width (1.4739 pp) and the root's
prospective CI90 half-width (1.2413 pp) are different interval summaries.
Neither is a universal detection guarantee. In particular, a pooled-F1
margin must not be used as evidence for mean row-F1 or exact span-F1.
The in-sample state-action winner table uses the old row-F1 feedback and
the same rows to choose winners; it is not a frozen learned policy or
evidence of out-of-sample policy improvement.

Proceed in the owner-approved order: finish VERIFY-1 selection capability;
measure VAR-2 same-prefix supply actions and F10 empty-set representation;
validate any promising action through the complete four-node system; then
learn and freeze a finite action-selection policy, evaluated against both
the locked system and the best fixed action. Keep all exposed-roster
findings explicitly labeled construction/regression evidence.
