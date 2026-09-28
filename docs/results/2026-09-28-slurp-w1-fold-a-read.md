# Cell W1 (card selection) read: intent +0.19 pp CI95 [-0.74, +1.11] and official SLU-F1 +0.53 pp [-0.85, +1.93] against the shared wave A/A on TRAIN Fold A (DESCRIPTIVE)

Read 2026-09-28 by Claude Opus 5.5 (worktree `/home/chao/saea-worktrees/fable-wavereads`, branch
`fable/wavereads`). The registered paired read (READ row `SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1`,
ROOT COUNTERSIGNED before any score was opened -- the driver refuses otherwise; recipe
`slurp-stage3-w1-cardsel-fold-a-paired-analysis-v1`, sha256
`9f26e7ca99aa3d0ff279d96d976f8ded4d77d56b8917619b7fc8735d9cb62e35`) ran through
`scripts/flights/wave/wave_read.sh w1` -> `scripts/flights/read_paired_cell.sh` ->
`scripts/analysis/stage3_paired_read.py` (sha256 `433bc936c0106f6377ed8ba693539f30dbe36014ec0622650ddafffb0656fad1`):
seed 20260927, 10,000 draws, the row as the resampling unit (cluster key `sample_id`), TRAIN gold through
`slurp-slu-official-train`. Outputs under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1/`:
`vs-aa/` (GATING; README sha256 `f2e62404b13825d19d966f64cd99150b20746bd55432d1485b43219568c3c3e0`,
`verdict.json` `26ece40358b559c852d68c804bedd9f66001ab7835e3e7c07ee7ae4856e6d94c`, `score-contrasts.json`
`bc691b070b10bcadcee194c67c0acd48de32234f66dee091aab0e8a320019827`) and `vs-comparator/` (the sealed AGREE arm,
CONTEXT only; `verdict.json` `6369240a6d7bda0fb2154b93766caa4d756951c09c393a226169b317eae7eefa`). The recipe's
per-role Solver token delta and the registered harm rows were computed by
`scripts/analysis/stage3_wave_beside_read.py` (sha256 `3075080ed77738ef8500ad208638bd21a2e14fa16a57c5f0be900526912ad2f7`)
into a new sibling `beside/beside-v1.json` (sha256 `edee7f523dcc35d1e9c6a3180d2efd82c213297138264b6eb3cf7658c5732b03`).
Model-free throughout: zero model, tokenizer, encoder, scorer, server and network contacts; the official scorer
ran once per arm at finalize and its sealed per-sample output is read. No utterance text, transcript, gold
label string or model output is printed or persisted.

**DESCRIPTIVE.** This note states the numbers and which side of the pre-declared rule they fall on. The
verdict word is the coordinator's; the disposition is taken with the owner (decision 139). A development read
on a TRAIN construction fold (decisions 28 and 86): never a test claim.

## 1. What flew

One campaign step (driver step 1, `w1`) at flight commit `5f8b4c9d` on session
`serving-slurp-native-candidate-five-train-a-np4-v1`, study tree clean at seal (`study_repo_dirt` empty): the
four-row smoke (COMPLETED, 16 calls, unscored), then the shared A/A and the W1 arm.

| run | sealed at (UTC) | rows | contacts / cap | speech s | GPU-active | state |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (shared A/A) | 05:41:00 | 1,080 | 4,393 / 11,880 | 12,557.168 | 6,270.0 s = 1.7417 GPU-h | COMPLETED, scored once |
| `SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1` (arm) | 07:21:08 | 1,080 | 4,401 / 11,880 | 12,571.056 | 5,768.3 s = 1.6023 GPU-h | FINALIZED, scored once |

| artefact sha256 | A/A | arm |
| --- | --- | --- |
| run manifest | `d3d7501f0e8740f9809325333f5515e6cfc245e4c7f9ef40a5acde6047d2c69e` | `6335f9776b6553d7c45194a887f971cf3667138394988dd72fe21191f6ed5725` |
| outputs | `548ba6662b31282d4c34bcd9f5833e9b667a20c2f9a3f51764b6f76504bfe84b` | `d1c4f438aa71a5284ff5347912772e0bfd93f78f1b7280a9f8e9fc5654d8fc03` |
| scores | `e935745a2cc41734f06e358a624729e066b6fe9c16bc5cc2d8eec630d7f5cfc4` | `cd5e25048dbd2560356885dd852d7919cd12366b5ab580a9e8019706d50028e1` |
| generation manifest | `173297f68760e08a5ca0d7790fe753303411ea8246080be0ca2e320c1459e140` | `bae88ab6ddde4098e63725b57360726bb74ed5c8c4bb03daff3f46b448eab4d8` |
| phases | `37425ffc066eb5ee01521ec67aff7ffd940abb8b7894bb61149ed3d95547d542` | `a3c7ef3c406e5ae55546e118f651cccccd3345be8ca45286a30e3734a9105dfd` |
| flight receipts | `03c80bc63afa1ee2870dd7b79c2a8233d5795b662bff2d92b1cdfbec92f28bc9` | `ce76b94136572a7b620bd505d209fd19ed770faee8c0877c93ed79075ab7ef76` |

## 2. Stop and structural gates

| gate | A/A | arm |
| --- | --- | --- |
| official pooled SLU-F1 recomputed from per-sample counts | diff 0.0 | diff 2.2e-16 |
| rows admitted | 1,080 / 1,080 | 1,080 / 1,080 |
| tool calls | 0 | 0 |
| context-fit compacted contacts | 0 | 0 |
| Planner ACCEPT / REVISE; revisions executed | 1,066 / 29; 29 | 1,073 / 30; 29 |
| role visits per row (2 / 4 / 7) | 14 / 1,037 / 29 | 6 / 1,045 / 29 |
| deliver-normaliser changed rows | 96 | 76 |

Recipe step 2's per-row subset check of the Solver card selection against the A/A's (same Perception
shortlist) is not computed by the registered driver and was not run here; the delivery check below shows the
Perception boundary delivery is identical on both arms (1,040 / 1,040, 0 newly delivered, 0 newly lost).

## 3. The contrasts

Gating, the arm against the shared wave A/A (`vs-aa/`):

| metric | A/A | arm | delta pp | CI95 pp | saves / harms | McNemar p |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| **intent (scenario_action_exact), primary** | 85.65 | 85.83 | **+0.19** | **[-0.74, +1.11]** | 14 / 12 | 0.845 |
| scenario | 89.44 | 89.54 | +0.09 | [-0.74, +0.93] | 11 / 10 | 1.000 |
| action | 86.48 | 86.85 | +0.37 | [-0.46, +1.30] | 14 / 10 | 0.541 |
| **official pooled SLU-F1, guard** | 64.16 | 64.69 | **+0.53** | **[-0.85, +1.93]** | -- | -- |
| official pooled span-F1 | 53.54 | 54.59 | +1.05 | [-0.58, +2.71] | -- | -- |
| per-row SLU-F1 | 42.98 | 43.73 | +0.75 | [-0.37, +1.91] | 74 / 53 | 0.076 |
| per-row slot exact F1 | 35.11 | 36.17 | +1.06 | [-0.22, +2.34] | 58 / 40 | 0.085 |

Per channel (descriptive, unclustered): intent -0.90 far-field (557 rows, 4 / 9), +1.34 headset (523 rows,
10 / 3); per-row SLU-F1 +1.78 far-field, -0.34 headset.

Context only, the arm against the sealed AGREE arm (`vs-comparator/`): intent 85.83 -> 85.83, +0.00 pp
[-0.93, +0.93] (14 / 14); official SLU-F1 65.16 -> 64.69, -0.47 pp [-1.83, +0.92]. The instrument's own
reading, the wave A/A against the AGREE arm whose bytes it re-flies: intent 85.65 vs 85.83 (-0.19), official
SLU-F1 64.16 vs 65.16 (-1.00).

## 4. The pre-declared rule, and where the numbers fall

Recipe `decision_rule` (owner decision 127, no-harm): against the shared in-chain A/A, intent CI95 lower bound
not below -0.9943 pp AND official pooled SLU-F1 CI95 lower bound not below -1.2485 pp; HARMFUL on a measured
loss on either metric (CI95 upper bound below zero); never reported as a gain.

| clause | measured | side |
| --- | ---: | --- |
| intent CI95 lower bound >= -0.9943 | -0.74 | holds (0.25 pp inside the margin) |
| official SLU-F1 CI95 lower bound >= -1.2485 | -0.85 | holds (0.40 pp inside the margin) |
| intent CI95 upper bound < 0 (harm) | +1.11 | not met |
| official SLU-F1 CI95 upper bound < 0 (harm) | +1.93 | not met |

Both no-harm clauses hold and neither harm clause is met. Both intervals include zero.

## 5. Per-scenario tables (both weightings)

Stratum: the Fold A roster receipt's per-item `stratum` (`docs/receipts/rosters/slurp-evo-fold-a-v2.json`,
sha256 `1fe7908c...`), 18 scenarios x 60 rows; per-scenario CI95 by the cluster bootstrap within scenario.

| weighting | intent delta pp | intent CI95 pp | SLU-F1 delta pp | SLU-F1 CI95 pp |
| --- | ---: | --- | ---: | --- |
| natural mixture | +0.19 | [-0.74, +1.11] | +0.53 | [-0.85, +1.93] |
| equal scenario | +0.19 | [-0.74, +1.11] | -0.40 | [-2.05, +1.20] |

| scenario | intent A/A | intent arm | delta | saves / harms | SLU A/A | SLU arm | delta | SLU CI95 |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| alarm | 91.67 | 88.33 | -3.33 | 0 / 2 | 69.58 | 74.18 | +4.61 | [-1.09, +10.14] |
| audio | 81.67 | 81.67 | +0.00 | 2 / 2 | 60.82 | 64.15 | +3.32 | [+0.00, +8.18] |
| calendar | 91.67 | 88.33 | -3.33 | 0 / 2 | 64.72 | 66.05 | +1.33 | [-2.92, +5.92] |
| cooking | 83.33 | 86.67 | +3.33 | 2 / 0 | 65.98 | 61.91 | -4.08 | [-9.06, -0.18] |
| datetime | 91.67 | 91.67 | +0.00 | 0 / 0 | 74.02 | 72.24 | -1.78 | [-7.42, +4.02] |
| email | 90.00 | 90.00 | +0.00 | 0 / 0 | 62.76 | 61.39 | -1.38 | [-8.03, +4.79] |
| general | 50.00 | 53.33 | +3.33 | 2 / 0 | 26.09 | 15.38 | -10.70 | [-27.98, +2.80] |
| iot | 81.67 | 83.33 | +1.67 | 1 / 0 | 69.75 | 71.67 | +1.92 | [-4.53, +8.78] |
| lists | 90.00 | 90.00 | +0.00 | 0 / 0 | 57.66 | 55.57 | -2.09 | [-12.80, +7.60] |
| music | 81.67 | 80.00 | -1.67 | 1 / 2 | 46.33 | 44.51 | -1.82 | [-7.19, +3.73] |
| news | 91.67 | 90.00 | -1.67 | 0 / 1 | 74.41 | 66.97 | -7.44 | [-16.98, +0.00] |
| play | 88.33 | 90.00 | +1.67 | 1 / 0 | 54.79 | 57.50 | +2.71 | [-2.49, +8.45] |
| qa | 88.33 | 90.00 | +1.67 | 1 / 0 | 65.10 | 64.70 | -0.40 | [-4.71, +3.66] |
| recommendation | 96.67 | 100.00 | +3.33 | 2 / 0 | 73.04 | 67.84 | -5.21 | [-12.79, +1.67] |
| social | 81.67 | 81.67 | +0.00 | 0 / 0 | 58.76 | 58.55 | -0.21 | [-3.38, +3.31] |
| takeaway | 81.67 | 80.00 | -1.67 | 1 / 2 | 55.12 | 61.86 | +6.75 | [+2.12, +11.67] |
| transport | 85.00 | 83.33 | -1.67 | 0 / 1 | 62.97 | 70.44 | +7.47 | [+3.83, +12.06] |
| weather | 95.00 | 96.67 | +1.67 | 1 / 0 | 79.72 | 79.55 | -0.17 | [-5.25, +4.40] |

## 6. Delivery and conversion

Delivered = the row's own gold intent boundary entry is among the flown Perception consumption's intent
boundary items (counts only).

| quantity | A/A | arm |
| --- | ---: | ---: |
| delivered | 1,040 | 1,040 |
| newly delivered / newly lost | -- | 0 / 0 |

| delivery group | rows | wrong -> right | right -> wrong | right -> right | wrong -> wrong |
| --- | ---: | ---: | ---: | ---: | ---: |
| delivered in both | 1,040 | 14 | 11 | 907 | 108 |
| delivered in neither | 40 | 0 | 1 | 6 | 33 |

W1 moves no Perception key, so there is no conversion set; the intent movement is 14 / 12 inside identical
delivery.

## 7. Tokens and cost

| quantity | A/A | arm | arm - A/A |
| --- | ---: | ---: | ---: |
| contacts | 4,393 | 4,401 | +8 |
| prompt tokens per row | 35,061.4 | 31,681.9 | -3,379.5 |
| prefilled tokens per row | 8,762.3 | 7,639.6 | -1,122.7 |
| completion tokens per row | 245.9 | 249.0 | +3.1 |
| GPU-h per 1,080 rows | 1.7417 | 1.6023 | -0.1394 (-8.0 %) |

Per role, from the sealed COST records joined to the USE role ids (`beside/`):

| role | contacts A/A / arm | prompt tokens per contact A/A -> arm | delta | prefilled per contact delta |
| --- | --- | --- | ---: | ---: |
| Perception | 1,080 / 1,080 | 3,598.4 -> 3,598.4 | 0.0 | +4.2 |
| Solver | 1,109 / 1,109 | 10,228.3 -> 9,103.3 | **-1,125.0** | -1,105.9 |
| Reviewer | 1,109 / 1,109 | 10,203.6 -> 9,078.6 | -1,125.0 | 0.0 |
| Planner | 1,095 / 1,103 | 10,338.9 -> 9,217.1 | -1,121.8 | +6.5 |

The measured Solver delta, -1,125.0 tokens per contact, sits beside the registered expectation of about
-1,186 (`card-selection-measurement-v1.json` `saving.tokens_per_solver_contact.mean` 1,185.83). Nearly all
of the prefill saving is on the Solver; the Reviewer and Planner render the same block from the prefix cache.

Frontier row (decision 75): intent +0.1852 pp and SLU-F1 +0.5326 pp at -1,122.7 prefilled tokens per row and
-0.1394 GPU-h per 1,080 rows.

## 8. Registered harm rows

`card-selection-measurement-v1.json` registered 5 rows that lose a card for a gold slot type, read row by
row (ids and 0/1 only):

| sample id | intent A/A -> arm | per-row SLU-F1 A/A -> arm |
| --- | --- | --- |
| `slurp:train:003057:audio-1490201218` | 1 -> 1 | 0.00 -> 0.00 |
| `slurp:train:010065:audio-1501756518` | 0 -> 0 | 100.00 -> 100.00 |
| `slurp:train:012069:audio-1492780300` | 1 -> 1 | 0.00 -> 0.00 |
| `slurp:train:012876:audio-1502309870-headset` | 1 -> 1 | 18.48 -> 20.36 |
| `slurp:train:016867:audio-1497438083` | 0 -> 0 | 0.00 -> 0.00 |

No registered harm row changed its intent outcome, and none lost per-row SLU-F1. The recipe's "rows whose
delivered answer used a dropped type" (registered as a count of 12 without row ids) was not re-derived here:
it needs the delivered slot types, which this note does not open.

## Coordinator verdict (Fable 5.1, 2026-09-28)

**NEUTRAL (no-harm holds; retained as an enabler).** Against the shared wave A/A, intent +0.19 [-0.74,
+1.11] and official SLU-F1 +0.53 [-0.85, +1.93]: both pre-declared no-harm clauses hold (margins intent
0.9943 / SLU-F1 1.2485) and no harm clause is met. The measured saving (-3,379.5 prompt tokens per row,
-8.0 % GPU-h, Solver -1,125 tokens per contact against the registered -1,186) is the room W3a and W4 need.
W1 folds into COMP-2 only after AGREE replicates on DEV-2000-ADDED (decisions 138, 161, 169). The
instrument's own reading (the wave A/A against the AGREE arm it re-flies: intent -0.19, SLU-F1 -1.00) sits
inside the between-flight band. The agent's numbers above are unchanged.
