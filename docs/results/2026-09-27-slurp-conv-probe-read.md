# Cell CONV read: m = 32 of 70 newly delivered rows moved from a wrong intent to the gold intent (DESCRIPTIVE)

Read 2026-09-27 by Fable 5.1 with `scripts/analysis/slurp_conv_probe_read.py` (sha256
`8866a52aceb4b9dc2778824da8fea752955ac0cb64077c336a698502b0948b3d`), following the registered recipe
`slurp-stage3-conv-fold-a-70-conditional-rate-v1`
(`docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1/analysis-recipe-v1.json`) step by step.
Analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-CONV-FOLD-A-70-CONDITIONAL-RATE-V1`
(`read-v1.json` sha256 `c1aa690c93ed1600ee08fefb35e5944c995190a167eacb82f2c0cd8a63af7ce8`, `read-v1.md`
sha256 `f919fba5487ebfc6d8858eb28199b571cfc46aa60e5fa8d4c6c22456345d552f`; byte-reproducible apart from
`generated_at_utc`). Model-free: zero model, tokenizer, encoder, embedder, scorer, llama-server and
network contacts; the official scorer ran once at finalize and its sealed per-sample output is read,
never re-run; nothing under the sealed run directory was opened for writing. No utterance text,
transcript, gold label string, intent name, value id or delivered answer is printed or persisted here
or in the receipt.

Status: **DESCRIPTIVE** (a conditional rate on a gold-selected TRAIN roster; no admission, no pooled or
roster-level claim, no superiority or generalisation claim; the cell decides nothing).

## 1. What flew

Run `SAEA-SLURP-STAGE3-CONV-FOLD-A-70-V1`, attempt
`attempt-slurp-native-stage3-conv-fold-a-70-generation-v1`, flight commit `9255ac71`, study tree clean
at seal: the registered AGREE treatment (`w_agree` 1.0, `k` 60, `fuse_coverage` m 8 / c 1 / top_l 8) on
the 70 TRAIN Fold A rows of the committed roster (`roster-derivation-v1.json` sha256
`865d3fe0432bc8f18e9d19b26636e1560bcc82f2d7a9fedae32eadb5cb208dba`, id-list sha256
`5920bd6c99d1d5935881c0ca85c8454c7ec8eed096d950b7242c0ec7d8fbf73b`, split identity
`57c6f278d8ab35dafa0f1183938c13b6084a4f3d9d9438cfb3e55bbf73ff335c`), treatment only, read against the
sealed PLAN comparator `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` /
`attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1` (never re-flown; its official
per-sample score sha256 `9f3047fa77a868cb6c8cd72827c0358996288b12cb976a682a960bde5eda707c`, outputs
`2dcaa925ab7dad77e5938002d5606189ff7f644a94ade5b7265060e94d3ae17f`). Manifest COMPLETED, attempt
FINALIZED, 70 of 70 rows admitted and parsed. Sealed hashes: run manifest
`d5489a986fcac77e3e68c3c1fc23663e9c076fba0c2a56abe5314e4fdb57a6ed`, outputs
`8c606864f00df2532fbd269a202ce398063f7db45eadce479c2314f3dac9c33f`, scores
`faa78b190676d2b4ae00156e76b9ac40fb6611edf8c268ec4e0a838748c72667`, phase artefact
`4ef98a39429663da52704ab1d03c0226d0dafe166342af084204cb62a72f8268`, flight receipts
`80d2898753b156fc136401035e3dcc4e5652a0c43cc23f6055eb1b65e4280392`, official score-batch result
`b78c08d99f6512ec5b2570acae80217b01a9e72789ba119bc85cde06543a1cd2` (one job, `succeeded`, 66.8 s,
never sharded).

## 2. The recipe's gates

| step | gate | result |
| --- | --- | --- |
| 1 | manifest COMPLETED at 70 rows; the sealed id list hashes to the committed roster's id-list sha256 (compared as a hash, not a count) | held |
| 2 | the flown Perception consumption delivered the row's own gold intent boundary value id on all 70 rows (the offline derivation predicted 70) | **held, 70 / 70** |
| 3 | one official complete score over the complete manifest; per-sample `scenario_action_exact` read from the seal | held; the per-sample mean reproduces the official intent accuracy to 1e-9 |
| 4 | the comparator's per-row verdict from the bad-case bank (sha256 `26231b86b86f35251fed2b7d7c59bf33e8806b5ef71739b74bf9d5bc2b8a3ccf`; all 70 rows `INTENT-UNCOVERED`) and from the sealed PLAN official score agree on every row | held, 0 disagreements |
| 5 | reverse count r | 0 (zero by construction on this roster; confirmed) |

Delivery detail, counts only: every row received exactly 8 boundary entries; the consumption tracer
marks the gold entry `use` on 42 rows and `ignore` on 28.

## 3. The number

| quantity | value |
| --- | ---: |
| m, rows moved from a wrong intent to the gold intent | **32 of 70** |
| P(correct given newly delivered) | **45.71 %** |
| Wilson score CI95 | **[34.57 %, 57.30 %]** |
| Clopper-Pearson exact CI95 | [33.74 %, 58.06 %] |

One binomial proportion over independent rows; no bootstrap, because the estimand is not a paired
difference of pooled metrics.

## 4. Four-way row split and within-pair identity

| transition, comparator to treatment | rows |
| --- | ---: |
| wrong to gold (m) | 32 |
| gold to wrong (r) | 0 |
| unchanged wrong: the same wrong intent | 22 |
| a different wrong intent | 16 |

Of the 38 rows that stay wrong, 13 deliver an answer byte-identical to the comparator's, 16 deliver a
different wrong intent and 9 deliver the same wrong intent in different bytes (entity content differs).
On the 22 rows whose intent did not change, **13 of 22 (59.1 %)** delivered answers are byte-identical to
the comparator's (the raw response text sha256 is identical on the same 13). This is not an A/A figure:
the treatment changes the Perception supply on every row by construction (the gold entry is newly
delivered) and the two arms are different flights, so it is reported as context beside the ROLL-AA
within-flight null (91.5 % byte-identical at np4, 0 intent flips in 200), not against it. The
deliver-normaliser changed 7 probe rows; 0 probe rows were unparsed; the parsed probe intent agrees
with the scorer's exact flag on all 70 rows; the bank's recorded comparator intent agrees with the
parsed comparator output on all 70.

## 5. Spend and dispositions

| quantity | value |
| --- | ---: |
| generation contacts used / cap | **289 / 770** (4.13 per row; 67 rows at 4 contacts, 3 rows at 7) |
| speech audio seconds used / cap | 707.123 / 1,899 (roster 172.605 s, replayed 4.10x) |
| GPU, monitored active | **7.43 min** (0.1239 GPU-h) inside an 8.73 min window, 2026-09-26 23:55:45 to 2026-09-27 00:04:34 UTC; mean utilisation 73.3 %, parked fraction 0.149, mean 79.2 W; cap 1.0 GPU-h |
| prompt / completion tokens | 2,723,441 / 18,565 |
| tool calls | 0 |
| dispositions | finite_completion 0, revision_limit 0, planner_action_illegal 0, ReAct exhaustion 0, context compaction 0 contacts; Planner routes ACCEPT 70 and REVISE 3 (three rows took one revision: 7 role visits instead of 4) |
| official scoring | one complete job at finalize, 66.8 s |
| FIT identity | `SAEA-SLURP-STAGE3-CONV-FOLD-A-70-FIT-V1` opened no attempt and no run directory; the 289 native contact-fit receipts (all `tokenizer` class, 0 compactions) sit inside the generation attempt, against the 3,080 FIT endpoint cap |

The registration expected about 352 contacts and about 0.24 GPU-h; realized 289 and 0.12.

## 6. The re-declaration arithmetic, stated and not applied

The AGREE arm's declared expectation is a product of a measured delivery gain (70 newly delivered
`INTENT-UNCOVERED` rows of TRAIN Fold A, 0 lost) and a persuasion factor that was unmeasured; this cell
measures that factor as 32 / 70. The re-declaration rule registered by the parent package is
m x 0.041615 pp SLU-F1 and m x 0.092615 pp intent accuracy (equivalently the 2.9131 / 6.4831 pp ceilings
x m/70), against the arm's 2.5 pp bar at n = 1,080.

| framing | re-declared expectation | rows needed to clear the bar | m = 32 |
| --- | ---: | ---: | --- |
| intent accuracy primary, official SLU-F1 as the non-inferiority guard (owner decision 133) | **2.9637 pp intent** | **27** | **above: 32 >= 27, by 5 rows** |
| official SLU-F1 primary (the framing decision 133 retired for this mechanism) | 1.3317 pp SLU-F1 | 61 | below: 32 < 61 |

The CI95 in rows: Wilson [24.2, 40.1], so the interval spans the 27-row line; the point estimate is
above it and the lower bound is below it. The prior the coordinator asked for: 86 of the 191
intent-wrong Fold A rows already received the gold intent's boundary entry in the sealed comparator and
were wrong anyway; against that observable zero, 32 of 70 newly delivered rows converting is the first
direct measurement of the factor.

This is a CONDITIONAL rate on a roster selected with gold, offline: it is not a pooled effect, not a
roster-level claim, and it cannot see harm on rows the comparator already gets right. Whether the AGREE
arm is re-declared as a benefit claim, flown as a no-harm base item under decision 127, or closed is the
coordinator's call pending the owner's answer; this note does not recommend one.

## 7. Records

- `docs/exposure-ledger.md`: rows `SAEA-SLURP-STAGE3-CONV-FOLD-A-70-V1` and
  `SAEA-SLURP-STAGE3-CONV-FOLD-A-70-FIT-V1` flipped to consumed with the sealed facts above; no other row
  touched.
- `docs/results/stage2-results-ledger.md` and `.json`: a DESCRIPTIVE entry for cell CONV (`SLURP-CONV`,
  tally `instrument`).
- Machine receipt `read-v1.json` under the analysis root, sha256 as above.
- Gates: the seven offline gates (`finite_completion_policy_check`, `results_ledger_check`,
  `harness_admission_check`, `engineering_base_check`, `tool_catalog_check`,
  `stage3_algorithm_label_check`, `stage3_effect_floor_check`) pass in the read worktree with these
  records applied (`results_ledger_check` PASS: 85 rows, 130 run ids registered and closed, the
  status word re-parsed from this note's first line); `bash scripts/flights/batch/main_gates_generic.sh`
  on the main checkout exits 0. `handoff_freshness_check` reports `stale-vs-results` against the
  standing handoff's stamp `2026-09-26T19:30:57Z`; refreshing that file is the coordinator's step at
  landing, not this read's.
