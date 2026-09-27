# Cell AGREE read: intent +3.33 pp CI95 [+1.57, +5.09] and official SLU-F1 +1.85 pp [+0.23, +3.47] against the in-chain A/A on TRAIN Fold A (ADMITTED on Fold A by the registered rule, pending fresh-roster replication)

Read 2026-09-27 by Claude Opus 5.5 (worktree `/home/chao/saea-worktrees/fable-agreerec`, branch
`fable/agreerec`). The registered paired read (READ row `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-PAIRED-ANALYSIS-V1`,
countersigned at master `c2623782` after the seal and before any score was read; recipe
`slurp-stage3-agree-w1-fold-a-paired-analysis-v1`) was executed by the coordinator with
`scripts/flights/agree/agree_read.sh` -> `scripts/analysis/slurp_paired_roster_read.py` (sha256
`90831272906e0b149c0ef70dca39130bfa7a8190f615cb7077d6c572ffb1faac`): seed 20260926, 10,000 draws, the row
as the resampling unit (cluster key `sample_id`), TRAIN gold through `slurp-slu-official-train`. Outputs
under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-PAIRED-ANALYSIS-V1/`: `vs-aa/` (gating)
and `vs-plan/` (context). The recipe's `reported_beside_every_verdict` quantities the paired driver does not
compute were computed by `scripts/analysis/slurp_agree_beside_read.py` (sha256
`d8cab4c28d32263ee541311c7e5b4c4f1a6dda5f1cf059a34662ae7ad6258d97`) into a NEW sibling directory
`beside/` of the same analysis root (`beside-v1.json` sha256
`7742da3376e4a24dcfe676832e8589ba3ed4db3a05bb191400de63707afb2332`, `beside-v1.md` sha256
`756aecf5d067d34fdc272a1540a845f1cc62ef78e6f4472961b12bb092d71e4a`); nothing under `runs/`, `vs-aa/` or
`vs-plan/` was opened for writing. Model-free throughout: zero model, tokenizer, encoder, embedder, scorer,
server and network contacts; the official scorer ran once per arm at finalize and its sealed per-sample
output is read, never re-run. No utterance text, transcript, gold label string, intent name, value id or
delivered answer is printed or persisted here or in the receipts.

## 0. Status, by the rule the package registered

The decision rule is fixed in `docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1/protocol-registered-v1.json`
(`decision_rule_fixed_here`) and the preregistration section "Decision rule": **NEUTRAL** when both guards
are non-inferior at the plan's own null (CI95 lower bound of the paired official pooled SLU-F1 delta above
-h_SLU = -1.2485 and of the intent delta above -h_intent = -0.9943, both against the IN-CHAIN A/A);
**ADMITTED** when NEUTRAL and the SLU CI95 lower bound is above zero against the in-chain A/A; **HARMFUL** on a
measured loss on either guard. Owner decisions 133 and 143 made intent accuracy the primary metric for this
mechanism and official SLU-F1 its non-inferiority guard; the registered `stage3_measurement` block declares
`claims_benefit: true`, expected 2.96 pp intent against the 2.5 pp cross-flight floor at n = 1,080.

| condition, against the in-chain A/A | measured | held |
| --- | --- | --- |
| official pooled SLU-F1 CI95 lower bound > -1.2485 (guard) | +0.23 | yes |
| intent CI95 lower bound > -0.9943 (guard) | +1.57 | yes |
| official pooled SLU-F1 CI95 lower bound > 0 (the registered ADMITTED clause) | +0.23 | yes |
| intent CI95 lower bound > 0 (the primary under decision 133) | +1.57 | yes |

**Fold-A verdict word: ADMITTED, pending replication.** Under owner decisions 115 and 127 this is a
SYSTEM-LEVEL benefit claim, which additionally needs replication on a fresh roster and is never final on
Fold A alone; nothing here is a disposition. The disposition is taken with the owner in conversation
(decision 139).

## 1. What flew

One campaign chain on session `serving-slurp-native-candidate-five-train-a-np4-v1` (np4 x 24,576, max 512),
flight commit `05e8053a` (`05e8053a8c5b2d7a23e87b4eba38ca08a8da5cf5`), study tree clean at seal
(`study_repo_dirt` empty). The two arms differ in `w_agree` alone (A/A 0.0, arm 1.0; both at recall width
k 60, delivered width 8, fuse m 8 / c 1 / top_l 8).

| run | window (UTC) | rows | contacts / cap | speech s / cap | GPU-active | state |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1` | 08:18:44 - 08:19:24 | 4 | 16 / 44 | 42.382 / 117 | 10.8 s | manifest COMPLETED, attempt OPENED (unscored by registration) |
| `SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1` | 08:21:53 - 10:14:17 | 1,080 | 4,405 / 11,880 | 12,571.195 / 33,930 | 103.86 min = 1.7309 GPU-h | FINALIZED, scored once (354.0 s) |
| `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` | 10:16:16 - 12:18:01 | 1,080 | 4,385 / 11,880 | 12,518.316 / 33,930 | 112.89 min = 1.8816 GPU-h | FINALIZED, scored once (388.6 s) |

