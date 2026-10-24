# NX-T R2, the per-node reasoning-budget column on the Thinking core (TRAIN Fold B, n = 1,080, rec2 mode-A resume): perception-off-solver-3072 UNRESOLVED (SLU-F1 -1.49 [-2.83, -0.11]); solver-2048 UNRESOLVED (-0.94 [-2.32, +0.45]); R1's Perception no-think NO-RESOLVED-LOSS does not replicate; development numbers, claims_benefit false

Read 2026-10-24 by Claude Opus 5.5 (results-note agent, on the coordinator's brief) in the ext4 worktree branch `opus/nxt-r2-note` (base master `e28a95a66`). Model-free: this note opened no model, server, encoder, embedder, tokenizer, scorer or GPU, and wrote nothing under the data root. It reads the aggregate files of the registered read `SAEA-SLURP-NXT-R2-THINKING-BUDGET-FOLD-B-READ-V1` (`read.json`, `README.md`, `columns/score-summary.json`), the package `docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1/` (README with the rec1 / rec2 sections, `analysis-recipe-v1.json`, `resume-replay-proof-rec2-v1.json`), its preregistration, the exposure-ledger blocks of cell NXT-R2 and the registry sections named in section 9. For sections 3 and 5 it opened the `per_sample` arrays of the official column score files of this read, of the NX-T R1 read and of the R2b read, and counted rows by `sample_id` and numeric score flags only. No utterance text, transcript, gold value, slot filler, model output or reasoning text was read, printed or persisted. Numbers marked "derived" are ratios, sums or differences of numbers printed in those files.

**Status: DESCRIPTIVE, development numbers on TRAIN Fold B (`SLURP-EVO-FOLD-B-V2`, n = 1,080, discovery role; owner decisions 28 and 86). Never a test claim. `claims_benefit` is false.** `read.json` `status` verbatim: "PREREGISTERED-READ (development numbers; never a test claim; claims_benefit false)". A per-node cost attribution on the selection fold (owner rulings 304/307, 313 A, 318 A), not an admission, a lock or a benefit claim (`analysis-recipe-v1.json` `claim_boundary`: "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim."). The node words are the reader's, fixed at registration: **GAIN / NEEDS-FULL-BUDGET / CHEAPER-AT-NO-RESOLVED-LOSS / UNRESOLVED** (first that applies).

## 0. Answer in six lines

1. **Perception no-think (`perception-off-solver-3072`): UNRESOLVED.** SLU-F1 **-1.49 pp [-2.83, -0.11]**, intent **+0.65 [-0.65, +2.04]** (32 saves / 25 harms) against the delivering lock form `budget-3072` (72.21 SLU / 84.91 intent -> 70.72 / 85.56). The SLU interval excludes zero (a loss resolved against 0) but not -|o| = -1.15; the lower bound -2.83 fails the -1.49 floor of CHEAPER-AT-NO-RESOLVED-LOSS.
2. **Solver at 2,048 (`solver-2048`): UNRESOLVED.** SLU **-0.94 [-2.32, +0.45]**, intent **+0.46 [-0.56, +1.48]** (19 / 14); 71.27 / 85.37. The SLU lower bound fails the same floor.
3. **R1 does not replicate.** NX-T R1 (2026-10-17) read the same Perception no-think form on the same roster at -0.19 [-1.69, +1.29] (NO-RESOLVED-LOSS, no floor word). Both reads fail the -1.49 floor; what moved is the point (-0.19 -> -1.49, 1.30 pp apart, derived, about the declared A/A offset 1.15) and the interval now excludes zero (section 3).
4. **Cost per node (1,054 flown rows):** Perception thinking 62.1 s per contact (forced-close share 0.199) vs no-think 3.4 s; Solver 68.0-70.6 s at 3,072 (forced 0.45-0.46) and 52.1 s at 2,048 (forced 0.50). Row cost: 130.0 s delivering, 74.0 s perception-off (-43.1 %), 114.4 s solver-2048 (-12.0 %).
5. **Consequence (coordinator, registry 2026-10-24 15:35Z):** the 324-B Fold A confirm does NOT fly (331 A / 334 B condition "no resolved loss" unmet); the composed lock keeps Perception thinking at 3,072 / 4,096 and the Solver at 3,072 / 4,096 (R2b: 6,144 NEEDS-NO-MORE-BUDGET; 2,048 UNRESOLVED, no saving adopted).
6. **Flight cost:** rec2 ran 2026-10-18 14:37:33Z -> 2026-10-20 11:27:54Z (44 h 50 min, derived) against about 23.5 h expected, because a degraded power plug held the GPU at its 95 W default cap; a cost note, not a result caveat (section 7).

## 1. Identities

| item | value |
| --- | --- |
| cells | smoke `slurp-native-stage3-nxt-r2-thinking-budget-fold-b-smoke-4-v1` (sealed 2026-10-17 10:56:47Z, not re-flown); column `slurp-native-stage3-nxt-r2-thinking-budget-fold-b-v1`, run `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1`, attempt `attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-rec2-v1`, FIT run `...-FOLD-B-FIT-REC2-V1`; read run `SAEA-SLURP-NXT-R2-THINKING-BUDGET-FOLD-B-READ-V1`, recipe `slurp-nxt-r2-thinking-budget-fold-b-read-v1`, schema `saea-nxt-r2-thinking-budget-column-read-v1` |
| authority | owner rulings 304/307, 313 A, 318 A; arm table decided 2026-10-17 10:37Z under the rule "R1's answer decides the arm table"; recoveries: 309 A (rec1), 328 (rec2, explicit exception to the one-recovery rule) |
| system | the 268-B Thinking lock cell (lock v2.2, plain review-off COMP-1b module graph) plus the Perception `thinking_variants` block; program `phase-native-module-v1-c6` (6 contacts per row: 3 arms x Perception + Solver) |
| core and session | Qwen3-Omni-30B-A3B-Thinking Q4_K_M, decoder-only build `04ccc72a`; fragment `q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max4096-v1`; session swap target `think-budget-np4` (4 slots x 24,576, q8_0 KV, `--reasoning-format deepseek`) |
| arms (declared order, delivering last; no twin) | `perception-off-solver-3072`: Perception `enable_thinking` false (max_tokens 1,024), Solver 3,072 / cap 4,096; `solver-2048`: Perception 3,072 / 4,096, Solver **2,048** / reserve 2,048 / cap 4,096; `budget-3072` (DELIVERING, the 268-B lock form). All: `drop-reasoning-v1`, temperature 0, seed 20260913, the registered forced-close message. Independent chains: each arm's Solver reads its own arm's Perception note |
| roster / scorer | `SLURP-EVO-FOLD-B-V2` (`docs/receipts/rosters/slurp-evo-fold-b-v2.json` sha256 `47b89b9e...`), split identity `4407794c...`, 1,080 rows, 18 scenarios x 60; `slurp-slu-official-train` (pinned official `evaluate.py`), one complete scoring per arm (`contacts.scorer` = 3) |
| null and floors | no twin (313 A); declared A/A offset |o| = 1.15 pp SLU ("the larger of the two measured same-core A/A offsets": 268-B +1.15 / intent -0.09, P3.1 -0.61 / +1.6); paired floor 0.7 pp (declared; no word rule uses it); decision-190 floors 1.49 SLU / 0.65 intent |
| resampling | paired utterance-cluster bootstrap, 10,000 draws, seed 20261015, CI95 |
| seal | manifest `8cc011418c8a8a4c2014aa25e339fea7bd3ccd336e09610f73a263c22959d3d5`; outputs `7ca3c77bda63cf6505b75e5fead7515dd25c670d06105fa6f685135a54d03095`; trace `e8404fa3dba4d0b790331d66d52ba617ca86c08130d82402bf4b0fc6e08d654e`; sealed delivered scores `1fa202aa...`; config `2ac21f2c...`; flight commit `394f4a760` |
| read sequence (UTC) | columns stage `score-summary.json` 15:15:53Z (prints no number); READ row countersigned `96a8e2974` 15:17:29Z (gate-form phrase `5e7e5c661` 15:19:49Z); `read.json` 15:20:38Z; row consumed in `e28a95a66` |

## 2. The contrast

| arm | Perception / Solver | SLU-F1 % | SLU delta pp [CI95] | intent % | intent delta pp [CI95] | intent saves / harms / ties | absent rows | word |
| --- | --- | ---: | --- | ---: | --- | --- | ---: | --- |
| budget-3072 (delivering) | 3,072 / 3,072 | 72.21 | -- | 84.91 | -- | -- | 0 | -- |
| perception-off-solver-3072 | no-think / 3,072 | 70.72 | **-1.49 [-2.83, -0.11]** | 85.56 | **+0.65 [-0.65, +2.04]** | 32 / 25 / 1,023 | 0 | **UNRESOLVED** |
| solver-2048 | 3,072 / **2,048** | 71.27 | **-0.94 [-2.32, +0.45]** | 85.37 | **+0.46 [-0.56, +1.48]** | 19 / 14 / 1,047 | 0 | **UNRESOLVED** |

Full precision (`contrast.versus_delivering`): perception-off SLU -1.4883 [-2.8325, -0.1100] (half-width 1.36), intent +0.6481 [-0.6481, +2.0370]; solver-2048 SLU -0.9375 [-2.3234, +0.4508] (1.39), intent +0.4630 [-0.5556, +1.4815]. Official counts (`score-summary.json` `official.raw`): SLU-F1 TP / FP / FN 1,590 / 692.97 / 530.97 (delivering), 1,560 / 750.89 / 540.89 (perception-off), 1,570 / 725.87 / 539.87 (solver-2048); exact entities 617 / 408 / 327, 618 / 431 / 326, 618 / 419 / 326; intent correct 917, 924, 922. Derived, arm minus delivering: perception-off TP **-30**, FP **+57.92**, FN +9.92; solver-2048 TP -20, FP +32.90, FN +8.90. Both cheaper arms lose slot precision and some recall; intent moves the other way by 7 and 5 rows.

**Applying the word rule** (`analysis-recipe-v1.json` `word_rules`). GAIN needs the SLU lower bound > +1.15: no for both. NEEDS-FULL-BUDGET needs the SLU upper bound < -1.15: -0.11 and +0.45, no. CHEAPER-AT-NO-RESOLVED-LOSS needs SLU lower bound >= -1.49 and intent lower bound >= -0.65: SLU -2.83 and -2.32 fail (the intent clauses hold, perception-off's -0.648 by 0.002 pp, under one row). -> **UNRESOLVED** for both, as `node_words.words.*.word` states. The perception-off point -1.4883 equals the 1.49 floor magnitude.

## 3. R1 against R2: the same Perception no-think form, read twice on the same roster

| reading | R1 (read 2026-10-17, rec2) | R2 (read 2026-10-24, rec2) |
| --- | --- | --- |
| delivering lock form, SLU / intent | 72.35 / 85.74 (both-on) | 72.21 / 84.91 (budget-3072) |
| Perception no-think arm, SLU / intent | 72.16 / 85.28 (`perception-off`) | 70.72 / 85.56 (`perception-off-solver-3072`) |
| paired SLU [CI95] / intent [CI95] | -0.19 [-1.69, +1.29] / -0.46 [-1.76, +0.83] | -1.49 [-2.83, -0.11] / +0.65 [-0.65, +2.04] |
| intent saves / harms; SLU TP / FP / FN vs delivering | 24 / 29; -6 / -4.54 / +11.46 | 32 / 25; -30 / +57.92 / +9.92 |
| equal-scenario SLU delta | -0.32 | -1.66 |
| word (its own vocabulary) | NO-RESOLVED-LOSS; NOT-NEEDED-AT-THE-FLOOR not attached | UNRESOLVED |
| program, null | 5 arms, 10 contacts per row, in-flight twin |o| = 0.12 | 3 arms, 6 contacts per row, declared |o| = 1.15 |

Why the two reads differ (derived; stated, not claimed):
- **Not a change of rule.** Under R2's rule R1's interval also reads UNRESOLVED (lower bound -1.69 < -1.49); R1 never cleared the floor (R1 note section 2; registry correction 2026-10-17 10:51Z). The 324-B condition was "no resolved loss"; R2's upper bound -0.11 now resolves a loss against zero.
- **The candidate arm moved, the delivering arm did not.** Cross-flight, the lock form moved -0.14 SLU (72.35 -> 72.21) and the no-think arm -1.44 (72.16 -> 70.72); the six lock-form readings on this roster still span 71.61-72.75 SLU (268-B lock and twin, R1 both-on and twin, R2b and R2 delivering). The intent sign flip comes from the delivering arm (926 -> 917 correct), not the no-think arm (921 -> 924).
- **Same roster, same registered form, different decode.** "greedy decoding at temperature 0 is not reproducible under np4 batching" (registry 2026-10-18 15:30Z); inside this flight the two same-form Perception columns differ by 20 forced closes (section 4). R1 flew 5 arms in a 10-contact program and R2 3 arms in a 6-contact one, so every request met different batch neighbours. The two point estimates are 1.30 pp apart, about the declared A/A offset 1.15 pp that 313 A sets as the width of exactly this jitter.
- **Row-level deltas do not replicate.** Same-form cross-flight discordance: no-think arm R2 vs R1 35 intent rows / 61 exact-slot rows; lock form R2 vs R1 45 / 62; R1's in-flight twin 24 / 52. Of the 70 rows whose per-row SLU-F1 delta is nonzero in both reads, 31 share its sign; the per-row delta correlation is 0.02; scenario signs agree in 11 of 18 (audio and play lose in both).

## 4. Per-node cost and forced closes (the 1,054 flown rows; `arms_nodes`)

| arm | node | mode / budget (cap) | contacts | completion tokens mean / p50 / p90 / p99 | forced closes (share) | prompt tokens mean | reasoning chars mean | s per contact mean / p50 / p99 |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| budget-3072 | perception | think 3,072 (4,096) | 1,054 | 2,063.5 / 1,952.5 / 3,155.7 / 3,196.5 | **210 (0.199)** | 3,589.1 | 9,146 | **62.08** / 59.85 / 109.68 |
| budget-3072 | solver | think 3,072 (4,096) | 1,054 | 2,072.9 / 2,171.5 / 3,131.0 / 3,144.9 | **474 (0.450)** | 8,621.8 | 8,622 | **67.96** / 66.52 / 123.85 |
| perception-off-solver-3072 | perception | no-think (1,024) | 1,054 | 90.9 / 92 / 99 / 107 | 0 | 3,593.1 | 0 | **3.40** / 3.28 / 7.32 |
| perception-off-solver-3072 | solver | think 3,072 (4,096) | 1,054 | 2,014.7 / 1,902.0 / 3,131.0 / 3,145.5 | **487 (0.462)** | 10,519.3 | 8,410 | **70.56** / 65.12 / 129.95 |
| solver-2048 | perception | think 3,072 (4,096) | 1,054 | 2,051.7 / 1,988.0 / 3,142.2 / 3,194.5 | **190 (0.180)** | 3,589.1 | 9,100 | **62.28** / 59.52 / 112.59 |
| solver-2048 | solver | think **2,048** (4,096) | 1,054 | 1,573.0 / 2,038.0 / 2,108.0 / 2,123.5 | **522 (0.495)** | 8,594.7 | 6,508 | **52.10** / 58.42 / 84.99 |

Every node: finish `stop` 1,054, 0 cap hits, 0 empty, 0 no-JSON, 0 think markers in content; every thinking node 1,054 contacts with reasoning characters, every no-think node 0; `reasoning_marker_total` 0; 0 reasoning leaks in 1,080 delivered answers; 0 unattributed contacts. The 26 kept rows' contacts live in the rec1 trace, which these tables do not read. Reading it (derived):
- **Perception no-think removes 58.7 of 62.1 s per row's Perception contact** and lengthens the Solver prompt by 1,897 tokens (10,519 vs 8,622): the no-think note is longer after `drop-reasoning-v1`, as in R1 (+2,225). Its Solver then forced-closes slightly more (0.462 vs 0.450).
- **The Solver at 2,048 runs to its budget on about half the contacts** (p50 2,038 of 2,048; forced 0.495 vs 0.450); mean completion -24 %, seconds -23 %.
- **Same-form A/A-like readout:** the Perception requests of `budget-3072` and `solver-2048` share their form; they differ by 20 forced closes (210 vs 190), 11.8 mean tokens and 0.2 s. The Solver's forced share at 3,072 reads 0.450 here against 0.401 in R2b (same form, cross-flight).

| arm | s per row | rows per minute (4 slots) | GPU-h per 1,080-row lock flight | at the 1.84 rows/min reference | cost in delivering rows (measured / registered) | saving |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| budget-3072 | 130.0 | 1.85 | 9.75 | 9.78 | 1.00 / 1.0 | 0.0 % |
| perception-off-solver-3072 | 74.0 | 3.25 | 5.55 | 5.56 | 0.57 / 0.53 | 43.1 % |
| solver-2048 | 114.4 | 2.10 | 8.58 | 8.60 | 0.88 / 0.93 | 12.0 % |

Measured arm mix 2.45 delivering rows per row (registered 2.46); one flight 23.88 GPU-h (ceiling 31.3). These figures are call latency (slot-normalised), not wall time (section 7). Neither saving is adopted: no arm reads CHEAPER-AT-NO-RESOLVED-LOSS.

## 5. Per scenario (18 x 60 rows; point deltas, no scenario CI in the read; R1 column from the R1 `read.json`)

| scenario | SLU budget-3072 % | SLU d perception-off pp | R1 SLU d perception-off pp | SLU d solver-2048 pp | intent budget-3072 % | intent d perception-off pp | intent d solver-2048 pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 75.51 | +2.98 | +3.09 | +0.63 | 90.00 | +1.67 | +0.00 |
| audio | 71.19 | -6.98 | -11.65 | +2.22 | 83.33 | +3.33 | +0.00 |
| calendar | 71.50 | -0.92 | +1.09 | -0.28 | 83.33 | +0.00 | -1.67 |
| cooking | 71.83 | -0.66 | -1.73 | +2.19 | 83.33 | +0.00 | -1.67 |
| datetime | 74.77 | +1.42 | +1.46 | +0.95 | 96.67 | +0.00 | +1.67 |
| email | 69.64 | +5.58 | +0.20 | +4.14 | 93.33 | +0.00 | +0.00 |
| general | 64.64 | -1.00 | -3.09 | -10.06 | 36.67 | +10.00 | +0.00 |
| iot | 71.32 | +2.37 | -3.75 | +4.24 | 88.33 | +1.67 | +3.33 |
| lists | 66.04 | -4.54 | -0.39 | -2.13 | 86.67 | +3.33 | +1.67 |
| music | 54.45 | -1.12 | +12.45 | -2.40 | 81.67 | -5.00 | +1.67 |
| news | 74.23 | -8.05 | -0.78 | -3.24 | 90.00 | -1.67 | -3.33 |
| play | 60.64 | -9.61 | -4.91 | -2.69 | 81.67 | -6.67 | +1.67 |
| qa | 79.35 | -5.64 | -2.19 | -6.16 | 85.00 | +1.67 | +3.33 |
| recommendation | 68.45 | -0.47 | +3.94 | -4.70 | 86.67 | +0.00 | -1.67 |
| social | 74.83 | -3.77 | +3.69 | -3.09 | 90.00 | +1.67 | +1.67 |
| takeaway | 68.69 | +4.88 | -1.21 | +3.15 | 85.00 | +3.33 | +0.00 |
| transport | 75.94 | -2.16 | +1.13 | -2.70 | 88.33 | -1.67 | +1.67 |
| weather | 85.34 | -2.14 | -3.04 | +0.10 | 98.33 | +0.00 | +0.00 |

Weightings (`per_scenario`): natural mixture -1.49 (perception-off) / -0.94 (solver-2048); equal-scenario **-1.66 / -1.10**; same sign. Derived counts: perception-off SLU down in 13 of 18 scenarios, solver-2048 in 10. The largest perception-off losses (play -9.61, news -8.05, audio -6.98, qa -5.64) are all far inside the 60-row scenario swing this core shows (R1's in-flight twin moved music +13.93).

## 6. Resume accounting (rec2, mode A)

| item | value |
| --- | --- |
| rows | **1,080 = 26 kept + 1,054 flown** (`resume.rows` / `kept` / `flown`; mode `trace`); kept and flown rows are never separated in a contrast |
| kept rows | from `attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-rec1-v1` (ABORTED 2026-10-17 about 13:42Z: a serving-task registration started a second server whose reaper killed the resident one; coordinator error, not the cell); kept-row id hash `d7f17639ee8afb68c2a403d3f082cdda9c787f69a9d61c9a6315b8fb7a4ca1b9`; predecessor trace `add8fb93cd4096787e5ae559c3374ec77edff4f9145499ecf986c4c458473813` |
| flown rows | 1,054 (4 partial rows of rec1 re-flown + 1,050 never started); 6,324 program contacts = 1,054 x 6 |
| why mode A | the rec1 row checkpoint binds the protocol hash, which covers the attempt id, so no new attempt can resume it (mode B); the trace pin has no such binding and holds the same complete-row set |
| replay proof | `resume-replay-proof-rec2-v1.json` (2026-10-17T15:05Z, code `b147641b2`): 26 rows re-rendered through the seal stage, 0 failing, 0 sealed twice; kept-row note parse status `solver-2048:duplicates-collapsed` 2 / 26 |
| spend (ledger, CONSUMED) | 6,324 contacts, 18,507.2 speech-audio seconds, 93.22 summed call-latency hours; manifest COMPLETED, attempt FINALIZED, sealed 2026-10-20T11:27:54Z; run-cumulative caps 12,094 calls / 35,317 s (11,880 registered + 42 first attempt + 172 rec1); ceiling 31.3 GPU-h |
| attempts | first attempt OPENED (host reboot about 12:52Z, 42 calls); rec1 ABORTED (172 calls; owner decision 309 A); rec2 FINALIZED (owner ruling 328, the explicit exception) |

## 7. Flight-cost note (not a result caveat)

- **Wall time.** Chain started by hand 2026-10-18 14:36:38Z (the queue hook had refused on a false `refus` match), arm-start 14:37:33Z, seal 2026-10-20 11:27:54Z (chain exit 11:29:29Z): **44 h 50 min** against the 23.5 h the registration estimated (registry 2026-10-24 13:30Z). Average 2.35 contacts per minute (about 1.9 in the second half) against R2b's 4.8 (registry 15:35Z).
- **Cause.** The laptop ran on a degraded power plug; the card was held at its 95 W default power limit. After the plug change of 2026-10-24 it reports 175 W, and R3 runs at 5.0 contacts per minute at 158-161 W. The GPU then idled 2026-10-20 11:29Z -> 2026-10-24 (322 window: `wsl --shutdown` detached the data VHDX; fixed `8b27c67ce`).
- **Where it shows (derived).** The read's per-contact latencies are only 5-6 % above R2b's same-form contacts (Perception 62.1 vs 59.0 s, Solver 68.0 vs 64.1 s), while 93.22 summed latency-hours / 4 slots = 23.3 h against 44.8 h of wall time. The slowdown sits in wall time, not in the latency the throughput table uses; the read does not decompose it.
- **Why not a result caveat.** Greedy decoding (temperature 0, fixed seed); the power limit changes no request byte, and timing is not an input. It can change batch timing, which is the same np4 batch-composition jitter every flight carries and the declared offset covers (section 3).

## 8. Consequences and limits

- **324-B does not fly.** Rulings 331 A and 334 B made the Fold A confirm of Perception no-think conditional on this replicate reading no resolved loss; it reads a loss resolved against zero (UNRESOLVED). Per 334 B / 335 B the Fold A confirm batch therefore carries no Perception no-think arm.
- **Composed lock v3.x keeps both nodes at 3,072 / 4,096.** Perception thinking stays (no saving adopted despite the 43 % row saving); the Solver stays at 3,072 (R2b: 6,144 NEEDS-NO-MORE-BUDGET; here 2,048 UNRESOLVED). The per-node cost table stands as the measured cost of the lock form.
- **Not shown.** That Perception reasoning helps: the loss is resolved against zero only, not beyond |o|, and R1 read -0.19 on the same rows. With R1's in-flight |o| = 0.12 the word would still be UNRESOLVED (upper bound -0.110 is not below -0.121, by 0.011 pp, derived).
- **Development numbers on TRAIN Fold B, never a test claim** (owner decisions 28 and 86); one roster, the selection fold; `claims_benefit` false.
- **No twin; the null is declared** (313 A). No in-flight readout separates the arms' effect from this flight's jitter except the Perception same-form pair of section 4.
- **Independent chains.** The perception-off arm measures Perception no-think together with its longer note's effect on the Solver (+1,897 prompt tokens).
- **Decode tables cover the 1,054 flown rows only;** forced closes are counted, not linked to correctness. One scorer parse failure on `solver-2048` (`scorer_parse_failures`), scored as the scorer returns it; 0 absent rows on every arm.
- **Cross-flight comparisons (section 3) are descriptive;** they carry no interval.

## 9. Pointers (sha256)

Analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NXT-R2-THINKING-BUDGET-FOLD-B-READ-V1/`: `read.json` `3f72bde170e5816a33803c319d0301bb5365a26280a30746d21a9292f0306af6`; `README.md` `b6e45afb703dba9c5c4c65837eb388659106f908a4b6049219513d4051ab0d29`; `columns/score-summary.json` `bbb34b2f550c07bd523f36dacb3f3f7f2bfeb604aca4a97ba97f74e21e6d8ade`; column scores `budget-3072` `c504e277...`, `perception-off-solver-3072` `af859662...`, `solver-2048` `3df97a0c...`.

Repository (bytes at `e28a95a66`): package `README.md` `828a28ff40d698f320da858e9a63134411df44da5092e9a94ab96cb3bc0c6229`; `analysis-recipe-v1.json` `db28e3127c499ef706d54503b072a7aad8c41249b901e70726019f0a004092d8`; `registered-facts-v1.json` `0bf58804...`; `generation-plan-registered-rec2-v1.json` `8d651250...`; `protocol-registered-v1.json` `be41988b...`; `resume-replay-proof-rec2-v1.json` `665fee26...`; preregistration `088139a3...`; reader `scripts/analysis/slurp_nxt_thinking_budget_column_read.py` `0b88f152...`; arm table `scripts/flights/nx/nxt_r2_arms.json` `c3ee8c6b...`.

Registry `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, sections "NX-T R1 READ" (2026-10-17 10:37Z) and its 10:51Z correction, "Owner rulings 323 and 324", "Owner rulings 325-327", "R2b READ" (2026-10-18 15:30Z), "Owner rulings 331 A, 332 A, 333 B, 322 A", "Owner rulings 334 B, 335 B, 336 A, 337", "Owner ruling 344 A; 322 window incident ..." (2026-10-24 13:30Z) and "NX-T R2 rec2 READ" (15:35Z). Exposure ledger: blocks "Cell NXT-R2", "recovery rec1", "recovery rec2". Related notes: `docs/results/2026-10-17-slurp-nxt-r1-thinking-policy-column-read.md`, `docs/results/2026-10-18-slurp-nxt-r2b-solver-budget-column-read.md`.
