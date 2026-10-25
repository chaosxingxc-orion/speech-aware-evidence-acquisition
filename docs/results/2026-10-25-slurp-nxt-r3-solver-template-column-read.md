# NX-T R3, the Solver instruction-template column on the Thinking core (TRAIN Fold B, n = 1,080): all four candidates NEUTRAL (t4-decide-once-grounded SLU-F1 +1.19 [-0.10, +2.50], t1-decide-once +0.80 [-0.47, +2.07]); t1 cuts the Solver forced-close share -10.93 pp [-14.07, -7.87], under the 15 pp bar of ruling 345 A (NO-345 for every arm); development numbers, claims_benefit false

Read 2026-10-25 by Claude Opus 5.5 (results-note agent, on the coordinator's brief), written outside the repository because a flight is open (master at `6aaa0f6e6`). Model-free: this note opened no model, server, encoder, embedder, tokenizer, scorer or GPU, and wrote nothing under the data root or in the repository. It reads the aggregate files of the registered read `SAEA-SLURP-NXT-R3-SOLVER-TEMPLATE-FOLD-B-READ-V1` (`read.json`, `README.md`) and the beside-read of owner ruling 345 A (`efficiency-345.json`, `efficiency-345.md`, the version regenerated 2026-10-25 17:26:51Z), the package `docs/readiness/2026-10-18-slurp-nxt-r3-solver-template-fold-b-v1/` (README, `analysis-recipe-v1.json`), the registry sections named in section 9, the docstring of `scripts/analysis/forced_close/efficiency_rule_345.py` and the exposure-ledger rows of cell NXT-R3. No per-row file, utterance text, transcript, gold value, slot filler, model output or reasoning text was read, printed or persisted. Numbers marked "derived" are ratios, sums or differences of numbers printed in those files.

**Status: DESCRIPTIVE, development numbers on TRAIN Fold B (`SLURP-EVO-FOLD-B-V2`, n = 1,080, discovery role; owner decisions 28 and 86). Never a test claim. `claims_benefit` is false.** `read.json` `status` verbatim: "PREREGISTERED-READ (development numbers; never a test claim; claims_benefit false)". A USE-node template column on the selection fold (owner ruling 326 A), not an admission, a lock or a benefit claim (`analysis-recipe-v1.json` `claim_boundary`: "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim."; `what_is_not_here`: "No margins block and no admission: nothing is locked here."). The arm words are the reader's, fixed at registration (2026-10-18T15:51:41Z): **NOMINATED / EFFICIENT-NO-LOSS / HARM / NEUTRAL** (first that applies). The 345 verdict (**ENTERS-LOCK-EFFICIENCY-345 / NO-345**) is a beside-read under a ruling made after registration; the preregistered reader is untouched.

## 0. Answer in six lines

1. **All four candidates read NEUTRAL; no NOMINATED, no EFFICIENT-NO-LOSS, no HARM.** Against the delivering `lock` arm (72.04 SLU-F1 / 85.28 intent): `t1-decide-once` **+0.80 [-0.47, +2.07]** / intent -0.09; `t2-grounded-or-empty` **+0.82 [-0.39, +2.02]** / -0.65; `t3-supply-focus` **+0.21 [-1.01, +1.45]** / -0.19; `t4-decide-once-grounded` **+1.19 [-0.10, +2.50]** / -0.56. No SLU lower bound clears 0; no Solver seconds ratio reaches 0.85 (0.93-1.01).
2. **In-flight twin:** `aa` (the locked template, replicate of `lock`) reads SLU **+0.45 [-0.77, +1.64]**, intent -0.09 [-0.93, +0.74]; offset o = +0.45 pp, |o| = 0.45 is the bar (the external 268-B reference +1.15 is reported beside, never used in a word).
3. **345 A beside-read: NO-345 for every arm.** No arm reaches the 15 pp forced-close cut: t1 **-10.93 pp [-14.07, -7.87]** (43.5 % -> 32.6 %), t4 **-7.78 [-10.74, -4.81]**, t2 -2.31 [-5.37, +0.74], t3 +1.11 [-1.85, +4.17]. In the ruling's literal no-resolved-loss form every arm passes SLU and fails intent (True / False); the verdict is NO-345 on the cut alone.
4. **Mechanism:** the termination paragraph (t1) lowers the forced-close share by about a quarter at equal quality; the grounding paragraph (t2) does not move it; the supply-focus paragraph (t3) moves nothing; combining termination and grounding (t4) cuts less than t1 alone (section 7).
5. **Consequence:** instruction alone does not clear the 345 bar. The next lever ruling 345 A names is already flying: the NX-T R4 Solver decoding-policy column; if neither R3 nor R4 cuts the tail, the 330 A diagnostic's verdict picks the next lever (repetition loop -> the decoding axis; enumeration -> a structural Solver supply-cap column, after L338). No Fold A confirm is triggered.
6. **Flight cost:** 7,560 program contacts, 22,083.6 speech-audio seconds, 27.00 GPU-h measured against the 43.4 ceiling (measured arm mix 3.51 lock rows per row, registered 3.61).

## 1. Identities

| item | value |
| --- | --- |
| cells | smoke `slurp-native-stage3-nxt-r3-solver-template-fold-b-smoke-4-v1` (sealed 2026-10-24T13:35:16Z, 28 contacts); column `slurp-native-stage3-nxt-r3-solver-template-fold-b-v1`, run `SAEA-SLURP-STAGE3-NXT-R3-SOLVER-TEMPLATE-FOLD-B-V1`, attempt `attempt-slurp-native-stage3-nxt-r3-solver-template-fold-b-generation-v1` (FINALIZED), FIT run `SAEA-SLURP-STAGE3-NXT-R3-SOLVER-TEMPLATE-FOLD-B-FIT-V1`; read run `SAEA-SLURP-NXT-R3-SOLVER-TEMPLATE-FOLD-B-READ-V1`, recipe `slurp-nxt-r3-solver-template-fold-b-read-v1`, schema `saea-nxt-r3-solver-template-column-read-v1` |
| authority | owner rulings 326 A and 327 A (2026-10-17), 313 A (2026-10-14), 304/307 (2026-10-13), coordinator approval of the NX-T R3 design; beside-read: owner ruling 345 A (2026-10-24 17:50Z) |
| system | the 268-B Thinking lock cell (lock v2.2, plain review-off COMP-1b module graph) plus ONE addition, the Solver `template_variants` block; program `phase-native-module-v1-c7` (7 contacts per row: 1 shared Perception + 6 Solver arms over the SAME Perception note, evidence and QueryState) |
| core and session | Qwen3-Omni-30B-A3B-Thinking Q4_K_M, decoder-only build `04ccc72a`; fragment `q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max4096-v1`; session `serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1` (swap target `think-budget-np4`, 4 slots x 24,576, q8_0 KV, `--reasoning-format deepseek`) |
| thinking fields (every Solver arm) | budget 3,072 + answer reserve 1,024 = cap 4,096, `drop-reasoning-v1`, temperature 0, seed 20260913, the registered forced-close message; composed per ROLE at request time |
| arms (declared order; twin, then delivering last) | `t1-decide-once` (termination paragraph, template `c62991891a8b`); `t2-grounded-or-empty` (grounding paragraph, `eda1c311238b`); `t3-supply-focus` (supply-focus paragraph, `67e5044d5b5e`); `t4-decide-once-grounded` (t1 + t2 paragraphs, `c31397b4e1d6`); `aa` (twin, the locked template `18bff5c557ca`); `lock` (DELIVERING, the locked template `18bff5c557ca`). Each candidate is the locked template with its paragraph(s) inserted before the revision paragraph, everything else byte-identical |
| roster / scorer | `SLURP-EVO-FOLD-B-V2` (`docs/receipts/rosters/slurp-evo-fold-b-v2.json` sha256 `47b89b9e33b1aed553ad94a1819acba6ac8837130ca546c33219d91a1ab944a8`), split identity `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`, 1,080 rows, 18 scenarios x 60; `slurp-slu-official-train` (pinned official `evaluate.py`); each arm's first-visit Solver answer scored once, complete (`stage3_rollout_score --mode supply-variants`) |
| null and floors | in-flight twin `aa`: \|o\| = 0.4529 pp SLU (`arm_words.twin_offset_abs_pp`); intent guard -0.65 pp; Solver seconds ratio max 0.85; decision-190 floors 1.49 SLU / 0.65 intent (used by the 345 beside-read, not by the arm words); external 268-B reference SLU +1.15 / intent -0.09, P3.1 -0.61 (beside, never in a word) |
| resampling | paired utterance-cluster bootstrap, 10,000 draws, seed 20261018, CI95 (reader and 345 beside-read alike; 1,080 clusters) |
| seal | manifest `34dcfc8e83cf49ce14cbb46cac762f186a6990b374b473439e750cc391e66cc1`; outputs `c93000185b0ba70cd978319c7f6e1620b5deebfee5b624eba35a63d117343539`; trace `4e092cd458b82b0f0ce9a1b0987f76f66f7dc677ba06ccaa5b64cf2007beda30`; flight commit `033f1be39ac4c4edacaac69ff6484b61e742ae1e` |
| read sequence (UTC) | column sealed 2026-10-25T17:04:24Z (run row) / 17:06:02Z (READ row text), chain exit 17:08:31Z; READ row countersigned 17:16:18Z (`863675542`, "no number read before"); `columns/score-summary.json` 17:20:33Z, `read.json` and `README.md` 17:22:32Z (file times); 345 beside-read first written 17:22:47Z, regenerated 17:26:51Z in the ruling's own condition form (script commit `6aaa0f6e6`) |

## 2. The contrast

| arm | SLU-F1 % | SLU delta pp [CI95] | intent % | intent delta pp [CI95] | intent saves / harms / ties | Solver s ratio vs lock | absent rows | word |
| --- | ---: | --- | ---: | --- | --- | ---: | ---: | --- |
| lock (delivering) | 72.04 | -- | 85.28 | -- | -- | 1.00 | 0 | -- |
| aa (twin) | 72.49 | +0.45 [-0.77, +1.64] | 85.19 | -0.09 [-0.93, +0.74] | 9 / 10 / 1,061 | 0.98 (derived) | 0 | (the bar) |
| t1-decide-once | 72.84 | **+0.80 [-0.47, +2.07]** | 85.19 | **-0.09 [-1.11, +0.93]** | 14 / 15 / 1,051 | 0.98 | 0 | **NEUTRAL** |
| t2-grounded-or-empty | 72.86 | **+0.82 [-0.39, +2.02]** | 84.63 | **-0.65 [-1.57, +0.28]** | 9 / 16 / 1,055 | 0.96 | 0 | **NEUTRAL** |
| t3-supply-focus | 72.25 | **+0.21 [-1.01, +1.45]** | 85.09 | **-0.19 [-1.20, +0.83]** | 14 / 16 / 1,050 | 1.01 | 0 | **NEUTRAL** |
| t4-decide-once-grounded | 73.23 | **+1.19 [-0.10, +2.50]** | 84.72 | **-0.56 [-1.48, +0.37]** | 10 / 16 / 1,054 | 0.93 | 0 | **NEUTRAL** |

Full precision (`contrast.versus_delivering`; CI95 half-width in parentheses): t1 SLU +0.8039 [-0.4710, +2.0684] (1.27), intent -0.0926 [-1.1111, +0.9259] (1.02); t2 SLU +0.8169 [-0.3950, +2.0224] (1.21), intent -0.6481 [-1.5741, +0.2778] (0.93); t3 SLU +0.2083 [-1.0108, +1.4470] (1.23), intent -0.1852 [-1.2037, +0.8333] (1.02); t4 SLU +1.1876 [-0.1032, +2.4958] (1.30), intent -0.5556 [-1.4815, +0.3704] (0.93); twin aa SLU +0.4529 [-0.7738, +1.6416] (1.21), intent -0.0926 [-0.9259, +0.7407] (0.83). 0 absent columns, 0 scorer parse failures and 0 unattributed contacts on every arm.

**Applying the word rule** (`analysis-recipe-v1.json` `word_rules`; `arm_words.words.*.conditions`).
- NOMINATED needs SLU lower bound > 0, intent point >= -0.65 and SLU point >= \|o\| = 0.45: the lower bounds are -0.47, -0.39, -1.01, -0.10, so no arm. (The intent-point and twin-bar clauses hold for t1, t2, t4; t3's point +0.21 is below the bar; t2's intent point -0.6481 sits 0.002 pp above the guard, under one row.)
- EFFICIENT-NO-LOSS needs no resolved loss (SLU upper bound >= -0.45 and intent upper bound >= -0.65: both hold for all four) AND Solver seconds per contact <= 0.85 x the lock's: the ratios are 0.976, 0.959, 1.014, 0.933, so no arm.
- HARM needs SLU upper bound < 0: +2.07, +2.02, +1.45, +2.50, no arm.
- -> **NEUTRAL** for all four, as `arm_words.words.*.word` states; `next_step` is null for every arm.

## 3. The 345 A beside-read (forced-close efficiency rule)

The ruling, as written in the registry (section "2026-10-24 17:50Z -- Owner ruling 345 A"): "A Solver arm that cuts the Solver forced-close share by >= 15 pp (absolute, against the in-flight twin / delivering lock of the same flight) with no resolved loss (SLU-F1 delta CI95 lower bound >= -1.49 pp AND intent delta CI95 lower bound >= -0.65 pp against the twin) enters the composed lock v3.x as an EFFICIENCY component even when its pre-registered score word is NEUTRAL. The per-arm forced-close share and seconds per contact are mechanism readouts in every Solver column read." Application, same section: "NX-T R3 (t1 / t3 / t4) and NX-T R4 (presence penalty, temperature arms) are read under this rule. The pre-registered readers are not edited while their flights are open; the 345 readout (forced share delta per arm, with its no-resolved-loss check) is computed beside each read by a model-free script over the sealed trace and the official per-row columns and recorded in the results note."

What the script computes (`scripts/analysis/forced_close/efficiency_rule_345.py` docstring at `6aaa0f6e6`): per candidate arm against the delivering lock arm, the forced-close share of arm and lock on the SAME rows with the paired per-row difference and an utterance-cluster bootstrap CI95 (the reader's seed and draw count), whether the cut reaches the 15 pp bar (point estimate), the Solver seconds per contact and ratio, the no-resolved-loss conditions in the RULING's form taken from the deltas the preregistered read wrote ("never recomputed"), the reader's own NO-RESOLVED-LOSS conditions carried beside them (`reader_conditions`), and the verdict "ENTERS-LOCK-EFFICIENCY-345 when the cut reaches the bar AND both ruling-form conditions hold, otherwise NO-345". The contrast is against `lock`; the twin supplies the offset.

`efficiency-345.md` (regenerated 17:26:51Z), verbatim:

Lock arm `lock`: forced share 43.5 %, 52.9 s per Solver contact, 1080 rows.

| arm | quality word | forced share | delta vs lock (pp) CI95 | cut >= 15 pp | s / contact (ratio) | SLU delta CI95 | intent delta CI95 | no resolved loss, ruling form (SLU lo >= -1.49 / intent lo >= -0.65) | 345 verdict |
| --- | --- | ---: | --- | --- | ---: | --- | --- | --- | --- |
| t1-decide-once | NEUTRAL | 32.6 % | -10.93 [-14.07, -7.87] (n=1080) | no | 51.6 (0.98) | +0.80 [-0.47, +2.07] | -0.09 [-1.11, +0.93] | True / False | **NO-345** |
| t2-grounded-or-empty | NEUTRAL | 41.2 % | -2.31 [-5.37, +0.74] (n=1080) | no | 50.8 (0.96) | +0.82 [-0.39, +2.02] | -0.65 [-1.57, +0.28] | True / False | **NO-345** |
| t3-supply-focus | NEUTRAL | 44.6 % | +1.11 [-1.85, +4.17] (n=1080) | no | 53.7 (1.01) | +0.21 [-1.01, +1.45] | -0.19 [-1.20, +0.83] | True / False | **NO-345** |
| t4-decide-once-grounded | NEUTRAL | 35.7 % | -7.78 [-10.74, -4.81] (n=1080) | no | 49.4 (0.93) | +1.19 [-0.10, +2.50] | -0.56 [-1.48, +0.37] | True / False | **NO-345** |

Beside it (`efficiency-345.json`): the reader-form conditions (`reader_conditions`) are True / True for all four arms; the paired forced-close transitions against the lock (rows forced in both / arm only / lock only) are t1 260 / 92 / 210, t2 311 / 134 / 159, t3 338 / 144 / 132, t4 288 / 98 / 182 (1,080 rows, 1,080 clusters each).

Reading the conditions:
- **The cut decides.** The 15 pp bar is a point-estimate condition; the largest cuts are t1 -10.93 and t4 -7.78, so no arm reaches it and every verdict is NO-345 whatever the loss conditions read. t1's whole interval [-14.07, -7.87] also lies above -15.
- **Instrument note on the intent floor (a rule-form question, not a finding of this read).** At n = 1,080 the intent delta CI95 half-width is about 1 pp (0.83-1.02 pp across the five contrasts, section 2), so the literal lower-bound floor of -0.65 pp is failed by every arm, including one whose intent point is -0.09, and also by the in-flight twin `aa` itself (-0.09 [-0.93, +0.74], lower bound -0.93; the twin is not a 345 candidate and has no row in the beside-read). A same-template replicate does not pass this condition at this roster size, so in its literal form the intent clause does not separate an arm from the null. The coordinator flags this to the owner as a rule-form question (proposed 346); it does not change this read, whose verdicts rest on the cut. The reader-form conditions (CI95 upper bounds, the NX-T R1 NO-RESOLVED-LOSS rule) hold for every arm.

## 4. Per-node cost, forced closes and the preregistered secondaries (1,080 rows; `arms_nodes`, `secondaries`)

| arm | node | contacts | completion tokens mean / p50 / p90 / p99 / max | forced closes (share) | prompt tokens mean | reasoning chars mean | s per contact mean / p50 / p99 |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| (shared) | perception | 1,080 | 2,050.0 / 1,928 / 3,157 / 3,198 / 3,232 | **220** (0.204, derived) | 3,589.6 | 9,087 | **49.54** / 46.62 / 85.17 |
| lock | solver | 1,080 | 2,060.0 / 2,129 / 3,131.0 / 3,145.2 / 3,157 | **470 (0.435)** | 8,615.4 | 8,598 | **52.93** / 52.92 / 89.52 |
| aa | solver | 1,080 | 2,024.8 / 2,047 / 3,131.1 / 3,146.0 / 3,162 | **460 (0.426)** | 8,615.4 | 8,426 | **52.10** / 49.46 / 89.81 |
| t1-decide-once | solver | 1,080 | 1,955.2 / 1,881 / 3,130.0 / 3,143.2 / 3,167 | **352 (0.326)** | 8,653.4 | 8,213 | **51.64** / 48.69 / 91.83 |
| t2-grounded-or-empty | solver | 1,080 | 1,970.8 / 1,827 / 3,131.0 / 3,144.2 / 3,162 | **445 (0.412)** | 8,663.4 | 8,188 | **50.75** / 46.20 / 88.96 |
| t3-supply-focus | solver | 1,080 | 2,081.8 / 2,251 / 3,131.0 / 3,145.0 / 3,167 | **482 (0.446)** | 8,657.4 | 8,676 | **53.68** / 55.96 / 89.28 |
| t4-decide-once-grounded | solver | 1,080 | 1,918.4 / 1,759 / 3,131.0 / 3,145.2 / 3,158 | **386 (0.357)** | 8,701.4 | 8,006 | **49.41** / 43.45 / 89.70 |

Every node: mode think, cap 4,096, finish `stop` 1,080, 0 cap hits, 0 length finishes, 0 empty, 0 no-JSON, 0 think markers in content, 1,080 contacts with reasoning characters; 0 unattributed contacts; the read itself made 0 model, server, encoder, scorer or tokenizer contacts (`contacts`). The Perception node is one shared contact per row (220 forced closes of 1,080), so every Solver arm reads the same note. The candidates' Solver prompts are 38-86 tokens longer than the lock's (derived), the size of the added paragraphs.

| arm | forced share | forced < 40 items (n = 780) | forced >= 40 items (n = 300) | empty-gold false fill, all (of 392) | forced | natural | non-empty exact set (of 688) |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| lock | 0.435 | 276 (0.354) | 194 (0.647) | 77 (0.196) | 58 / 140 (0.414) | 19 / 252 (0.075) | 360 (0.523) |
| aa | 0.426 | 275 (0.353) | 185 (0.617) | 79 (0.202) | 63 / 132 (0.477) | 16 / 260 (0.062) | 362 (0.526) |
| t1-decide-once | 0.326 | 199 (0.255) | 153 (0.510) | 72 (0.184) | 44 / 97 (0.454) | 28 / 295 (0.095) | 373 (0.542) |
| t2-grounded-or-empty | 0.412 | 265 (0.340) | 180 (0.600) | 71 (0.181) | 45 / 113 (0.398) | 26 / 279 (0.093) | 364 (0.529) |
| t3-supply-focus | 0.446 | 290 (0.372) | 192 (0.640) | 71 (0.181) | 53 / 130 (0.408) | 18 / 262 (0.069) | 357 (0.519) |
| t4-decide-once-grounded | 0.357 | 223 (0.286) | 163 (0.543) | 70 (0.179) | 49 / 99 (0.495) | 21 / 293 (0.072) | 369 (0.536) |

No secondary carries an interval in the read; differences below are point counts. The same-form twin pair gives the in-flight jitter scale: `aa` and `lock` differ by 10 forced closes (460 vs 470; 9 of them in the 40+ bin), 2 false-fill rows and 2 exact-set rows (derived).

## 5. Per scenario (18 x 60 rows; point deltas against `lock`, no scenario CI in the read)

| scenario | n | SLU lock % | SLU d aa | SLU d t1 | SLU d t2 | SLU d t3 | SLU d t4 | intent lock % | intent d aa | intent d t1 | intent d t2 | intent d t3 | intent d t4 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 60 | 73.31 | -1.18 | +3.00 | +3.72 | +1.09 | -1.62 | 90.00 | +0.00 | +0.00 | +0.00 | +1.67 | -1.67 |
| audio | 60 | 78.79 | -2.77 | -2.38 | -8.03 | -1.02 | -2.83 | 85.00 | -1.67 | +1.67 | -1.67 | -3.33 | +0.00 |
| calendar | 60 | 71.28 | +2.48 | +0.52 | +2.00 | +1.82 | +2.54 | 85.00 | -3.33 | +0.00 | -3.33 | -1.67 | -1.67 |
| cooking | 60 | 74.81 | -2.14 | -0.94 | -0.35 | -0.38 | -0.24 | 83.33 | -3.33 | -3.33 | +0.00 | +1.67 | -3.33 |
| datetime | 60 | 80.58 | -3.75 | -2.52 | +3.80 | -4.64 | -4.60 | 96.67 | +0.00 | +0.00 | -1.67 | +0.00 | +1.67 |
| email | 60 | 73.60 | +0.03 | +3.03 | +2.13 | -0.46 | +3.45 | 93.33 | +0.00 | +0.00 | -1.67 | +0.00 | +0.00 |
| general | 60 | 55.46 | +0.00 | +3.87 | +2.85 | +1.87 | +3.87 | 41.67 | +1.67 | +0.00 | -1.67 | +0.00 | +0.00 |
| iot | 60 | 73.66 | +0.18 | +0.00 | +4.60 | -0.72 | +2.94 | 91.67 | +0.00 | +1.67 | +0.00 | +0.00 | +0.00 |
| lists | 60 | 65.67 | -0.53 | +1.73 | +8.48 | +2.86 | +7.99 | 86.67 | +0.00 | +0.00 | +1.67 | +1.67 | +0.00 |
| music | 60 | 56.35 | +8.24 | -0.68 | -1.49 | +1.13 | +1.13 | 75.00 | +1.67 | +3.33 | +3.33 | +1.67 | +0.00 |
| news | 60 | 75.12 | -2.17 | +0.60 | +0.89 | -2.69 | -4.18 | 91.67 | +0.00 | -1.67 | +0.00 | +0.00 | -1.67 |
| play | 60 | 59.49 | +5.68 | +0.37 | -0.93 | +2.54 | +2.55 | 83.33 | -1.67 | +0.00 | -3.33 | -5.00 | -1.67 |
| qa | 60 | 77.37 | -1.20 | +1.17 | -0.08 | -2.59 | +0.38 | 85.00 | -1.67 | +0.00 | -1.67 | -1.67 | -1.67 |
| recommendation | 60 | 64.66 | +3.28 | +5.11 | +3.32 | +1.57 | +8.05 | 83.33 | +1.67 | -1.67 | +1.67 | +3.33 | +0.00 |
| social | 60 | 71.56 | -1.93 | -0.77 | -2.40 | -2.94 | +2.15 | 88.33 | +0.00 | +0.00 | -1.67 | +0.00 | +0.00 |
| takeaway | 60 | 69.37 | +1.45 | +1.56 | -0.96 | +2.96 | +0.22 | 90.00 | +1.67 | -1.67 | -1.67 | -3.33 | -3.33 |
| transport | 60 | 74.48 | +1.59 | +0.32 | -0.17 | +0.25 | +1.81 | 86.67 | +1.67 | +0.00 | +0.00 | +1.67 | +1.67 |
| weather | 60 | 84.60 | -0.54 | -0.43 | -1.93 | +1.42 | -2.71 | 98.33 | +1.67 | +0.00 | +0.00 | +0.00 | +1.67 |

Weightings (`per_scenario`), SLU delta pp: natural mixture aa +0.45 / t1 +0.80 / t2 +0.82 / t3 +0.21 / t4 +1.19; equal-scenario **aa +0.37 / t1 +0.75 / t2 +0.86 / t3 +0.11 / t4 +1.16**; same sign and same order. Derived counts: SLU down in 6 of 18 scenarios for t1 and t4, 9 for t2, 8 for t3 and 9 for the twin. The largest scenario moves (t2 lists +8.48 and audio -8.03, t4 recommendation +8.05 and lists +7.99) are of the size the same-form twin shows at 60 rows (aa music +8.24, play +5.68).

## 6. Run accounting

| item | value |
| --- | --- |
| rows | 1,080, one attempt, no resume, no recovery; 0 absent columns on every arm (`absent_columns_by_arm`) |
| spend (ledger, CONSUMED) | 7,560 program contacts (1,080 x 7), 22,083.6 speech-audio seconds, 108.02 summed call-latency hours (slot-hours); manifest COMPLETED, attempt FINALIZED, sealed 2026-10-25T17:04:24Z, study commit `033f1be39`; registered caps 15,120 calls / 44,168 audio seconds / 43.4 GPU-h |
| smoke (ledger, CONSUMED) | 28 contacts, 71.3 speech-audio seconds, 0.35 summed call-latency hours; sealed 2026-10-24T13:35:16Z |
| throughput (`throughput`) | seconds per row (column) **360.1**; lock row **102.5** (Perception 49.54 + lock Solver 52.93); measured arm mix **3.51** lock rows per row (registered 3.61); one flight **27.00 GPU-h** measured against the registered ceiling **43.4** (registered expectation 33.32 GPU-h at 1.95 rows per minute) |
| cost model vs measured | the registration costed Perception at 59.00 s and every Solver contact at 64.07 s (the NX-T R2b delivering arm); measured 49.54 s and 49.41-53.68 s per contact. 108.02 slot-hours / 4 slots = 27.0 h (derived), consistent with the throughput figure |
| READ row | REGISTERED WITH THE FLIGHT; root countersigned 2026-10-25T17:16:18Z by the coordinator after the column seal and before any number was read; zero model, server, encoder, embedder, tokenizer and GPU contacts |

## 7. Interpretation (mechanism readouts; stated, not claimed)

- **The termination paragraph (t1) cuts the forced-close share by about a quarter at equal quality.** 43.5 % -> 32.6 % (-10.93 pp [-14.07, -7.87]; 470 -> 352 forced closes, -25 % relative, derived), with SLU +0.80 and intent -0.09, both intervals spanning zero. By supply bin the share falls 35.4 -> 25.5 % on rows under 40 supplied items and 64.7 -> 51.0 % on 40+ rows: 77 of the 118 removed forced closes are on the 780 rows under 40 items (-28 % relative there against -21 % on 40+ rows, derived), although the share-point cut is larger on the 40+ rows (-13.7 vs -9.9 pp, derived); half of the 40+ rows still forced-close under t1. Forced status is not stable per row: t1 frees 210 lock-forced rows and forces 92 new ones. Solver seconds fall only 2.4 % (ratio 0.976): the freed contacts end at lower token counts (mean 1,955 vs 2,060, p50 1,881 vs 2,129), but the p90 / p99 stay at the budget ceiling (3,130 / 3,143).
- **The grounding paragraph (t2) does not move forced closes** (-2.31 pp [-5.37, +0.74]; 445 vs 470). On its target, empty-gold false fill, it reads 71 of 392 against 77 for the lock and 79 for the twin (6 and 8 rows, derived; the twin and the lock differ by 2 rows on the same count; no interval is computed). Intent is the weakest of the four at -0.65 [-1.57, +0.28] (9 saves / 16 harms).
- **The supply-focus paragraph (t3) moves nothing:** forced +1.11 pp [-1.85, +4.17], the under-40 bin slightly up and the 40+ bin flat (0.372 / 0.640 against 0.354 / 0.647 on the lock), seconds ratio 1.01, SLU +0.21 below the twin bar. In this form the instruction does not reduce the supply the Solver works through.
- **Combining (t4) does not add the cuts.** -7.78 pp against t1's -10.93 (386 vs 352 forced closes). It is the cheapest arm (ratio 0.933, p50 1,759 tokens) and has the highest SLU point (+1.19 [-0.10, +2.50]); neither clears its threshold (0.85; lower bound > 0).
- **Instruction alone does not clear the 345 bar.** The best measured cut (t1) is about 4 pp short of 15 pp at the point (derived), and its interval stops at -14.07. Ruling 345 A names the next lever: NX-T R4, the Solver decoding-policy column (presence penalty and temperature arms on the Thinking core, TRAIN Fold B; flipped to ready 2026-10-25 17:09-17:13Z in `28b27dd7d`, `cb29502fa`, `7fae86389`; in flight since 17:15Z per the coordinator), read under the same rule. If neither R3 nor R4 cuts the tail, the 330 A reasoning diagnostic's verdict (enumeration vs repetition loop) decides between the decoding axis and a structural Solver supply-cap column (items per candidate intent), after L338. This note proposes nothing beyond what the registry already states.

## 8. What this does and does not say

- **Development numbers on TRAIN Fold B, never a test claim** (owner decisions 28 and 86); one roster, the selection fold; `claims_benefit` false; no admission, no lock change (`what_is_not_here`).
- **No Fold A confirm is triggered.** The preregistered next step ("a NOMINATED or EFFICIENT-NO-LOSS arm goes to a 2-arm Fold A confirm (stated, not built)") applies to no arm here.
- **No arm enters the lock under 345 A.** NO-345 for all four rests on the forced-cut bar; the ruling-form intent condition fails for every arm and for the twin's own interval alike, which section 3 records as a rule-form question (proposed 346), not as a finding about any arm.
- **Not shown:** that any template improves the Solver. t4 +1.19 and t1 / t2 +0.80 / +0.82 sit within about 0.75 pp of the twin's own +0.45 offset (derived), and every SLU interval includes zero. Not shown either: that t1's forced-close cut changes quality; the forced close is a mechanism readout, and the read does not link forced status to correctness.
- **Same Perception note for every arm.** The column varies only the Solver template; the shared Perception contact (220 forced closes) is common to all arms, so the contrasts isolate the USE node.
- **Secondaries carry no interval** except the 345 forced-share deltas; the per-scenario table carries points only (60 rows per scenario).

## 9. Pointers (sha256)

Analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NXT-R3-SOLVER-TEMPLATE-FOLD-B-READ-V1/`: `read.json` `fad30509c93a662e1988b2cae1ce9c44e86e0bd7f25abe04c91ba8d331d1b631`; `README.md` `04526d3c53ac0861517d2d6922b7c0f4326baab448ed5dd4f64014cb17e623cc`; beside-read (regenerated 17:26:51Z) `efficiency-345.json` `8658e6aaa5e473cc32d58387c9f48e3e7b3eb22a441c35f60810168d43bc7db4`, `efficiency-345.md` `e8981de1063504cce6d28bf210bbd1fe25482288885b69d643433d6fbb35edef`; `columns/score-summary.json` `ce1b745fe6518f654ae8344be51851108ef8951bf1f5bad858fc41772fe1bf4e`; column scores `lock` `d2fdaabf...`, `aa` `8fffa50e...`, `t1-decide-once` `a6bc20a6...`, `t2-grounded-or-empty` `8a1ae0a0...`, `t3-supply-focus` `929e8441...`, `t4-decide-once-grounded` `8a2760d9...`. Sealed hashes (`read.json` `sealed_hashes`, identical in `efficiency-345.json` `read_sealed_hashes`): manifest `34dcfc8e83cf49ce14cbb46cac762f186a6990b374b473439e750cc391e66cc1`, outputs `c93000185b0ba70cd978319c7f6e1620b5deebfee5b624eba35a63d117343539`, trace `4e092cd458b82b0f0ce9a1b0987f76f66f7dc677ba06ccaa5b64cf2007beda30`.

Repository (blob bytes at `3cc3ac0bf`, unchanged at `6aaa0f6e6` unless noted): package `docs/readiness/2026-10-18-slurp-nxt-r3-solver-template-fold-b-v1/` `README.md` `cd6c510a77ad0842bc6c7416da1a78cf82a2aee6549a7d1a2e9688e81ba8d279`; `analysis-recipe-v1.json` `a26be88fb968b388f60ad7f5d771700e17464d2e4b6aefba51f8425091bc617d`; `registered-facts-v1.json` `b8b5c97a...`; `protocol-registered-v1.json` `ee40e638...`; `generation-plan-registered-v1.json` `8d656708...` (the ledger's registered plan SHA256 is `787d0912dc1644105c04f61ef1fb27c635a0f5b89af167715149c3d3efae2993`); `signoff-conditions-v1.json` `1fc01cae...`; reader `scripts/analysis/slurp_nxt_r3_solver_template_column_read.py` `fa5a962b...`; 345 beside-script `scripts/analysis/forced_close/efficiency_rule_345.py` `c26394fa44c8cde6dc6716cd868f8f1e5703b51a3aec75c7a570240a2ec86be8` at `6aaa0f6e6` (the ruling-form version that wrote the regenerated files; the first version at `3cc3ac0bf` is `09bd05f4...`); arm table `scripts/flights/nx/nxt_r3_arms.json` `944bd0cd...`; roster `docs/receipts/rosters/slurp-evo-fold-b-v2.json` `47b89b9e...`.

Registry `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, sections "R2b READ: NEEDS-NO-MORE-BUDGET; ... owner rulings 329 A and 330 A" (2026-10-18 15:30Z), "NX-T R2 rec2 READ" (2026-10-24 15:35Z), "2026-10-24 17:30Z -- Owner directive on the Solver forced-close share; within-row analysis across two same-form flights; 345 proposed" and "2026-10-24 17:50Z -- Owner ruling 345 A". Exposure ledger rows: `SAEA-SLURP-STAGE3-NXT-R3-SOLVER-TEMPLATE-FOLD-B-SMOKE-4-V1` and `...-SMOKE-4-FIT-V1`, `SAEA-SLURP-STAGE3-NXT-R3-SOLVER-TEMPLATE-FOLD-B-V1` and `...-FIT-V1` (CONSUMED), `SAEA-SLURP-NXT-R3-SOLVER-TEMPLATE-FOLD-B-READ-V1` (countersigned 2026-10-25T17:16:18Z). Related notes: `docs/results/2026-10-24-slurp-nxt-r2-thinking-budget-column-read.md`, `docs/results/2026-10-18-slurp-nxt-r2b-solver-budget-column-read.md`.