Sealed hashes (sha256):

| artefact | A/A | arm |
| --- | --- | --- |
| run manifest | `a352370aaa4d4ae167f5e2d80f09f287eb2d67443eb6ed2353dd2899360dbb50` | `1cd3a765b95e01f2643a1bbb59a231386a4081c9a642dfb621200aba3d22252f` |
| outputs | `453a9a49340b578d04e2c9833893a285e3b929e8a9008296081e8f54ce551b61` | `6a4256e09278722518236912701e890369f70e1808b664118a4c6a87a983d4c1` |
| scores | `66cb7ab22bc94fa083e6c5289feb25354c26d4f125bb4acaa80431d636e4f444` | `01db05fa57787a0bc3ec679848610549c7581e76df3ea1d67a830f63f0626a1b` |
| phase artefact | `26e964aabc141e0a11dd0797e71b750f78652d8ae176dd392c51a3830a2e1c7b` | `783299f156269acbf11a162e37d788e92987252e3a3a4204c8e82031046c27d1` |
| generation manifest | `d2f424c528771f97f0c268d21d21951d04d291aad61d413ae76567723e476bd0` | `90520489c672e5056e55171bd9ac2e3f7871c4b1a272bf74ed3d4f1df7d385ea` |
| flight receipts | `1fcda0305757fa6cd96efe3c611b544795ccfcc2c6997836fb1e62044cf82df7` | `051bd72d9e6fe8347b707fb4d67158269a07cdea66d5fbfdc87f1ee981ff1193` |
| official score-batch result | `ccd793a8208ed84539c27d6dc28eeca6eae17f5d309d005b0e49898544d1b323` | `599af0a98661472ae71df23f1ec9fa09615fbc77beb69c973e4a7c8f472ba06e` |
| prepared first-phase supply as flown | `f03e40aa...` (`phase-supply-v2.json`, the registered bytes) | `be70d4d0...` (`phase-supply-v2.json`, the registered bytes) |

The smoke's run manifest is `7a48fe53254765a361de2aedfe53a610e45105c9f8a58f33ea9917f56cdf4a0e`. The three FIT
identities opened no attempt and no run directory; their request-fit receipts (tokenizer class, four endpoint
contacts each: `/props`, `/apply-template`, `/tokenize` x2) sit under `prepared/<FIT run id>/<fit attempt>/`:
4,405 receipts (17,620 endpoint contacts of the 47,520 registered) for the A/A FIT, 4,385 (17,540 of 47,520)
for the arm FIT, 16 (64 of 176) for the smoke FIT.

## 2. Stop and structural gates

| gate | A/A | arm |
| --- | --- | --- |
| stop stage (manifest COMPLETED, attempt FINALIZED, one complete official job, the official pooled micro SLU-F1 recomputed from the per-sample count fields) | PASSED; diff 2.2e-16 | PASSED; diff 0.0 |
| rows admitted / parsed | 1,080 / 1,079 | 1,080 / 1,079 |
| tool calls | 0 | 0 |
| context-fit receipts / compactions | 4,405 / 0 | 4,385 / 0 |
| finite-completion rows (two role visits) | 11 | 4 |
| planner_action_illegal rows | 0 | 0 |
| Planner routes ACCEPT / REVISE; revisions executed | 1,065 / 36; 32 | 1,075 / 24; 23 |
| deliver-normaliser changed rows | 94 | 108 |
| boundary entries per row | 8 on 1,076 rows (7, 5, 3, 1 on one row each) | identical histogram |
| flown boundary set equals the cell's own prepared supply | 1,080 / 1,080 | 1,080 / 1,080 |

