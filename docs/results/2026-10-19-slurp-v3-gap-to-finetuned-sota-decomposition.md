# SLURP v3.0 gap decomposition against the fine-tuned tiers (owner ruling 337): where the errors are, oracle ceilings, ranked levers

Model-free analyst read, 2026-10-18. It is read-only on the study repo and the data root. It contacted no model, server or GPU and ran no scorer
subprocess: the re-scoring uses the in-repo port, which reproduces the sealed per-sample counts on 2,080 of 2,080 rows.
No test row was opened. The test numbers below are aggregates quoted from the notes.
No utterance, transcript, filler, model output or reasoning text was printed or persisted. Only counts, rates, pp and label/type names appear.
**Development numbers, never a test claim (decisions 28 and 86). Diagnostic only: it gates nothing and admits nothing.**

Files (scratchpad `gap/`):
- `gap_decomposition.py`: per-row classes, oracles and strata. Output: `gap-numbers.json`.
- `rank_conversion.py`: accuracy by the gold intent's shortlist rank. Output: `rank-conversion.json`.
- `multi_decode_ceiling.py`: vote and selection ceiling over 7 sealed Fold B decodes. Output: `multi-decode.json`.

## 0. Populations and the gap

| population | sealed source | n | SLU-F1 | intent |
| --- | --- | ---: | ---: | ---: |
| **DEV**: DEV-2000-ADDED, P3.1 lock arm | `SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-LOCK-V1` (devel gold) | 1,000 | 74.69 | 84.50 |
| **FB**: TRAIN Fold B, R2b delivering arm `budget-3072` | `SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-V1` (train gold) | 1,080 | 72.74 | 85.37 |
| v3.0 on the 3,010-row test sample (aggregate only) | successor-3 read | 3,010 | 73.05 | 86.33 |

Checks passed: SLU-F1 and intent are reproduced to the sealed reads; the re-scored counts match the sealed counts on 1,000/1,000 and 1,080/1,080 rows; the parsed intent agrees with the sealed exact flag on every row; forced-close status (trace COST `forced_close` stat) is known on every row.
On 3 of 1,080 FB rows the receipt's candidate list differs from the Perception state; the receipt was used.

Gap from the v3.0 test sample to each tier, in pp (SLU / intent):
- LauraGPT 73.45 / 87.87: **+0.40 / +1.54**
- SFT Qwen2-Audio-7B 76.75 / 88.13: **+3.70 / +1.80**
- UniverSLU-14 90.3 intent / 79.5 SLU: **+6.45 / +3.97**

Caveats on the comparison:
- The tiers are scored on the full test set; ours is a 3,010-row sample.
- Every "share of gap" below divides a DEV or FB oracle gain (pp) by the test gap. This assumes the pp transfer.

## 1. Where the errors are

### 1.1 Intent (Perception proposes 1-3 candidates from an 8-entry retrieved boundary block; the Solver decides)

| class | DEV rows (pp) | FB rows (pp) |
| --- | ---: | ---: |
| correct | 845 | 922 |
| **(a) gold absent from Perception's shortlist** | **121 (12.1)** | **118 (10.9)** |
| a1. gold was in the 8-entry block; Perception dropped it | 85 | 78 |
| a2. gold not in the block either (retrieval miss) | 36 | 40 |
| **(b) gold on the shortlist, Solver chose wrong** | **34 (3.4)** | **40 (3.7)** |
| b, Solver picked another shortlist member / went off the list | 27 / 7 | 33 / 7 |
| b, gold was at shortlist rank 1 / 2 / 3 | 12 / 17 / 5 | 19 / 17 / 4 |
| unparsed | 0 | 0 |

**78 % (DEV) and 75 % (FB) of intent errors are (a).**

Accuracy by the gold intent's position on the shortlist (`rank-conversion.json`):

| gold position | DEV rows | DEV accuracy | FB rows | FB accuracy |
| --- | ---: | ---: | ---: | ---: |
| sole candidate | 752 | 99.3 % | 785 | 99.2 % |
| rank 1 of 2-3 | 85 | 92 % | 116 | 89 % |
| rank 2-3 | 34 | 35 % | 51 | 59 % |
| off the list | 129 | 6.2 % | 128 | 7.8 % |

