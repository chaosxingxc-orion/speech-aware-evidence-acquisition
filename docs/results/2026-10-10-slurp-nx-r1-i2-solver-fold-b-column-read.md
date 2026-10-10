# NX round R1 iteration 2 (Solver instruction-template column, TRAIN Fold B): every arm NOT NOMINATED on the official column, none HARM; r1-i2-c3 again empties rows (pooled +0.74 [-0.43, +1.94], per-row -2.56 [-3.48, -1.70]); both in-template empty gates failed; the plateau rule closes the Solver-template line

Read 2026-10-10 by Claude Opus 5.5 (analysis agent, on the coordinator's brief, Fable 5.1) in the worktree
`fable/nx-r1-i2-results`. Model-free: this note opened no model, server, encoder, embedder, tokenizer or GPU, ran no
scorer and wrote nothing under the data root. It reads the on-file outputs of the registered read
`SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-COLUMN-READ-V1`, the registered offline apply read
`SAEA-SLURP-NX-POSTPROC-V4-APPLY-V1`, and the sealed run. No utterance text, transcript, gold value, slot filler or
model output was printed or persisted. Only counts, rates, deltas, slot-type and scenario labels, ids and hashes
appear below.

**DESCRIPTIVE.** These are development numbers on a TRAIN construction fold (owner decisions 28 and 86). They are
never a test claim and never a system-level claim. The claim ceiling of the cell is `nominated`. The verdict words in
section 7 apply the rule registered for this round (package README section 5). They are proposed to the coordinator.

## 0. Answer in five lines

1. No iteration-2 arm is NOMINATED. No official pooled SLU-F1 delta vs `lock` has a CI95 lower bound above 0. None is HARM: every upper bound is above 0. The in-flight `aa` twin reads -0.43 [-1.08, +0.19].
2. `r1-i2-c3` (c3 plus c5's conventions, the declared +1.54 pp carrier) passes the twin bar and the intent guard (7 rows), but only its CI-LB fails: pooled +0.74 [-0.43, +1.94]. It repeats iteration 1: false fill -18.11 pp and non-empty exact -2.62 pp, so its per-row SLU-F1 is a measured loss (-2.56 [-3.48, -1.70]). The conventions did not recover c3's non-empty loss; that loss grew (-12 to -18 rows).
3. The two gated empty decisions failed. `r1-i2-c1` (decision after extraction, keep-list of heard kinds) erased the empty effect: false fill +1.02, official -0.88 [-2.04, +0.28], intent 8 rows. `r1-i2-c2` (one soft sentence) reversed it: false fill +9.95 [+6.37, +13.78], official -0.90 [-2.07, +0.27], equal-scenario -1.62 [-2.89, -0.39].
4. On the locked v4g delivery the Solver arms add nothing. v4g(X) - X is +0.77 to +1.81 with CI-LB > 0 on every arm. On the v4g base, `r1-i2-c3`'s advantage over `lock` shrinks to +0.08 (point; the decision-239 study bootstraps +0.08 [-1.10, +1.29]).
5. The plateau rule closes the Solver-template line after its second and last round: `configs/probes/slurp_native_role_solver_v2.txt` stays the lock. Per owner decision 239, the empty-entity decision moves upstream to R6: the core's own presence verdict, gated by the supply's entity-free share.

## 1. Identities

| item | value |
| --- | --- |
| cell / experiment | `slurp-native-stage3-nx-r1-i2-solver-fold-b-v1` (package `docs/readiness/2026-10-09-slurp-nx-r1-i2-solver-fold-b-v1/`; candidates `docs/readiness/2026-10-09-slurp-nx-r1-iter2-solver-candidates-v1/`) |
| run / attempt | `SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-V1` / `attempt-slurp-native-stage3-nx-r1-i2-solver-fold-b-generation-v1` (smoke and FIT runs as registered; the smoke was a first attempt with no recovery) |
| flight commit | `3910c77c817a955997ef84ec774843999d936292` (`study_commit` of the run manifest; status COMPLETED; `study_repo_dirt` empty) |
| roster | TRAIN Fold B `SLURP-EVO-FOLD-B-V2`, 1,080 rows (392 empty-gold, 688 non-empty-gold), split identity `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a` |
| flight | 1,080 rows; 8,640 contacts (8 per row: Perception, then the seven Solver arms, `lock` last and delivering); 25,238.379 speech-audio seconds; 84,273,705 prompt / 300,283 completion tokens; generation wall 7,674 s and GPU-active 7,505 s (2.085 GPU-h, mean utilisation 83.9 %) per `efficiency.json`; 2 h 18 m end to end as reported by the coordinator (not re-derived here) |
| run manifest / generation manifest | `06b0cb682ab28fdc12051aaec79cbcd71060fcbff2f1300f3df361de0070fcba` / `66b7a379fc50a09666da40f9a07a5c94b5caac9a027377ab65aafb72990b584a` |
| outputs / scores | `f2c31ae558f9be139dbc49f638c2df2849e18e890393482aa55417e6264659ca` / `878844360a2511a81a9d057fc812fa87742f371ca29ba0136eab18cda76643d7` |
| raw trace / trace manifest | `2c8dd3cf6e2580ea11dad61d293a1c8750f8a161766f7f59adc8ae4d8aa09fa2` / `ce079bb9740871e4d37f7eb4e56c8e34b6d8b25a17dd7adf14db8c2fb28a5b8b` |
| protocol / composed config | `b54d1e7aae7462281fe586a7a8b53935c8970ef9ce7e98661ecff3dab3f58845` / `ed16cc5f3ba29c33cfe6119605da761610b2323fa685692ffd6139cacf71bb10` |
| READ run | `SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-COLUMN-READ-V1` (the read driver refuses unless the READ row is root countersigned; it ran) |
| recipe | `slurp-nx-r1-i2-solver-fold-b-column-analysis-v1`, `docs/readiness/2026-10-09-slurp-nx-r1-i2-solver-fold-b-v1/analysis-recipe-v1.json` sha256 `2bb0d7d6aa63e673ebfc4eef34ad5c42064406228250c556ae38dfb6209e8ba2` |
| read driver | `scripts/analysis/nx_r1_read.sh` sha256 `54b3d1ab2ca9bb80462d30d006ff73b75da149da7072a63826408ce9d6da2ba0` (at this note's base) |
| node-local (schema `saea-nx-solver-column-read-v2`, primary `exact_set_normalised`) | `node-local/report.json` `7e4bd7b542945719d360de03194fe5dcbc4b4783e8657d9852bff1ac7c990260`, `tables.md` `ce34789034c2f7a7459bb1ea5395a213412a75351e1085dd5956b39d531f4e18` |
| official columns | `<run dir>/supply-variants/score-summary.json` `2ae8cd4e5ad1f5b8aec6ac83498e19e5606183eb763cba876e7f92304e471ae8` (seven column scorings, `slurp-slu-official-train`, never sharded; contacts scorer 7, all others 0) |
| paired contrasts (`score-contrasts.json`) | aa `bce22e77...`, i2-c1 `2807ff94...`, i2-c2 `689c119a...`, i2-c3 `d5bc75ca...`, i2-c4 `c945887b...`, i2-c5 `d3d10acc...`; driver `5c95a2e3...`, stage-3 driver `stage3_paired_read.py` `da9485fc...`; every `verdict.json` status DESCRIPTIVE (aa `f2dd9715...`, c1 `e3179f5e...`, c2 `df8f4246...`, c3 `e84df1c6...`, c4 `ce98b3d6...`, c5 `acef29ca...`) |
| read contacts | model 0, encoder 0, tokenizer 0, GPU 0; scorer 7 (the seven local official column scorings) |

Paths: analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-COLUMN-READ-V1/`
(`node-local/`, `aa-vs-lock/`, `r1-i2-c1-vs-lock/` .. `r1-i2-c5-vs-lock/`, `cross-iteration/`); run dir
`$SPEECHRL_DATA_DIR/runs/SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-V1/attempt-slurp-native-stage3-nx-r1-i2-solver-fold-b-generation-v1/`.

The arms (templates under `configs/probes/nx/solver/r1/`, candidates README section 3):

- `r1-i2-c1` (221 words, `45b3d55a...`): c5 plus an empty decision taken after extraction, with a keep-list of heard value kinds.
- `r1-i2-c2` (230, `656a0aa5...`): c5 plus one soft empty sentence ("never empty when you heard a value of a type the supplied examples annotate").
- `r1-i2-c3` (230, `bcfbc69f...`): c3's decision-first empty step plus c5's filler conventions. This is the declared carrier: +48 raw-exact rows, +1.54 pp class-split.
- `r1-i2-c4` (229, `60e90ef3...`): c5 plus c2's heard-span anti-copy block.
- `r1-i2-c5` (181, `0463a497...`): c5 with the contract tightening removed (the ablation).
- `aa`: the in-chain twin.
- `lock`: `configs/probes/slurp_native_role_solver_v2.txt` (160 words, sha256 `18bff5c557cac7ac14be6b08aa0a1a6ad54c1b9820199c3b6749b2271d756fbd`), delivering, last.

Base: the review-off COMP-1b module graph (agree-vote-seed and centroid-boundary-key on), no tool schema on any role,
program `phase-native-module-v1-c8`, v3 delivery normaliser.

## 2. The official column (decides; paired row bootstrap vs `lock`, cluster `sample_id`, 10,000 draws, seed 20260915)

`lock` levels: pooled official SLU-F1 63.43 %, per-row mean SLU-F1 42.29 %, intent 83.15 %, span-F1 53.11 %.

| arm | pooled SLU-F1 % | pooled delta pp [CI95] | per-row SLU-F1 delta pp [CI95] (saves / harms) | intent % | intent delta pp [CI95] (rows differing) | headset per-row delta pp (s / h) | far-field per-row delta pp (s / h) |
| --- | ---: | --- | --- | ---: | --- | --- | --- |
| `aa` twin (bar) | 63.00 | **-0.43 [-1.08, +0.19]** | -0.16 [-0.53, +0.19] (11 / 12) | 82.96 | -0.19 [-0.46, +0.00] (2) | -0.27 (5 / 6) | -0.06 (6 / 6) |
| `r1-i2-c1` | 62.55 | -0.88 [-2.04, +0.28] | -0.14 [-0.92, +0.67] (38 / 37) | 82.59 | -0.56 [-1.11, -0.09] (**8**) | +0.66 (20 / 15) | -0.90 (18 / 22) |
| `r1-i2-c2` | 62.53 | -0.90 [-2.07, +0.27] | +0.77 [-0.06, +1.65] (49 / 28) | 82.78 | -0.37 [-0.93, +0.09] (**8**) | +1.54 (26 / 12) | +0.04 (23 / 16) |
| `r1-i2-c3` | 64.17 | **+0.74 [-0.43, +1.94]** | **-2.56 [-3.48, -1.70]** (24 / 58) | 82.69 | -0.46 [-0.93, +0.00] (7) | -1.93 (10 / 25) | -3.17 (14 / 33) |
| `r1-i2-c4` | 63.53 | +0.10 [-0.97, +1.19] | -0.60 [-1.37, +0.13] (36 / 34) | 82.78 | -0.37 [-0.83, +0.00] (6) | -0.17 (20 / 15) | -1.02 (16 / 19) |
| `r1-i2-c5` | 63.40 | -0.03 [-0.97, +0.93] | -0.51 [-1.28, +0.25] (28 / 31) | 82.87 | -0.28 [-0.65, +0.09] (5) | -0.46 (11 / 15) | -0.55 (17 / 16) |

Intent is the official `Intent (scen_act)` row. "Rows differing" counts saves plus harms of per-row intent
correctness vs `lock`, the registered guard (limit 7 rows = the 0.65 pp floor at 1,080). Channel columns are per-row
SLU-F1 deltas (headset n = 527, far-field n = 553); the tool emits per-channel numbers for per-row metrics only.
Every arm loses intent rows at the point. The Solver arms see the same Perception note, so this is Solver re-labelling
noise. It is one-directional (harms exceed saves on every arm), but the largest movement is 8 rows.

Pooled span-F1 (exact spans) deltas: aa -0.32 [-1.03, +0.39]; c1 -0.43; c2 -0.47; **c3 +1.14 [-0.30, +2.59]**; c4
+0.68 [-0.54, +1.93]; c5 +0.23.

Equal-scenario weighting (18 scenarios x 60 rows, unweighted mean of per-scenario deltas, stratified bootstrap) is
reported beside the natural mixture and never gates:

| arm | equal-scenario delta pp [CI95] | scenarios up / down |
| --- | --- | --- |
| `aa` | -0.52 [-1.23, +0.13] | 7 / 9 |
| `r1-i2-c1` | -1.14 [-2.35, +0.01] | 6 / 11 |
| `r1-i2-c2` | -1.62 [-2.89, -0.39] | 9 / 9 |
| `r1-i2-c3` | +1.31 [-0.02, +2.66] | 10 / 8 |
| `r1-i2-c4` | -0.05 [-1.26, +1.11] | 10 / 8 |
| `r1-i2-c5` | +0.33 [-0.76, +1.46] | 10 / 8 |

`r1-i2-c2`'s equal-scenario upper bound is below 0. HARM is defined on the pooled natural mixture only, so this is
reported and not ruled.

Official counts (exact-span `Entities` row; distance-credited `Slu f1` TP / FP / FN):

| arm | entity TP / FP / FN | SLU-F1 TP / FP / FN |
| --- | --- | --- |
| `lock` | 513 / 475 / 431 | 1,382 / 840.8 / 752.8 |
| `aa` | 511 / 481 / 433 | 1,376 / 856.2 / 760.2 |
| `r1-i2-c1` | 511 / 485 / 433 | 1,370 / 872.3 / 768.3 |
| `r1-i2-c2` | 525 / 526 / 419 | 1,402 / 947.2 / 733.2 |
| `r1-i2-c3` | **486 / 362 / 458** | **1,292 / 625.2 / 817.2** |
| `r1-i2-c4` | 512 / 448 / 432 | 1,360 / 796.8 / 764.8 |
| `r1-i2-c5` | 507 / 450 / 437 | 1,358 / 796.9 / 770.9 |

**Per-row against pooled, again.** The per-row SLU-F1 scores every empty-gold row 0 whatever the arm answers
(iteration-1 note, section 2). It is therefore blind to the 392 empty-gold rows and to every false fill.

- `r1-i2-c3` removes 113 exact-span FPs (475 -> 362), which the pooled F1 rewards. It also loses 27 exact TPs (513 -> 486), which the per-row mean sees in full.
- `r1-i2-c2` is the mirror image. Its per-row is +0.77 [-0.06, +1.65] and its non-empty raw exact is +3.05 pp, while its pooled is -0.90, because it adds 51 FPs (475 -> 526) for 12 TPs.

## 3. Node-local tables (E2 reader v2, paired vs `lock`, whole-utterance cluster bootstrap, 10,000 draws, seed 20260915, CI95)

Normalised = the arm's first Solver answer after the delivered row's own normaliser (`saea-deliver-normalise-v3`).
This is the primary from this iteration on. Raw = the sealed first-visit text, kept as a diagnostic. The node-local
read gates nothing in this round.

| arm | exact-set normalised pp [CI95] (b / c) | exact-set raw pp [CI95] (b / c) | empty-gold false fill pp [CI95] (b / c, n 392) | non-empty exact normalised pp [CI95] (b / c) | non-empty exact raw pp [CI95] | screen normalised / raw |
| --- | --- | --- | --- | --- | --- | --- |
| `aa` | -0.74 [-1.67, +0.19] (9 / 17) | -0.65 [-1.67, +0.28] (10 / 17) | +2.04 [-0.26, +4.34] (14 / 6) | +0.00 [-0.73, +0.73] (3 / 3) | +0.15 [-0.58, +0.87] | twin |
| `r1-i2-c1` | -0.65 [-2.13, +0.93] (31 / 38) | +0.74 [-0.83, +2.41] (44 / 36) | +1.02 [-2.30, +4.08] (22 / 18) | -0.44 [-1.89, +1.16] (13 / 16) | +1.74 [+0.00, +3.63] | fail / fail |
| `r1-i2-c2` | **-3.06 [-4.72, -1.39]** (29 / 62) | -1.67 [-3.52, +0.19] (42 / 60) | **+9.95 [+6.37, +13.78]** (49 / 10) | +0.87 [-0.73, +2.47] (19 / 13) | +3.05 [+1.16, +4.94] | fail / fail |
| `r1-i2-c3` | **+4.91 [+3.15, +6.76]** (76 / 23) | +6.02 [+4.17, +7.87] (87 / 22) | **-18.11 [-21.94, -14.29]** (0 / 71) | **-2.62 [-4.22, -1.16]** (5 / 23) | -0.87 [-2.62, +0.87] | fail (secondary) / pass |
| `r1-i2-c4` | +0.93 [-0.56, +2.41] (37 / 27) | +2.22 [+0.65, +3.80] (49 / 25) | -4.08 [-7.14, -1.02] (11 / 27) | -0.87 [-2.33, +0.58] (10 / 16) | +1.16 [-0.44, +2.76] | fail / pass |
| `r1-i2-c5` | +1.20 [-0.19, +2.69] (37 / 24) | +2.50 [+1.02, +4.07] (49 / 22) | -4.08 [-6.89, -1.28] (8 / 24) | -0.44 [-2.03, +1.02] (13 / 16) | +1.60 [-0.15, +3.34] | fail / pass |

b / c are discordant rows (arm only / `lock` only). For false fill a negative delta is better and b counts rows where
only the arm falsely fills. The normaliser leaves false fill unchanged for every arm. Parse validity: 100.00 % for
`lock`, c1 to c4; 99.91 % for `aa` and c5 (one row each).

Marginal levels (normalised; raw in brackets):

| arm | exact-set | empty-gold false fill (rows of 392) | non-empty exact | predicted items |
| --- | --- | --- | --- | ---: |
| `lock` | 50.28 [49.07] | 34.69 (136) | 41.72 [39.83] | 988 |
| `aa` | 49.54 [48.43] | 36.73 (144) | 41.72 [39.97] | 992 |
| `r1-i2-c1` | 49.63 [49.81] | 35.71 (140) | 41.28 [41.57] | 996 |
| `r1-i2-c2` | 47.22 [47.41] | 44.64 (175) | 42.59 [42.88] | 1,051 |
| `r1-i2-c3` | 55.19 [55.09] | 16.58 (65) | 39.10 [38.95] | 848 |
| `r1-i2-c4` | 51.20 [51.30] | 30.61 (120) | 40.84 [40.99] | 960 |
| `r1-i2-c5` | 51.48 [51.57] | 30.61 (120) | 41.28 [41.42] | 957 |

Raw vs normalised flips are the rows whose exact-set changes under the v3 normaliser. No arm has a parse flip.

| arm | text changed | raw false -> normalised true | raw true -> normalised false | net |
| --- | ---: | ---: | ---: | ---: |
| `lock` | 97 | 18 | 5 | +13 |
| `aa` | 101 | 17 | 5 | +12 |
| `r1-i2-c1` | 62 | 3 | 5 | -2 |
| `r1-i2-c2` | 63 | 3 | 5 | -2 |
| `r1-i2-c3` | 57 | 6 | 5 | +1 |
| `r1-i2-c4` | 57 | 4 | 5 | -1 |
| `r1-i2-c5` | 54 | 4 | 5 | -1 |

Every iteration-2 template carries c5's filler conventions. All five arms are therefore already in the delivered
surface form: the normaliser repairs -2 to +1 net rows on them against +13 on `lock`. The raw screen passes of c3,
c4 and c5 are again partly formatting. c4 drops from +24 raw to +10 normalised rows, and c5 from +27 to +13.

## 4. Per slot type and per scenario: where c3 acted, and why the gates destroyed the effect

Node-local per-slot-type totals (normalised; 944 gold entities on the roster):

| arm | gold exact | gold missing | gold wrong | predicted | spurious |
| --- | ---: | ---: | ---: | ---: | ---: |
| `lock` | 513 | 194 | 237 | 988 | 238 |
| `aa` | 511 | 197 | 236 | 992 | 245 |
| `r1-i2-c1` | 511 | 200 | 233 | 996 | 252 |
| `r1-i2-c2` | 525 | 183 | 236 | 1,051 | 290 |
| `r1-i2-c3` | 486 | 250 | 208 | 848 | 154 |
| `r1-i2-c4` | 512 | 208 | 224 | 960 | 224 |
| `r1-i2-c5` | 507 | 210 | 227 | 957 | 223 |

**r1-i2-c3 (c3 plus conventions).** It predicts 140 fewer entities than `lock`. Spurious falls by 84 and wrong by 29,
which removes FP mass. Missing rises by 56 and exact falls by 27, so values that were right are now absent.

- Exact losses concentrate on `date` (-13 exact / +14 missing), then `event_name` -4 / +5, `transport_type` -4 / +4, `place_name` -2 / +9 and `business_name` -2 / +2.
- No type gains more than one exact entity.
- The spurious cuts are spread out: `device_type` -10, `event_name` -7, `song_name` -6, `time` -6, `date` -6, `place_name` -6, `food_type` -5, `business_type` -4.
- The hypothesis was that c3's non-empty loss is MISSING, not WRONG, and that conventions would recover about 9 of its 12 rows. That is refuted. The loss is MISSING, as predicted, but it grew: normalised non-empty exact is 5 / 23 discordant rows (-18 net) against iteration 1's 10 / 22 (-12). The conventions repaired WRONG fillers (wrong -29) and recovered no MISSING value.

Per scenario (official pooled SLU-F1 within 60 rows; descriptive, wide intervals):

- Gains: `music` +7.41 [+2.06, +15.00], `iot` +6.16 [+2.85, +10.13], `cooking` +5.98 [+2.80, +9.93], `audio` +5.42 [-5.97, +16.39], `alarm` +4.25 [+0.75, +9.53].
- Losses: `transport` -3.62, `takeaway` -3.34, `calendar` -2.93, `datetime` -2.57, `weather` -1.38.
- 10 scenarios up, 8 down. As in iteration 1, the losing scenarios are the date / time / transport ones whose slot types carry the exact losses.

**r1-i2-c1 (gated after extraction): the gate erased the empty effect.**

- False fill is +1.02 [-2.30, +4.08] (22 / 18), against c3's -18.11 (0 / 71). Predicted items are 996 (lock 988) and spurious is 252 (lock 238).
- Placing the empty decision after extraction, beside a keep-list of value kinds ("a spoken day, date, time, place, name, event, condition, or kind of media, device or vehicle"), left the model filling. The keep-list reads as a licence to fill. Spurious additions spread over `definition_word` +5, `person` +3, `device_type` +3, `currency_name` +3 and `media_type` +3. Exact `place_name` fell -4, with spurious +2.
- What it did protect, the non-empty rows (-0.44, 13 / 16), c5 already protected without any gate.
- Net: a c5-like column with no empty effect, official -0.88, plus 8 intent rows.

**r1-i2-c2 (soft sentence): the sentence reversed the decision.**

- False fill rose +9.95 [+6.37, +13.78] (49 rows newly filled, 10 emptied).
- Predicted items rose +63 and spurious +52: `device_type` +9, `person` +8, `definition_word` +4, `media_type` +4, and 8 additional entities typed `none`. The sentence's "never empty when you heard a value of a type the supplied examples annotate" acts as an anti-empty instruction.
- The non-empty rows gained a little (raw exact +3.05 [+1.16, +4.94]; normalised +0.87; official entity TP +12). The per-row metric sees this gain and not the false fills.
- Per scenario the loss sits on the scenarios with many empty-gold rows: `general` -9.84 [-18.29, -3.31], `lists` -8.11 [-15.09, -2.37], `recommendation` -7.65 [-13.80, -2.44], `qa` -4.47 [-9.79, -0.46].

**The aggregate reading.** Both gates were instructions that ask the Solver to judge "heard" against the supplied
annotations. In both arms the Solver read the protective clause as a reason to fill. Only the ungated decision-first
step (c3) moved false fill, and it moved it on heard values too. Within one Solver template, a gate written as
instruction text did not separate the two cases. The decision-239 study (section 7) finds the separating signal
outside the template: the supply's entity-free share, applied as an external gate.

**r1-i2-c4 and r1-i2-c5 (for completeness).**

- c4: false fill -4.08 [-7.14, -1.02] and spurious 238 -> 224, against exact `date` -4 and `place_name` -4. Official +0.10.
- c5 (the ablation): it reproduces iteration-1 c5's raw exact-set exactly, +2.50 [+1.02, +4.07], with the contract paragraph removed. Under the candidates README's reading rule (>= about 20 raw rows means the conventions carry c5) the conventions carry the raw gain. That gain is the formatting the v3 normaliser already supplies: normalised +1.20, official -0.03.

## 5. Offline post-processing columns v4 and v4g (registered apply read `SAEA-SLURP-NX-POSTPROC-V4-APPLY-V1`)

The ten iteration-2 reports are under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-POSTPROC-V4-APPLY-V1/offline-v4/<v4|v4g>-r1-i2-c<k>/report.json`.

- Status: DESCRIPTIVE.
- Driver: `scripts/analysis/slurp_nx_postproc_v4_apply.py` `4b979a8a...`.
- Admission: Fold B is admitted by this cell's recipe `2bb0d7d6...`. The pool is this run.
- Contacts: model 0 and GPU 0, with two registered-scorer-on-copy runs each.
- Base: the arm's v3-normalised column.
- Paired whole-utterance bootstrap: 1,080 clusters, 10,000 draws, seed 20260915.
- Neither normaliser moves an intent label: the intent delta is 0.00 [0.00, 0.00] on all ten.

**Coverage.** The apply read covers the five candidate columns of this run only. The folders `v4-lock`, `v4-aa`,
`v4g-lock` and `v4g-aa` hold iteration 1's run (`pool.run_id` `SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1`; v4g-lock
`7f2d22be...`, the lock confirmation). The write-once driver did not re-apply them to this run's `lock` and `aa`
columns. For this run's `lock` and `aa`, the v4g levels below come from the decision-239 offline study's exact
in-process re-score (`SAEA-SLURP-NX-R6-UPSTREAM-EMPTY-OFFLINE-V1`, which reproduces each sealed official column
on 1,080 / 1,080 rows). They are not registered apply reports.

| arm X | X official SLU-F1 | v4(X) - X pp [CI95] (rows edited) | v4(X) SLU-F1 | v4g(X) - X pp [CI95] (rows edited) | v4g(X) SLU-F1 | equal-scenario v4 -> v4g | audio v4 / v4g (rows edited) | v4g(X) - lock, point | v4g(X) - v4g(lock), point |
| --- | ---: | --- | ---: | --- | ---: | --- | --- | ---: | ---: |
| `lock` | 63.43 | not applied to this run | - | (239 study: 64.86) | 64.86 | - | - | +1.43 | 0 |
| `aa` | 63.00 | not applied to this run | - | (239 study: 64.41) | 64.41 | - | - | +0.98 | -0.45 |
| `r1-i2-c1` | 62.55 | +1.22 [+0.43, +1.99] (116) | 63.77 | +1.51 [+0.84, +2.19] (101) | 64.06 | +0.42 -> +1.59 | -23.72 (8) / +2.41 (2) | +0.63 | -0.80 |
| `r1-i2-c2` | 62.53 | +1.81 [+1.02, +2.62] (137) | 64.33 | +1.81 [+1.10, +2.52] (117) | 64.34 | +1.16 -> +1.88 | -17.73 (12) / +6.92 (6) | +0.91 | -0.52 |
| `r1-i2-c3` | 64.17 | +0.23 [-0.46, +0.92] (70) | 64.40 | **+0.77 [+0.21, +1.32]** (59) | 64.94 | -0.69 -> +0.93 | -28.43 (6) / 0.00 (0) | +1.51 | **+0.08** |
| `r1-i2-c4` | 63.53 | +0.99 [+0.24, +1.75] (105) | 64.52 | +1.41 [+0.75, +2.08] (94) | 64.94 | -0.08 -> +1.40 | -26.38 (7) / +1.44 (1) | +1.51 | +0.08 |
| `r1-i2-c5` | 63.40 | +0.91 [+0.18, +1.63] (100) | 64.32 | +1.33 [+0.69, +1.97] (89) | 64.73 | +0.26 -> +1.69 | -24.58 (8) / +2.66 (2) | +1.30 | -0.13 |

The last two columns are arithmetic on absolute levels of the same 1,080 rows. They were not bootstrapped and are not
nomination inputs. The 239 study bootstraps the c3 one: aggressive arm everywhere on v4g, i2, +0.08 [-1.10, +1.29].
Rows applied: 1,080 (c5 1,079, one unparsed row left unmodified).

- **v4g carries every arm.** v4g(X) - X has CI95 lower bound > 0 on all five candidates. It again gains least on `r1-i2-c3` (59 rows edited, no audio row edited, +0.77): c3's empty decision overlaps what v4g's `ee10` and `ti1` remove downstream.
- **On the v4g base no Solver arm beats the lock.** v4g(i2-c3) and v4g(i2-c4) tie v4g(lock) at the point (+0.08). The others are below it.
- **The audio guard holds on this run.** Unguarded v4 loses the `audio` stratum on every candidate (-17.73 to -28.43). v4g turns that into +0.00 to +6.92.

## 6. Cross-iteration contrast (DESCRIPTIVE; DIFFERENT FLIGHTS; non-gating)

The recipe's step 2b, `stage3_paired_read.py` with left = iteration 1 and right = iteration 2, left six pass
directories under `cross-iteration/` (`lock-vs-i1-lock`, `r1-i2-c<k>-vs-i1-r1-c5`). **All six are empty.** This is
consistent with the driver's non-gating failure branch ("cross-iteration ... FAILED; non-gating, the read continues").
The read log was not inspected by this note, and no bootstrapped cross-flight number is on file. The table below is
therefore point arithmetic on the two flights' official levels: iteration 1 from its `supply-variants/score-summary.json`
`8a5de8ac...`, iteration 2 from `2ae8cd4e...`.

| contrast | i2 level | i1 level | difference pp (point) | minus the flight offset (lock - lock) | same-flight i2 delta vs lock (section 2) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `lock` - i1 `lock` (flight offset) | 63.43 | 62.13 | **+1.30** | 0 | - |
| `r1-i2-c1` - i1 `r1-c5` | 62.55 | 61.98 | +0.57 | -0.73 | -0.88 |
| `r1-i2-c2` - i1 `r1-c5` | 62.53 | 61.98 | +0.55 | -0.75 | -0.90 |
| `r1-i2-c3` - i1 `r1-c5` | 64.17 | 61.98 | +2.20 | +0.90 | +0.74 |
| `r1-i2-c4` - i1 `r1-c5` | 63.53 | 61.98 | +1.55 | +0.25 | +0.10 |
| `r1-i2-c5` - i1 `r1-c5` | 63.40 | 61.98 | +1.42 | +0.13 | -0.03 |

The same `lock` template on the same 1,080 rows reads +1.30 pp apart across the two flights. The twin moved from
+0.57 to -0.43. A cross-flight difference of this size is therefore within flight-to-flight variation. Once the offset
is removed, each row equals its same-flight delta plus 0.15. That is an identity, because iteration-1 c5 sat 0.15 below
its own `lock`. The cross-flight view therefore adds no information beyond the two same-flight tables: no iteration-2 arm
is distinguishable from iteration 1's c5 by more than what those tables already say.

Node-local, read by hand from the two on-file reports (normalised exact-set levels, different flights): i1 `lock` 49.81
and `r1-c5` 51.11; i2 `lock` 50.28, c1 49.63, c2 47.22, c3 55.19, c4 51.20, c5 51.48. The i2-c3 node gain (+4.91) is
about iteration-1 c3's (+4.63). Every view is consistent: a second round of templates did not move the official
column beyond the first.

## 7. Verdict under the registered rule

Rule (package README section 5): NOMINATED iff all three hold:

- (a) the official pooled SLU-F1 delta vs `lock` has CI95 lower bound > 0;
- (b) that delta exceeds the `aa` twin's delta (-0.43);
- (c) the intent guard holds: rows whose official intent correctness differs from `lock` <= 7.

HARM iff the CI95 upper bound < 0.

| arm | (a) CI-LB > 0 | (b) delta > -0.43 | (c) intent rows <= 7 | HARM (UB < 0) | verdict |
| --- | --- | --- | --- | --- | --- |
| `r1-i2-c1` | no (-2.04) | no (-0.88) | no (8) | no (UB +0.28) | **NOT NOMINATED** |
| `r1-i2-c2` | no (-2.07) | no (-0.90) | no (8) | no (UB +0.27) | **NOT NOMINATED** |
| `r1-i2-c3` | no (-0.43) | yes (+0.74) | yes (7) | no (UB +1.94) | **NOT NOMINATED** |
| `r1-i2-c4` | no (-0.97) | yes (+0.10) | yes (6) | no (UB +1.19) | **NOT NOMINATED** |
| `r1-i2-c5` | no (-0.97) | yes (-0.03) | yes (5) | no (UB +0.93) | **NOT NOMINATED** |

**Every arm is NOT NOMINATED, and none is HARM.** The round's declared effect, +1.54 pp official pooled SLU-F1 class-split
carried by `r1-i2-c3`, was not met: the carrier reads +0.74, half of it, unresolved. The node-local raw count of the
carrier exceeded its prediction (+65 rows against +48). Its class-split conversion on the measured classes is
71 x 0.0333 - 18 x 0.0563 = +1.35 pp, which still over-predicts the column by about 0.6 pp.

**The plateau rule closes the Solver-template line.** This was the second and last evaluated round (programme C0.4).
No arm of either round is NOMINATED, so the delivering template is locked and the node closes.
`configs/probes/slurp_native_role_solver_v2.txt` (sha256 `18bff5c5...`) **stays the Solver lock**. No Fold A two-arm
confirmation is registered.

**The empty-entity decision moves upstream (owner decision 239, 2026-10-10).** The Solver template line closes, but
the empty-entity decision does not. It becomes round R6, designed offline first. The 239 offline study
(`docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md`, on branch `fable/nx-r6-upstream-empty`,
not yet on master) recommends, in three lines:

1. Perception's note carries no entity information today. `unresolved_fields` and `evidence_refs` are empty on all 1,080 rows of both flights (AUC exactly 0.5). The supply's entity-free exemplar share N1 is the best gold-free signal (AUC 0.856).
2. The core's own empty verdict, gated by N1 >= 0.2, reads **+0.75 [+0.27, +1.24] (i1) / +0.98 [+0.50, +1.48] (i2) pp on the v4g base, with 0 intent rows changed**. It removes 27 / 33 false fills and loses 3 non-empty exact rows per flight. This makes R6 (A) a Perception-side presence verdict consumed at delivery with the N1 gate. Its Perception verdict quality is still unmeasured, and the prediction is below the 1.5 pp bar.
3. A deterministic v5 (v4g plus "empty when the signal fires", zero GPU) fails. The A2-selected N1 >= 0.6 rule gives Fold B +0.04 [-0.23, +0.29], and no grid point clears 0.67 pp on any pool.

## 8. Lessons

1. **Per-row and pooled disagree whenever a mechanism changes how often the Solver answers empty.** This round shows the effect in both directions. c3 has per-row -2.56 and pooled +0.74. c2 has per-row +0.77 (CI-LB -0.06) and pooled -0.90. The per-row mean scores every empty-gold row 0 and is not this programme's estimand. It must never be read as a gain or a loss on its own.
2. **Two in-template gates failed in two different ways.** The post-extraction keep-list (c1) erased the empty effect: false fill +1.02 against c3's -18.11. The soft sentence (c2) reversed it: +9.95. Text that asks the Solver to judge whether a value was heard did not separate empty-gold rows from short heard values. The separating signal on file is a supply statistic applied outside the template (decision-239 study).
3. **Conventions do not recover a MISSING loss.** The i2-c3 hypothesis predicted the non-empty loss would shrink from -12 to about -3 rows. It grew to -18 (normalised), on `date` above all. The empty decision ungated deletes heard dates and times.
4. **The ablation attributes c5 cleanly, and the gain is formatting.** Raw exact-set is +2.50 with or without the contract paragraph, so the conventions carry it. The v3 normaliser already delivers it: normalised +1.20, official -0.03.
5. **The in-flight twin is the only bar.** The twin moved from +0.57 to -0.43, and the same `lock` moved +1.30 pp across flights. A cross-flight point difference of +2.20 (i2-c3 vs i1 c5) means nothing without the same-flight read.
6. **Cost and yield.** The template line flew two rounds of 1,080 rows x 8 contacts: 17,280 arm contacts, 2.08 + 2.08 monitored GPU-h for the two arm flights, and about 7 GPU-h of planned ceilings including the smokes. It produced the diagnosis, not a lock. That diagnosis is: the empty-entity decision is the lever, measured at -16 to -18 pp false fill; inside the Solver it cannot be gated; and on the v4g delivery the template arms add nothing (+0.08 at best).
7. **v4g is the composition's delivery.** v4g(X) - X is CI-LB > 0 on all twelve registered columns on file (iteration 1's seven, iteration 2's five candidates). The R5 composed read (decision 240) already carries v4g and the v2 Solver template unchanged.

## 9. Reproduce

Run from the study root in WSL (`source ~/.venvs/speechrl/bin/activate`; `SPEECHRL_DATA_DIR` set). The read is
model-free and refuses unless the READ row is root countersigned. A pass directory that already holds files is never
overwritten.

```bash
# identities only; opens no gold, runs no scorer
bash scripts/analysis/nx_r1_read.sh --iteration 2 --dry-run
# the registered read: node-local v2, seven official column scorings (idempotent), aa-vs-lock and <candidate>-vs-lock,
# the DESCRIPTIVE cross-iteration pass (step 2b, non-gating) and the offline v4 / v4g columns
bash scripts/analysis/nx_r1_read.sh --iteration 2
# verify the on-file bytes quoted above
A=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-COLUMN-READ-V1
R=$SPEECHRL_DATA_DIR/runs/SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-V1/attempt-slurp-native-stage3-nx-r1-i2-solver-fold-b-generation-v1
sha256sum $A/node-local/report.json $A/node-local/tables.md $A/*-vs-lock/score-contrasts.json \
  $R/supply-variants/score-summary.json $R/SAEA-SLURP-STAGE3-NX-R1-I2-SOLVER-FOLD-B-V1.outputs.jsonl \
  $SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-POSTPROC-V4-APPLY-V1/offline-v4/*-r1-i2-*/report.json
```

Offline report sha256 (under `offline-v4/`): v4-r1-i2-c1 `7eaa637a...`, v4g-r1-i2-c1 `72fff142...`, v4-r1-i2-c2
`b92c8388...`, v4g-r1-i2-c2 `65309e1c...`, v4-r1-i2-c3 `c7bfe706...`, v4g-r1-i2-c3 `6344db4b...`, v4-r1-i2-c4
`18a14ff6...`, v4g-r1-i2-c4 `ddd57980...`, v4-r1-i2-c5 `15d5ebdf...`, v4g-r1-i2-c5 `dc436001...`.