The beside read re-derived the paired driver's pooled SLU-F1 and intent for both arms to 1e-9 before
computing anything else.

## 3. The contrasts

Gating: the arm against its in-chain A/A (`vs-aa/`, README sha256
`fc718624ac76286f3bdaf358ab3c64c8a373644e0d02821dc08bf1b08adf57be`, `score-contrasts.json`
`bd677b098f91a92cc679fe2224ae7c0eeba4eb69cdb70d27095d5de4ef2046f3`, verdict.json
`6c7dd075991460d698d6ba507b8385817501793ee2601b1239980b6037de88a7`).

| metric | A/A | arm | delta pp | CI95 pp | saves / harms | McNemar p |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| **intent (scenario_action_exact), primary** | 82.50 | 85.83 | **+3.33** | **[+1.57, +5.09]** | 67 / 31 | 0.000355 |
| scenario | 87.50 | 89.63 | +2.13 | [+0.65, +3.70] | 47 / 24 | 0.008555 |
| action | 83.70 | 86.57 | +2.87 | [+1.11, +4.63] | 63 / 32 | 0.001924 |
| **official pooled SLU-F1, guard** | 63.31 | 65.16 | **+1.85** | **[+0.23, +3.47]** | -- | -- |
| official pooled span-F1 | 53.18 | 54.43 | +1.26 | [-0.62, +3.15] | -- | -- |
| per-row SLU-F1 | 41.88 | 43.68 | +1.79 | [+0.41, +3.15] | 77 / 60 | 0.171 |
| per-row slot exact F1 | 34.38 | 35.61 | +1.23 | [-0.21, +2.66] | 57 / 47 | 0.378 |

Per channel (descriptive, unclustered): intent +3.63 headset (523 rows, 29 / 10) and +3.05 far-field
(557 rows, 38 / 21); SLU per row +1.24 headset, +2.31 far-field.

Context only: the arm against the sealed PLAN arm (`vs-plan/`, README sha256
`ca00e292a9eeee8ce530607162a8f6a2f954bc83ae69ff3a63a3c0a8af034e83`): intent 82.22 -> 85.83, **+3.61 pp
[+1.76, +5.46]** (72 / 33, p 0.000178); official SLU-F1 63.63 -> 65.16, **+1.53 pp [-0.21, +3.29]**. This is
never the gating contrast.

Against the design's own figures: the point estimate +3.33 pp intent is above the declared expectation of
2.96 pp and above the 2.5 pp cross-flight floor at n = 1,080; the CI95 lower bound (+1.57) is below that
floor. The floor is a statement about what this design can see, not a clause of the decision rule.

## 4. Per-scenario tables (both weightings)

The stratum is the Fold A roster receipt's own per-item `stratum`
(`docs/receipts/rosters/slurp-evo-fold-a-v2.json`, sha256 `1fe7908c...`); 18 scenarios x 60 rows. Because
every stratum holds 60 rows, the equal-scenario intent delta equals the natural-mixture one exactly; the
pooled SLU-F1 does not, because micro-F1 weights rows by entity count. Descriptive; no per-scenario CI.

Arm against the in-chain A/A (gating):