- Perception commits to a single candidate on 85 % (DEV) and 81 % (FB) of rows.
- When gold is in the block but Perception drops it, the Solver recovers it in 4-8 % of cases when gold sat at block rank 2-8, and in 22-25 % when it sat at rank 1.
- Of the (a) and (b) errors, 75 % (116 of 155 DEV, 118 of 158 FB) cross scenarios; they are not near-miss actions.

**The catch-all `general_quirky` carries 35 errors on each population (DEV 35 of 51 rows, FB 35 of 54).**
- That is 23 % of DEV and 22 % of FB intent errors.
- 32 (DEV) and 30 (FB) of those errors are off the shortlist.
- Its largest confusion is `qa_factoid` (11 DEV, 9 FB).

Other error owners:
- DEV: `calendar_query` 23/80, `qa_factoid` 20/67, `play_music` 15/99, `calendar_set` 10/107.
- FB (60 rows per scenario by design): the remaining errors are flat, 4-9 per intent.

### 1.2 Slots (entity items, `entity_items` taxonomy; SLU-F1 is the official word+char distance F1)

| class | DEV items | FB items | DEV SLU pp if this class alone were repaired | FB pp |
| --- | ---: | ---: | ---: | ---: |
| FP, false fill on an empty-gold row | 90 (on 80 of 314 empty rows) | 92 (on 81 of 392) | **+3.00** | **+3.20** |
| FP, extra slot on a non-empty row | 95 | 97 | +3.28 | +3.61 |
| FN, missed slot (MISSING) | 112 (38 rows predicted empty) | 112 (33 rows) | **+5.74** | **+6.22** |
| wrong value, FORMAT (canonical-equal) | 9 | 17 | +0.25 | +0.49 |
| wrong value, BOUNDARY (span contains or is contained) | 58 | 58 | +2.23 | +2.35 |
| wrong value, NEAR (normalised distance ≤ 0.4) | 53 | 59 | +1.79 | +2.05 |
| wrong value, WRONG-VALUE (same type, different value) | 41 | 32 | +2.38 | +2.14 |
| wrong type (23 of them same value, i.e. a pure type swap) | 44 | 39 | +3.77 | +3.58 |
| all items repaired | 502 | 506 | +25.31 (to 100) | +27.26 |

- Gold entities: DEV 1,027, FB 944. Predicted entities: 1,100 and 1,021.
- The largest single masses are **missed slots** and **false fills taken together** (FP total 185 and 189 items).
- Type swaps and boundary errors follow.

Slot types:

| class | DEV top types | FB top types |
| --- | --- | --- |
| MISSING | `date` 10, `event_name` 9, `player_setting` 8 | `date` 10, `media_type` 9, `event_name` 8 |
| SPURIOUS | `event_name` 22, `place_name` 20, `person` 17 | `place_name` 27, `event_name` 16, `person` 14 |
| NEAR | `person` 15 | `business_name` 12 |
| WRONG-TYPE | `time` 7 | `time` 5 |

### 1.3 Forced-close rows (either node hit the 3,072-token reasoning budget)

| population | rows with a forced close | intent on them | SLU-F1 on them | intent / SLU-F1 on natural rows |
| --- | ---: | ---: | ---: | ---: |
| DEV | 529 / 1,000 (Solver 457, Perception 174) | 79.4 | 69.7 | 90.2 / 82.4 |
| FB | 525 / 1,080 (Solver 433, Perception 199) | 80.6 | 66.9 | 89.9 / 81.1 |

- Forced-close rows hold 109 of 155 (DEV) and 102 of 158 (FB) intent errors, i.e. 70 % and 65 %.
- They hold 366 of 502 (DEV) and 362 of 506 (FB) slot items, i.e. 73 % and 72 %.
- They hold 67 of 90 and 69 of 92 empty-gold false fills.
- Rows where Perception forced a close are the worst: intent 66 % (DEV) and 69 % (FB).
- The relation is strongly confounded with difficulty. R2b doubled the Solver budget: forced closes fell only from 40.1 % to 37.8 %, and the score moved -0.81 SLU (no gain).
- So the forced close is a marker of hard rows more than a cause that budget can remove.

### 1.4 By scenario (DEV, n ≥ 48; SLU pp = gain if every slot item in that scenario were repaired)

| scenario | n | intent | off-shortlist / Solver-wrong errors | SLU-F1 | SLU pp at stake |
| --- | ---: | ---: | --- | ---: | ---: |
| calendar | 221 | 84.2 | 24 / 11 | 80.1 | 6.38 |
| play | 203 | 84.2 | 23 / 9 | 65.2 | 6.09 |
| qa | 157 | 79.6 | 27 / 5 | 72.3 | 3.25 (28 empty-gold false fills) |
| email | 96 | 91.7 | 7 / 1 | 67.2 | 2.13 |
| general | 62 | 43.5 | 32 / 3 | 49.9 | 0.97 |
| weather, transport, iot, lists | 48-65 | 92-98 | ≤ 3 / ≤ 2 | 74-83 | 0.5-1.2 each |

- On DEV, intent loss sits in general, qa, calendar and play, and SLU loss in calendar and play (their size).
- FB (60 rows per scenario): the weakest are general (intent 38.3), play, music and lists (SLU 59-64), with calendar, play, takeaway and transport carrying the most SLU pp (2.1-2.5 each).

## 2. Oracle ceilings (sealed data only; gains in pp over the population's own score)

95 % CIs are utterance-cluster bootstrap, 2,000 draws, seed 20261019. The share columns are the gain divided by the test gap to the tier: LauraGPT / SFT Qwen2-Audio / UniverSLU.

| oracle | DEV gain | FB gain | SLU share of gap (DEV gain) | intent share of gap (DEV gain) |
| --- | --- | --- | --- | --- |
| (i) intent perfect | intent +15.50; SLU 0 to +5.18, central **+3.18** | intent +14.63; SLU 0 to +5.50, central +3.16 | central 795 % / 86 % / 49 % | >1000 % / 861 % / 390 % |
| (ii) gold always on Perception's shortlist (rows with gold on the list, rescaled) | intent **+11.60** [+9.53, +13.72] → 96.10; SLU +2.46 [+1.58, +3.39] | intent +10.43 [+8.63, +12.17] → 95.80; SLU +2.23 | 615 % / 66 % / 38 % | 753 % / 644 % / 292 % |
| (ii-b) gold always in the 8-entry block (Perception unchanged) | intent +3.26 | intent +3.24 | n/a | 212 % / 181 % / 82 % |
| (iii) every empty-gold false fill removed | SLU **+3.00** [+2.30, +3.77] | SLU +3.20 [+2.50, +4.00] | 750 % / 81 % / 47 % | 0 |
| (iv) values normalised where type matches and spans overlap (FORMAT + BOUNDARY + NEAR) | SLU **+4.41** [+3.63, +5.21] | SLU +5.10 [+4.18, +6.04] | 1100 % / 119 % / 68 % | 0 |
| (v) forced-close rows at natural-row error rates | intent +5.73, SLU +7.71 | intent +4.54, SLU +8.41 | 1930 % / 208 % / 120 % | 372 % / 318 % / 144 % |
| (v-b) Solver forced-close rows only, intent | +3.16 | +3.50 | n/a | n/a |
| (iii) and (iv) jointly | SLU +7.79 → 82.48 | SLU +8.78 → 81.51 | 211 % / 121 % (FB 237 % / 136 %) | n/a |
| selection over 5 lock-like FB decodes (any arm correct) | n/a | intent +4.26 → 89.63; SLU best-of-5 → 80.62 (+7.9) | (FB) 213 % / 122 % | (FB) 277 % / 237 % / 107 % |