| scenario | intent A/A | intent arm | delta | saves / harms | SLU A/A | SLU arm | delta |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| alarm | 90.00 | 93.33 | +3.33 | 4 / 2 | 73.64 | 72.86 | -0.78 |
| audio | 81.67 | 80.00 | -1.67 | 5 / 6 | 59.88 | 63.30 | +3.42 |
| calendar | 80.00 | 90.00 | +10.00 | 7 / 1 | 65.38 | 64.79 | -0.59 |
| cooking | 85.00 | 83.33 | -1.67 | 2 / 3 | 62.32 | 65.33 | +3.00 |
| datetime | 90.00 | 91.67 | +1.67 | 2 / 1 | 73.96 | 75.60 | +1.64 |
| email | 88.33 | 90.00 | +1.67 | 2 / 1 | 63.17 | 65.17 | +2.01 |
| general | 40.00 | 50.00 | +10.00 | 7 / 1 | 24.49 | 27.27 | +2.78 |
| iot | 85.00 | 83.33 | -1.67 | 1 / 2 | 65.39 | 69.33 | +3.94 |
| lists | 83.33 | 88.33 | +5.00 | 3 / 0 | 52.23 | 59.68 | +7.44 |
| music | 81.67 | 81.67 | +0.00 | 3 / 3 | 44.94 | 45.23 | +0.29 |
| news | 81.67 | 86.67 | +5.00 | 3 / 0 | 68.84 | 68.92 | +0.08 |
| play | 88.33 | 90.00 | +1.67 | 1 / 0 | 54.07 | 55.52 | +1.45 |
| qa | 75.00 | 88.33 | +13.33 | 9 / 1 | 59.45 | 64.11 | +4.66 |
| recommendation | 91.67 | 96.67 | +5.00 | 4 / 1 | 70.35 | 71.56 | +1.21 |
| social | 76.67 | 83.33 | +6.67 | 6 / 2 | 56.57 | 60.91 | +4.34 |
| takeaway | 85.00 | 85.00 | +0.00 | 4 / 4 | 59.44 | 64.09 | +4.65 |
| transport | 88.33 | 86.67 | -1.67 | 2 / 3 | 66.74 | 65.78 | -0.96 |
| weather | 93.33 | 96.67 | +3.33 | 2 / 0 | 77.10 | 75.36 | -1.75 |

| weighting | intent delta pp | official SLU-F1 delta pp |
| --- | ---: | ---: |
| natural mixture (pooled over all 1,080 rows) | +3.33 | +1.85 |
| equal scenario (unweighted mean of the 18 per-scenario deltas) | +3.33 | +2.05 |

Intent rises in 12 scenarios, falls in 4 (audio, cooking, iot, transport, each -1.67 = one net row) and is
flat in 2; SLU-F1 rises in 14 and falls in 4.

Arm against the sealed PLAN arm (context only): intent +3.61 in both weightings; SLU-F1 +1.53 natural,
+1.79 equal-scenario; intent up in 14 scenarios, down in 3 (cooking -1.67, iot -5.00, transport -1.67),
flat in 1 (takeaway); SLU-F1 up in 13, down in 5 (alarm -3.89, music -3.52, general -2.96, transport -0.90,
calendar -0.85).
The per-scenario rows are in `beside-v1.md`.

## 5. Delivery check and conversion

**Delivery** is read from the sealed Perception consumption records (`phases.json`): a row is delivered when
its own gold intent's boundary value id is among the boundary items the flown Perception received (the CONV
read's and the production replication's sealed-side definition). The gold intent per row comes from the
bad-case bank (`analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl`, sha256 `26231b86...`, 1,080 of 1,080 Fold A
rows), compared in memory and discarded. The prediction is the production-replication receipt
(`analysis/SAEA-SLURP-INTENT-AGREEMENT-PRODUCTION-REPLICATION-V1/replication-v1.json`, sha256 `7cd1f6d3...`).

| bank class (defined on the sealed PLAN arm) | rows | predicted w_agree 0 | A/A flown | predicted w_agree 1 | arm flown |
| --- | ---: | ---: | ---: | ---: | ---: |
| INTENT-WRONG (INTENT-UNCOVERED + INTENT-COVERED) | 191 | 86 (45.0 %) | **86** | 156 (81.7 %) | **156** |
| CORRECT | 480 | 467 | 467 | 478 | 478 |
| ENTITY-MIXED | 193 | 187 | 187 | 192 | 192 |
| ENTITY-FP-ONLY | 131 | 124 | 124 | 130 | 130 |
| ENTITY-FN-ONLY | 84 | 82 | 82 | 83 | 83 |
| MALFORMED | 1 | 1 | 1 | 1 | 1 |
| all rows | 1,080 | 947 | 947 | 1,040 | 1,040 |

| plan class | newly delivered, predicted / flown | newly lost, predicted / flown |
| --- | --- | --- |
| INTENT-UNCOVERED (130) | 70 / 70 | 0 / 0 |
| INTENT-COVERED (61) | 2 / 2 | 2 / 2 |
| CORRECT (480) | 11 / 11 | 0 / 0 |
| ENTITY-MIXED / FP-ONLY / FN-ONLY | 5 / 5, 6 / 6, 1 / 1 | 0 / 0 each |
| all rows | 95 / 95 | 2 / 2 |

**The flown delivery equals the offline prediction in every cell**, the A/A's delivery equals the sealed PLAN
arm's on every row, each arm's flown boundary set equals its own prepared supply on 1,080 of 1,080 rows, and
the 70 CONV-roster rows are exactly the 70 newly delivered INTENT-UNCOVERED rows (70 of 70 delivered in the
arm, 0 in the A/A; the CONV derivation lists no newly lost row there). No delivery defect. On the 95 newly delivered rows the consumption tracer marks the gold entry `use` on 64 and `ignore`
on 31.

**Conversion** (counts only; the A/A's own intent verdict on the left, the arm's on the right):

| rows, by delivery transition A/A -> arm | rows | wrong -> right | right -> wrong | right -> right | wrong -> wrong |
| --- | ---: | ---: | ---: | ---: | ---: |
| **newly delivered** (arm yes, A/A no) | 95 | **32** | 1 | 22 | 40 |
| newly lost (arm no, A/A yes) | 2 | 0 | 1 | 0 | 1 |
| delivered in both | 945 | 35 | 29 | 832 | 49 |
| delivered in neither | 38 | 0 | 0 | 6 | 32 |
| all rows | 1,080 | 67 | 31 | 860 | 122 |

Of the 95 rows that NEWLY received their gold intent's boundary entry, **54 answered the intent correctly**
in the arm. Of the 72 of them that were intent-wrong in the A/A, **32 converted (44.4 %)**, against the CONV
probe's m = 32 of 70 (45.71 %, Wilson CI95 [34.57, 57.30] %); 1 of the 23 the A/A already got right was lost.
On the 70 CONV-roster rows themselves the arm answers 31 correctly (the CONV probe 32, the A/A 2, the sealed
PLAN 0 by construction), and the arm and the CONV probe agree on per-row correctness on 67 of 70.

The prior the registration recorded (the term moves gold to position 1 on 35 of the 86 already-delivered but
intent-wrong rows) is measured here: of the 84 rows delivered in both flights and intent-wrong in the A/A,
**35 are right in the arm**. The saves therefore split 32 on newly delivered rows and 35 on rows whose
delivery did not change; 29 of the 31 harms sit on rows delivered in both flights, where the arm changes the
order and composition of the eight delivered entries.

**Per class over the bad-case bank** (classes defined on the sealed PLAN arm):

| bank class | rows | A/A intent correct | arm intent correct | gained | lost | SLU-F1 A/A | SLU-F1 arm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **INTENT-UNCOVERED** | 130 | 4 | **43** | 40 | 1 | 39.93 | 49.28 |
| **INTENT-COVERED** | 61 | 13 | **28** | 20 | 5 | 46.42 | 53.74 |
| CORRECT | 480 | 474 | 469 | 4 | 9 | 94.49 | 92.27 |
| ENTITY-MIXED | 193 | 189 | 180 | 2 | 11 | 54.43 | 55.49 |
| ENTITY-FP-ONLY | 131 | 127 | 124 | 1 | 4 | 19.77 | 22.36 |
| ENTITY-FN-ONLY | 84 | 83 | 82 | 0 | 1 | 58.84 | 64.80 |
| MALFORMED | 1 | 1 | 1 | 0 | 0 | 100.00 | 100.00 |

60 of the 67 saves land on the two intent-error classes; 25 of the 31 harms land on rows the PLAN arm had
intent-right.

## 6. Frontier row and the Perception token delta

Measured from each flight's own sealed wire responses (`usage.prompt_tokens`; prefilled =
`timings.prompt_n`, cached = `timings.cache_n`); both arms reconcile exactly to the sealed cost
(4,405 / 4,385 contacts; 36,515,553 / 37,676,859 prompt tokens). GPU hours are the serving monitor's active
seconds as the paired driver's `vs-aa/efficiency.json` (sha256 `e95d0da2...`) carries them.