How each oracle was computed:
- **(i)** SLU-F1 does not read the intent label. The central figure rescales the wrong-intent rows to the correct-intent rows' F1; the upper end repairs every slot item on the wrong-intent rows.
- **(v)** It is confounded with row difficulty (see 1.3). It is an upper bound on any fix of "unterminated reasoning", not an estimate.
- **Selection** over the five FB decodes: `multi-decode.json`; arms R1 both-on, both-on-twin and perception-off; R2b budget-3072 and solver-6144.
  - Plurality vote over the five gives intent **85.74**, against the best single arm 85.74 and the delivering arm 85.37. The vote's selection value is nil.
  - On the 947 unanimous rows accuracy is 91.8 %; on the 133 split rows it is 42.9 %.

Reading the oracles:
- Every SLU oracle except (ii) clears the LauraGPT SLU gap on its own; LauraGPT is already within same-flight noise of us on SLU.
- Against SFT Qwen2-Audio, (iii), (iv) or (v) alone would cover 81-208 % of the SLU gap, and (ii) would cover 644 % of the intent gap.
- Against UniverSLU, no single slot oracle covers the 6.45 pp SLU gap. Only (iii) and (iv) jointly, or the confounded (v), do so.
- These are oracles. Section 3 asks how much of each a training-free method has actually converted.

## 3. Ranked levers (by plausible training-free headroom on SLU-F1 and intent)

Prior evidence is cited from `docs/results/` unless stated. "Measured" means a sealed or offline read.
Most closures were measured on the Instruct core; on the Thinking core, re-test only where marked.

| # | lever | error class attacked | oracle mass (this read) | measured conversion so far | status | plausible training-free gain |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | **False-fill suppression**: multi-sample support filter (n=5, s=2-3) plus an N1-gated upstream empty decision | FP, empty gold and extra slots | (iii) +3.0/+3.2; all FP +6.3/+6.8 | support filter +0.76 to +1.40 (`2026-10-11-...ver1...`, `2026-09-24-...sample-aggregation...`); N1-gated empty +0.75/+0.98 (`2026-10-10-...nx-r6-upstream-empty...`); explicit empty rule inert (`2026-09-28-...empty-entity...`) | open; untested on the Thinking core. Needs 5-6 contacts/row (support filter), or 0 (N1 rule, judged "not worth flying" at the 1.5 bar) | **+1.0 to +2.0 SLU**; intent 0 |
| 2 | **Solver reasoning termination** (NX-T R3 instruction template; R4 decoding policy) | forced-close rows: 70 % of intent errors, 72 % of slot items | (v) SLU +7.7/+8.4, intent +4.5/+5.7, confounded | budget raise refuted (R2b -0.81 / -0.56); Solver thinking is load-bearing (R1 solver-off -7.11 SLU) | R3 and R4 registered and queued, not flown | 0 to +1.5 SLU, 0 to +1.0 intent (unmeasured; wide) |
| 3 | **Perception shortlist recall** (gold in the block but dropped: 85/78 rows; Perception commits to 1 candidate on 81-85 % of rows) | intent (a1) | (ii) intent +11.6/+10.4, SLU +2.5/+2.2 | all closed on Instruct: P-SV-1 contrast -0.19, P-SV-2 forced 3-list +0.37 gold-on-list, P-SV-3 depth 8→12 -1.39 (harm), P-SV-4 key -0.19; rank-2/3 conversion only 35-59 % (this read) | Perception-node levers CLOSED on Instruct; never re-tested on Thinking | 0 to +1.0 intent. A "widen when unsure" form on Thinking is the only untried shape; even perfect listing converts at 35-59 % at rank 2-3 |
| 4 | **Residual value normalisation / span repair** | wrong value: FORMAT, BOUNDARY, NEAR | (iv) +4.4/+5.1, of which FORMAT only +0.25/+0.49 | v4g already locked (+1.55 FB) and included in these numbers; core re-listen harmful (E4-1 -4.11); Whisper transcript oracle closed (E5 gold-span containment 0.75) | the deterministic part is nearly spent; BOUNDARY and NEAR need hearing | +0.3 to +0.8 SLU |
| 5 | **Type contract check** (type swap at the same value: 23 items each) | wrong type | +3.8/+3.6 (all wrong types) | v4g carries a type-by-intent table; no dedicated column | partly covered; no read | +0.3 to +0.8 SLU |
| 6 | **Catch-all `general_quirky` policy** | intent (a), 35 errors per population | about 3.5 pp intent (DEV, if all fixed) | label ceiling 100 % (`2026-09-26-...label-ceiling-audit`), but the class is semantic residue | no dedicated lever tested | 0 to +1.0 intent, high regression risk on `qa_*` |
| 7 | **Solver choice within the shortlist** | intent (b) | +3.4/+3.7 intent | Solver decision oracle: best rule +0.12 pp, conversion 0.008-0.185 (`2026-09-30-...solver-decision-oracle`); vote over 5 decodes +0.37 (this read); TF-0 routing +0.42; VER-1 not confirmed; ACE +0.27; GEPA neutral | CLOSED by measurement | 0 to +0.5 intent |
| 8 | **Retrieval recall** (gold not in the block) | intent (a2), 36/40 rows | (ii-b) +3.3 intent | key recall closed: K1-K8 at most +0.4 pp presence (`2026-09-30-...retrieval-key-recall`), P-SV-4 refuted | CLOSED | about 0 |
| 9 | **Missed-slot proposal** | FN | +5.7/+6.2 | S2/S2a1: recall ceiling 0.086, perfect ranker 0.47 (`2026-09-30-...s2a1...`); S1 S2+S5 below 1.5 pp; E5 "transcript proposes" ceiling +8.21 needs a stronger ASR and a transcript path the owner barred | CLOSED with current components | about 0 (only a stronger perception front-end could move it) |

**Reachable ceiling of this method class (estimate, test scale; the sum of the plausible column, with overlap discounted).**
- SLU-F1 gains:
  - levers 1, 4 and 5 add +1.6 to +3.6;
  - lever 2 adds 0 to +1.5;
  - levers 1 and 2 share the same forced-close FP rows, so the total is discounted by about 25 %.
  - **SLU-F1 ≈ 74.5-77.0 (central about 75.5).**
- Intent gains: lever 3 adds 0 to +1.0 and levers 2, 6 and 7 add 0 to +1.5. **Intent ≈ 86.3-88.0 (central about 87.0).**

What that means for each tier:
- **LauraGPT (73.45 / 87.87).** SLU is already matched within noise. Intent is reachable only at the optimistic end, and only if lever 3 works on the Thinking core.
- **SFT Qwen2-Audio-7B (76.75 / 88.13).** SLU sits at the top of the reachable band, and only if levers 1 and 2 both convert at the high end. Intent is just above the band.
- **UniverSLU-14 (79.5 / 90.3).** **Below this method class's ceiling on both metrics.**
  - Closing 6.45 pp of SLU would need about 83 % of the joint (iii)+(iv) oracle mass. Measured conversions of FP and value oracles run at 10-45 %.
  - Closing 3.97 pp of intent would need about a third of the shortlist-recall oracle (ii). Every Perception and retrieval lever that attacked it has been closed by measurement.

The binding constraints are structural:
- **Intent.** A single confident wrong Perception candidate causes 75-78 % of intent errors. The Solver rarely overrides it: 6-8 % accuracy when gold is off the list.
- **SLU.** Missed slots, the largest mass, have no training-free proposer: the recall ceiling is 0.086.

## 4. Limits of this read

- DEV and FB only, as required. Test-sample shares assume the pp transfer: DEV sits +1.6 SLU / -1.8 intent from test, FB -0.3 / -1.0.
- The oracles are upper bounds or rescalings. (i)-central, (ii) and (v) assume the repaired rows behave like the rows that are already right. Those rows are easier, so the oracles are optimistic.
- Repair oracles for single classes overlap and do not add up. Only the joint (iii)+(iv) figure was computed directly.
- The "plausible" column is the analyst's judgement from measured conversions, mostly on the Instruct core. It is not a measurement.
- Reasoning content was not read (ruling 286); forced close is the stored stat.
- The tiers are full-test numbers from `docs/readiness/2026-10-12-sota-comparator-table-v1.md`. That table claims no training-free SOTA; no published training-free SLU-F1 comparator exists.