| cell | official intent | official SLU-F1 | GPU-h / 1,080 | contacts / row | prompt tok / row | prefilled tok / row |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A/A (w_agree 0.0) | 82.50 | 63.31 | 1.7309 | 4.079 | 33,810.7 | 8,335.7 |
| **AGREE (w_agree 1.0)** | **85.83** | **65.16** | **1.8816** | 4.060 | 34,886.0 | 8,733.5 |
| delta | **+3.33** | **+1.85** | +0.1507 (+8.7 %) | -0.019 | +1,075.3 (+3.2 %) | +397.7 (+4.8 %) |

Frontier ratios: +1.77 pp intent per GPU-hour per 1,080 rows; +0.38 pp intent per 1,000 prefilled tokens per
row.

**The Perception block** costs what the read said it would: per row, the first Perception contact's prompt
tokens, arm minus A/A (every other Perception input is byte-identical), average **+1.36 tokens per row**
against the registered +1.4 (median 0; 565 of 1,080 rows exactly 0; range -78 to +97). **The frontier's
token growth is not the block**: it is downstream. Per role, prompt tokens per row move Perception +1.4,
Solver +341.5, Reviewer +391.0, Planner +390.5, and -49.1 on the wire responses no role-visit receipt names
(11 in the A/A, 4 in the arm, matching each flight's finite-completion row count); prefilled tokens per row move almost entirely on the Solver (+398.6; the Reviewer and
Planner prefixes stay 97 % cached). The mechanism is visible in the supply: the acquired slot-contract items
per row rise from 11.95 to 12.90 once Perception proposes different intents, while the boundary (7.99) and
exemplar (20.0) items do not move. The GPU-hour delta (+8.7 %) is larger than the prefilled-token delta
(+4.8 %) and also reflects the serving session's own utilisation over the two windows (78.5 % vs 76.1 %
mean); it is reported, not decomposed.

## 7. The A/A-versus-PLAN instrument check

The A/A re-flies the locked plan's own bytes (its prepared supply reproduces the sealed PLAN's output digest,
and its delivery equals PLAN's on every row), so its distance from PLAN and PLANr measures the instrument,
not the mechanism. Same estimator, seed and draws as the gating read.

| pair | intent | delta pp [CI95] | official SLU-F1 | delta pp [CI95] | saves / harms | byte-identical answers |
| --- | --- | --- | --- | --- | --- | ---: |
| A/A vs PLAN | 82.22 -> 82.50 | +0.28 [-0.74, +1.30] | 63.63 -> 63.31 | -0.32 [-1.74, +1.14] | 18 / 15 | 823 / 1,080 |
| A/A vs PLANr | 82.50 -> 82.50 | 0.00 [-0.93, +1.02] | 63.80 -> 63.31 | -0.49 [-1.79, +0.79] | 14 / 14 | 827 / 1,080 |
| arm vs A/A (gating) | 82.50 -> 85.83 | +3.33 [+1.57, +5.09] | 63.31 -> 65.16 | +1.85 [+0.23, +3.47] | 67 / 31 | 713 / 1,080 |

**The A/A reproduces the locked plan**: intent 82.50 against PLAN 82.22 and PLANr 82.50, both point deltas
inside the plan's own null (h_intent 0.9943, h_SLU 1.2485) and both CI95 containing zero. The between-flight
churn is about 15 intent flips each way with 76 % of answers byte-identical (the np4 serving property the DET
read located); the gating pair shows 67 / 31 against that background.

## 8. Claim boundary

A development read on a TRAIN construction fold (owner decisions 28 and 86): never a test claim, never a
generalisation claim, and it admits nothing into a default plan by itself. The Fold-A word is the registered
rule's; under decisions 115 and 127 a SYSTEM-LEVEL benefit claim is final only after replication on a fresh
roster (and, at the end of Stage 3, one test read). The per-scenario tables and the per-class table carry no
CI and no reading clause. No disposition is taken here (decision 139).

## 9. Records

- `docs/exposure-ledger.md`: the arm, the A/A, the smoke, the two generation FITs, the smoke FIT and the READ
  row flipped to consumed with the sealed facts above, and seven closure blocks under the AGREE table; no other
  row touched.
- `docs/results/stage2-results-ledger.md` and `.json`: entry `SLURP-AGREE`.
- `scripts/analysis/slurp_agree_beside_read.py`: the beside read (new); `scripts/flights/agree/agree_read.sh`:
  line continuations restored, behaviour unchanged.
