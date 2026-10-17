# SLURP test-sample successor 3 (the Thinking system, SLURP lock candidate v3.0): NEUTRAL under the registered rule; the no-harm claim holds; SLU-F1 +6.41 [+4.44, +8.46] and intent +3.97 [+2.26, +5.45] against the sealed successor-2 v2.2 column, gain reported beside the word, not claimed

Read 2026-10-17 by Claude Opus 5.5 (results-note agent, on the coordinator's brief, Fable 5.1) in the worktree
`opus/ms3-results-note` (base master `14f5c4ded`). Model-free: this note opened no model, server, encoder, embedder,
tokenizer, scorer or GPU, and wrote nothing under the data root. It reads the aggregate files of the registered read
`SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-PAIRED-ANALYSIS-V1` (`successor3-verdict.json`, `successor3-verdict.md`
and the pass `vs-comparator/`), the registration package, the two signed allowances, the registry, the exposure-ledger
rows and the metadata keys of the sealed generation manifest (status, cost, row-checkpoint block, timestamps). It opened
no per-row output, score, trace or checkpoint content. No utterance text, transcript, gold value, slot filler, model
output or reasoning text was printed or persisted; only counts, rates, pp, CIs, ids, hashes and intent labels appear.
Numbers marked "derived" are ratios, sums or differences of numbers printed in those files.

**A milestone development read (owner decisions 28, 151, 301); never a test claim.** This is the third test-sample
MILESTONE read. It is never a test claim, never an admission, never a final read and never a system-level lock.
`claims_benefit` is false. The registered words are **NEUTRAL / HARM / UNRESOLVED** (successor 2's); NOMINATED is not a
registered outcome. The verdict word is the coordinator's (owner decision 139); this note applies the rule fixed in
`docs/readiness/2026-10-14-slurp-milestone-successor3-thinking-system-v1/protocol-registered-v1.json`
(`decision_rule_fixed_here`). The gain is **reported beside the word, never claimed**.

## 0. Answer in eight lines

1. Registered verdict: **NEUTRAL**, so the registered **no-harm claim HOLDS on both metrics**. Thinking system minus the sealed successor-2 column (post-stratified natural mixture, the primary weighting): SLU-F1 66.65 -> 73.05, **+6.41 [+4.44, +8.46]**; intent 82.36 -> 86.33, **+3.97 [+2.26, +5.45]**. Both CI95 lower bounds are above -2.5; neither upper bound is below -|o| (0.6144 SLU / 1.6 intent).
2. Beside the word (`reported_beside_the_word`): `gain_reported_not_claimed: true`, `slu_point_at_or_above_the_bar: true`. The SLU point is 2.6 times the 2.5 pp bar (derived) and both lower bounds clear the declared offset (+4.44 > 0.6144; +2.26 > 1.6). Under the registered rule this is REPORTED; a claim would need its own replicated read.
3. **Limitation (verbatim from the verdict json):** "NO IN-CHAIN REPLICATE on the sample: the null is the DECLARED DEV P3.1 twin offset (a different roster and n), not a measured null of the sample. A milestone development read (owner decisions 28, 151, 301); never a test claim; claims_benefit is false."
4. Other weightings agree in sign: equal-stratum SLU **+6.98 [+4.71, +9.38]**, intent **+5.26 [+3.36, +6.72]**; raw roster mixture SLU +6.40 [+4.41, +8.44], intent +3.79 [+1.91, +5.88]. Raw span-F1 +5.84 [+3.45, +8.35].
5. The SLU gain is recall: in the pooled counts behind official SLU-F1, TP 3,562 -> 4,100 and FN 1,912.9 -> 1,377.8, while FP is flat (1,708.9 -> 1,701.8). Successor 2's gain over COMP-1b was the opposite (precision). Strata moving up / down / flat: SLU 42 / 10 / 6, intent 30 / 16 / 12 of 58.
6. Flight: one attempt, 3,010 rows, 6,020 contacts, COMPLETED / FINALIZED at flight commit `73fd885f8`, 0 tool calls, all 3,010 rows delivered, boundary supply matched on every row; summed call latency **102.77 h** (slot-hours, not wall); two host-sleep gaps (2026-10-16 05:14-06:47Z and 23:34Z -> 2026-10-17 04:44Z) were survived without a restart.
7. Cost: GPU-active 33.04 h (monitor, sleep gaps included) against successor 2's 3.72 h, about 8.9 times (derived); completion tokens per row 4,058.6 vs 137.9 (the reasoning). Under the 35.5 GPU-h registered ceiling.
8. Context, stated and not claimed: the Thinking system has now been read against the Instruct-era system on three rosters -- TRAIN Fold B +7.15 [+5.08, +9.26] SLU (268-B), DEV-2000-ADDED +7.52 [+5.46, +9.62] (P3.1), this test sample +6.41 [+4.44, +8.46]. The registered next steps are the NX-T node rounds (R1 rec2 resume next, then the R2 budget column), not a lock claim.

## 1. Inputs and identities

| item | value |
| --- | --- |
| Thinking arm (cell `slurp-milestone-successor3-thinking-system-v1`) | run `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1`, attempt `attempt-slurp-milestone-successor3-thinking-system-generation-v1`; run manifest `eb16b4ceae96968796e8cc28e18c33ab3c301f79aeb0ac1074c5f1df69e31f36`; outputs `a19c2e789a2d867dae3751ca4a924de02a30c73f7ce6f6581473c2c7212ce0ae`; scores `313bff137421797e2794e59fedd1772b033f7c7b10a08e7719b8d2c4bfcd25ad`; generation manifest `acc3b8ad7c88275c5dc086ca4a531e40f00b99c2d36ece1f0435427fa0ff07ed`; flight receipts `89193f8dca8d17ff814e841b52d2cc9c923cb607c5e173853acc9a37e122a847`; row checkpoint `bdfed492fe6f7913d5cb305bc16ee1f43f40991b7815e56860e699c9c83b6124` (3,010 complete rows, 0 unrendered); raw trace `126b13b8...`; trace manifest `3759d7c1...` |
| what it is | the P3.1 lock cell (`slurp-native-stage3-thinking-system-dev2000-added-lock-v1`, sealed at `37b0ed0aa`) with only the roster- and role-bound leaves moved, exactly the leaves that moved the R5 composed DEV cell to successor 2. COMP-1b's two components ON (agree-vote-seed, w_agree 1.0, recall k 60, with this roster's vote table; centroid-boundary-key) on lock v2.2 with v4g at delivery, Reviewer loop OFF (Perception then Solver, 2 contacts per row), program `phase-native-module-v1-c2`, every node thinking at reasoning budget 3,072 / cap 4,096, `drop-reasoning-v1`. The composed-diff proof (`registered-facts-v1.json`, `composed_config_diffs`): vs the P3.1 lock cell `anything_else` and `composition_factor` are empty; vs successor 2 exactly the 18 graph leaves of the core swap move, the same 18 leaves with the same values as the DEV swap R5 composed -> P3.1 lock |
| core and session | Qwen3-Omni-30B-A3B-Thinking Q4_K_M; model fragment `q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max4096-v1`; session `serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1` (swap target `think-budget-np4`, 4 slots x 24,576); its own Thinking sample speech packets (`TEST-SAMPLE-3010-promotion.json`, sha256 `686a2ba5...`, encoded in the GPU window 2026-10-15 23:11-23:14Z, row `SAEA-SLURP-TEST-SAMPLE-3010-THINKING-PACKETS-GPU-V1`) |
| comparator (sealed, not re-flown) | successor-2 column: run `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1`, attempt `attempt-slurp-milestone-successor2-composed-generation-v1`; manifest `b638eef9e829ed660814dec029272d93dc3be0eb053848fb6d4d0c1e7f0a482c`; outputs `fe8cec8c219cb6420de7c66a61e8b83364e101c9da950e2f375beb94b8c71874`; scores `6534195faeafa96c36ef032ed1abb7192ffa2cbb5a7d0b8031ad4b8a7d94bd5e`. The NX R5 composed system (review-off COMP-1b on lock v2.2 with v4g) on the Instruct core, flown 2026-10-10 at `25345cdd7`; its own read against the successor-1 COMP-1b column was NEUTRAL, SLU-F1 +1.67 [+0.53, +2.83], intent -0.47 [-1.04, +0.22] (`docs/results/2026-10-10-slurp-milestone-successor2-composed-test-sample-read.md`) |
| the one factor | the core (Instruct -> Thinking) with its decoding knobs and its own audio tower / packets; the system bytes, knowledge, roster and scorer are shared |
| roster | `SLURP-TEST-SAMPLE-3010-V1`, `docs/receipts/rosters/slurp-test-sample-3010-v1.json` sha256 `48d9fb336ce99ad1725bf5ca0f74687d37711d685fa9fb4f594b2f1d88344e6d`; split identity `0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9`; 3,010 recordings, 682 prompt clusters, 1,456 headset / 1,554 far-field; 58 of 59 intents (`general_greet` absent) |
| scorer | `slurp-slu-official-test` (official SLURP `evaluate.py`, TEST gold, read by the scorer after delivery only); one complete score job; `stop.json` reproduces the official pooled SLU-F1 and span-F1 of both arms from the sealed per-sample scores to 1.1e-16 (status PASSED) |
| seal | exposure-ledger row: CONSUMED (sealed), 6,020 contacts, 16,412.9 speech-audio seconds, 102.77 summed call-latency hours, manifest COMPLETED, attempt FINALIZED, sealed 2026-10-17T08:37:07Z, study commit `73fd885f8`. Generation manifest: `cost.latency_seconds_total` 369,962.45 s, `calls_used` 6,020, `tool_calls` 0, `failure_reason` none |
| allowances | `docs/receipts/owner/2026-10-13-slurp-test-sample-allowance-successor-3.json` (ruling 301 A; status `authorised`; sha256 `062f79e771376ea6da00121fda0e91e893c837f361c719c165faab3ebd9371df`) and its v2 successor `docs/receipts/owner/2026-10-14-slurp-test-sample-allowance-successor-3-v2.json` (decision 308 A; status `authorised`; sha256 `efd20fb6cc47e142fe9015d918a17a783c43892a57fa3927ff2065e78621c318`; adds the packets preparation id and the Thinking ceilings), both re-verified on the worktree bytes by this note |
| owner decisions | 299 A (rebuild the base on Thinking); 301 A (allowance signed; lock arm only; comparator = sealed successor 2; declared DEV twin offset with the no-in-chain-replicate limitation stated); 308 A (v2 allowance for the packets pass); 28 / 86 / 151 (development numbers, one-shot terms); 139 (the verdict word is the coordinator's) |
| read | recipe `slurp-milestone-successor3-thinking-system-paired-analysis-v1`; driver `scripts/flights/nx/successor3_thinking_read.sh`, rule applier `scripts/analysis/slurp_successor3_thinking_read.py`; contrast stages `driver.py` `5c95a2e3...`, stage-3 strata / delivery / frontier stages `stage3_driver.py` `da9485fc...`; zero model, tokenizer, encoder, scorer-process or network contacts in the read files (`contacts` blocks all 0) |

**Flight timeline.** Chain start 2026-10-15T23:30:39Z at flight commit `73fd885f8` (`/home/chao/ms3-chain.out`); session
attach 23:33:11Z (session-attach receipt); seal 2026-10-17T08:37:07Z (generation manifest `created_at`); chain exit
rc 0 at 08:38:28Z. The registry LAUNCHED section (2026-10-15 23:35Z) records the registration at `727d96336`, the
packets row countersigned 22:54Z, the packets window 23:11-23:14Z, the generation and FIT rows countersigned 23:18Z,
the receipt minted, `0e50fa84e` committed and the ext4 flip converged 23:28Z. Two host-sleep gaps (registry CORRECTION
2026-10-17 04:55Z, Windows Power-Troubleshooter events): sleep 2026-10-16 05:14:20Z -> wake 06:47:45Z and sleep
2026-10-16 23:34:13Z -> wake 2026-10-17 04:44:25Z. The worker and server processes survived both and resumed; across the
second, the row checkpoint and the workflow log agreed (2,586 checkpointed vs 2,585 workflow ends at 04:47Z), so no
durability defect. The first gap had been attributed to host memory pressure on 2026-10-16 07:30Z; the correction
supersedes that attribution.

**Custody.** The READ row was countersigned 2026-10-17T08:39:20Z (its text: "the arm is sealed at its flight commit with
one successful official score and the sealed run was not opened for any number before this countersignature"). The
first analysis artefact (`stop.json`) is stamped 08:39:28Z, after the countersignature, as `read-qualification-v1.md`
step 5 requires. As in successors 1 and 2, the generated `vs-comparator/README.md` and `verdict.json` carry inherited
boilerplate ("the fresh-roster generalisation read of the already-locked v2.0 default plan against the bare frozen
core"; "DEV-2000-ADDED is a development roster") that does not describe this pair; this note and the registered recipe
state the correct comparison. The generated tables call the 58 `scenario_action` intent strata "per-scenario".

## 2. Definitions and the rule

- **Contrast.** delta = Thinking system minus the sealed successor-2 column, paired per recording on the same 3,010 rows, cross-flight (nothing re-flown).
- **Metrics.** PRIMARY: official pooled SLU-F1 (`slu_f1` of `evaluate.py`, pooled counts, never a mean of per-row F1). GUARD: intent accuracy (`scenario_action` exact).
- **Resampling.** Prompt-cluster paired bootstrap, cluster key `utterance_id` (682 prompts), 10,000 draws, seed **20261014** (new; successor 2 used 20260915). The stratified weightings resample within gold-intent strata, computed inside the scorer (`--strata-inside-scorer`; no per-row gold bank exists).
- **Weightings.** *Post-stratified natural mixture* (primary): the full-population intent shares from `population-counts-v1.json` (sha256 `7f8a536f...`, the same bytes as successor 2's), renormalised over the 58 represented intents; intent = sum_h w_h * accuracy_h; SLU-F1 = F1 of the weighted per-stratum TP/FP/FN. *Equal-stratum*: the unweighted mean over the 58 strata of the per-stratum deltas. *Raw*: the roster's own mixture, not a population estimate.
- **Declared null.** |o| = the DEV P3.1 twin offset: SLU **0.6144** pp (signed -0.6144, CI95 [-1.8819, +0.6863]) and intent **1.6** pp (signed +1.6, CI95 [+0.5988, +2.668]), from `analysis/SAEA-SLURP-SYSTEM-THINKING-CORE-DEV2000-ADDED-READ-V1/read.json` (sha256 `f110be35...`). Borrowed from a 1,000-row DEV roster, not measured on the sample; the intent offset exceeds the 0.65 pp intent guard and is carried as read. No in-chain replicate exists on the sample, by design (ruling 301 A, as decision 250 A for successor 2).
- **Harm margin** 2.5 pp on both metrics. **Expected effect** (declared at registration, decision 139): +7.5179 pp SLU, the P3.1 DEV point.
- **Verdict words (the registered rule).** **NEUTRAL** iff the CI95 lower bound of the delta on SLU-F1 and on intent is >= -2.5 pp and the read is not HARM. **HARM** iff the CI95 upper bound on SLU-F1 or on intent is below -|o| (decision 25). **UNRESOLVED** iff a lower bound is under -2.5 pp while neither HARM nor NEUTRAL holds. NOMINATED is not a registered outcome: a point above the bar and a CI95 lower bound above |o| are REPORTED beside the word as "gain reported, not claimed" and would need their own replicated read.

Applying the rule: the lower bounds are +4.441 (SLU) and +2.2648 (intent), both >= -2.5. The upper bounds are +8.4602 and
+5.4524, neither below -0.6144 / -1.6. The read is **NEUTRAL**: no-harm PASS. Beside it, the SLU point +6.41 is at or
above the 2.5 pp bar and both lower bounds exceed |o|; this is reported, not claimed.

## 3. Contrasts

### 3.1 Pooled official metrics, all weightings

| weighting | SLU-F1 successor 2 -> Thinking % | SLU-F1 delta pp [CI95] | intent successor 2 -> Thinking % | intent delta pp [CI95] |
| --- | --- | --- | --- | --- |
| **post-stratified natural mixture (primary)** | 66.65 -> 73.05 | **+6.41 [+4.44, +8.46]** | 82.36 -> 86.33 | **+3.97 [+2.26, +5.45]** |
| equal-stratum | -- | +6.98 [+4.71, +9.38] (CI90 [+5.09, +8.98]) | -- | +5.26 [+3.36, +6.72] (CI90 [+3.63, +6.48]) |
| raw roster mixture (context) | 66.30 -> 72.70 | +6.40 [+4.41, +8.44] (CI90 [+4.74, +8.10]) | 83.16 -> 86.94 | +3.79 [+1.91, +5.88] |

Full precision (verdict json): SLU-F1 66.6473 -> 73.0527, delta +6.4054 [+4.441, +8.4602]; intent 82.3589 -> 86.3274,
delta +3.9685 [+2.2648, +5.4524]; equal-stratum SLU +6.9822 [+4.7105, +9.3768], intent +5.2561 [+3.3583, +6.7194].
Raw official span-F1 (pooled): 58.38 -> 64.22, **+5.84 [+3.45, +8.35]**.

Against the declarations. The declared expected effect was +7.5179 SLU (the P3.1 DEV point); the observed primary point
is +6.41, 85 % of it (derived), inside the DEV interval [+5.46, +9.62]. Every weighting's SLU and intent lower bound is
above zero and above the declared offset.

### 3.2 Per-row channels (raw roster, cluster bootstrap; saves / harms are rows that flip)

| per-row metric | successor 2 -> Thinking % | delta pp [CI95] | saves / harms / ties | McNemar p |
| --- | --- | --- | --- | ---: |
| intent (`scenario_action_exact`) | 83.16 -> 86.94 | +3.79 [+1.91, +5.88] | 187 / 73 / 2,750 | < 1e-6 |
| `action_exact` | 85.71 -> 88.27 | +2.56 [+1.14, +3.99] | 150 / 73 / 2,787 | < 1e-6 |
| `scenario_exact` | 87.97 -> 90.50 | +2.52 [+0.94, +4.46] | 133 / 57 / 2,820 | < 1e-6 |
| per-row slot F1 (exact) | 33.79 -> 38.54 | +4.75 [+3.07, +6.43] | 330 / 171 / 2,509 | < 1e-6 |
| per-row SLU F1 (mean, NOT the official metric) | 39.26 -> 44.32 | +5.06 [+3.57, +6.61] | 430 / 227 / 2,353 | < 1e-6 |

The README prints the McNemar p as 0.000000 on every row. Recording channel (n far-field 1,554 / headset 1,456): intent
far-field +4.18 (108 / 43), headset +3.37 (79 / 30); per-row SLU F1 mean far-field +5.22, headset +4.90; per-row slot F1
far-field +5.02, headset +4.47. The far-field gain is slightly larger on every metric; this note does not test the
difference. Unlike successor 2, the per-row mean SLU F1 moves with the official pooled number.

### 3.3 Pooled counts behind official SLU-F1 (raw roster, summed over the 58 strata; derived from `scorer-strata-aggregate.json`)

| arm | TP | FP | FN | TP + FP (emitted) | official SLU-F1 = 2TP / (2TP + FP + FN) | intent correct / 3,010 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| successor 2 (Instruct) | 3,562 | 1,708.92 | 1,912.92 | 5,270.92 | 66.30 | 2,503 |
| successor 3 (Thinking) | 4,100 | 1,701.79 | 1,377.79 | 5,801.79 | 72.70 | 2,617 |

These sums reproduce each arm's official pooled SLU-F1 and successor 2's counts as its own note printed them. FP and FN
carry `evaluate.py`'s fractional distance credits, so they are not exact-match entity counts. The Thinking system emits
531 more (weighted) entity predictions: TP +538, FN -535.1, FP -7.1. The SLU-F1 gain is a **recall gain at unchanged
false positives**, where successor 2's gain over COMP-1b was a precision gain bought with recall (FP -682.3, TP -220).
The natural-mixture roll-up of these counts with the population weights reproduces the post-stratified levels exactly
(66.6473 / 73.0527 SLU, 82.3589 / 86.3274 intent; derived).

## 4. Per-intent tables and the scenario roll-up

### 4.1 The 58 intent strata

Source: `vs-comparator/per-scenario-tables.json` (`per_scenario`, rendered in the pass README; stratum
`scorer:gold intent scenario_action`, aggregate-only, inside the scorer). Conditional within-stratum values, the same in
the natural and equal weightings; CI95 from the within-stratum paired cluster bootstrap (cluster `utterance_id`, 10,000
draws, seed 20261014). Descriptive, no multiplicity correction; no stratum selects or adopts anything. Strata up / down /
flat: intent 30 / 16 / 12, SLU 42 / 10 / 6. **Strata with n < 10 are unresolved**: only `iot_hue_lighton` (n = 1);
`music_dislikeness` sits at n = 10.

| intent stratum | n | intent s2 -> s3 % | intent d pp [CI95] | saves / harms | SLU s2 -> s3 % | SLU d pp [CI95] |
| --- | ---: | --- | --- | --- | --- | --- |
| alarm_query | 63 | 82.54 -> 90.48 | +7.94 [0.00, +21.33] | 6 / 1 | 74.84 -> 93.96 | +19.12 [+3.70, +48.92] |
| alarm_remove | 48 | 87.50 -> 100.00 | +12.50 [0.00, +30.77] | 6 / 0 | 73.68 -> 94.34 | +20.66 [0.00, +63.64] |
| alarm_set | 82 | 90.24 -> 91.46 | +1.22 [-4.82, +9.38] | 4 / 3 | 93.63 -> 92.28 | -1.35 [-4.02, +1.16] |
| audio_volume_down | 32 | 93.75 -> 96.88 | +3.12 [0.00, +10.00] | 1 / 0 | 78.07 -> 79.90 | +1.84 [-6.35, +12.13] |
| audio_volume_mute | 88 | 85.23 -> 95.45 | +10.23 [+1.96, +25.37] | 9 / 0 | 30.00 -> 100.00 | +70.00 [0.00, +100.00] |
| audio_volume_other | 16 | 31.25 -> 75.00 | +43.75 [0.00, +85.71] | 9 / 2 | 31.32 -> 27.08 | -4.24 [-5.87, 0.00] |
| audio_volume_up | 78 | 89.74 -> 88.46 | -1.28 [-6.45, 0.00] | 0 / 1 | 0.00 -> 0.00 | 0.00 [0.00, 0.00] |
| calendar_query | 74 | 75.68 -> 77.03 | +1.35 [-2.99, +6.33] | 4 / 3 | 74.53 -> 74.62 | +0.09 [-9.44, +11.61] |
| calendar_remove | 66 | 89.39 -> 93.94 | +4.55 [-3.45, +16.67] | 4 / 1 | 80.11 -> 95.82 | +15.70 [+1.59, +38.66] |
| calendar_set | 145 | 90.34 -> 94.48 | +4.14 [0.00, +10.45] | 6 / 0 | 69.94 -> 74.70 | +4.76 [-0.44, +10.57] |
| cooking_recipe | 49 | 97.96 -> 89.80 | -8.16 [-27.59, 0.00] | 0 / 4 | 76.26 -> 71.91 | -4.35 [-12.23, +4.64] |
| datetime_convert | 22 | 72.73 -> 72.73 | 0.00 [-16.67, +14.29] | 1 / 1 | 82.68 -> 85.22 | +2.54 [-4.02, +9.63] |
| datetime_query | 67 | 98.51 -> 97.01 | -1.49 [-5.06, 0.00] | 0 / 1 | 74.25 -> 79.72 | +5.47 [+0.30, +13.03] |
| email_addcontact | 32 | 93.75 -> 90.62 | -3.12 [-28.57, +4.41] | 1 / 2 | 32.53 -> 40.35 | +7.81 [-3.18, +36.79] |
| email_query | 91 | 86.81 -> 90.11 | +3.30 [-1.22, +7.79] | 4 / 1 | 74.74 -> 78.67 | +3.93 [-4.27, +12.09] |
| email_querycontact | 32 | 81.25 -> 87.50 | +6.25 [0.00, +17.86] | 2 / 0 | 59.66 -> 63.86 | +4.19 [-5.12, +12.51] |
| email_sendemail | 81 | 93.83 -> 93.83 | 0.00 [0.00, 0.00] | 0 / 0 | 58.23 -> 61.68 | +3.45 [-3.19, +11.81] |
| general_joke | 84 | 98.81 -> 100.00 | +1.19 [0.00, +2.61] | 1 / 0 | 70.83 -> 84.37 | +13.54 [-4.52, +63.64] |
| general_quirky | 91 | 18.68 -> 34.07 | +15.38 [+3.70, +28.74] | 17 / 3 | 37.35 -> 50.49 | +13.14 [+1.29, +25.14] |
| iot_cleaning | 51 | 72.55 -> 82.35 | +9.80 [0.00, +17.78] | 5 / 0 | 52.55 -> 64.11 | +11.56 [+3.56, +38.49] |
| iot_coffee | 39 | 100.00 -> 97.44 | -2.56 [-10.00, 0.00] | 0 / 1 | 88.89 -> 96.30 | +7.41 [-11.11, +34.12] |
| iot_hue_lightchange | 29 | 82.76 -> 93.10 | +10.34 [0.00, +27.28] | 3 / 0 | 90.91 -> 92.05 | +1.14 [-8.10, +13.88] |
| iot_hue_lightdim | 48 | 72.92 -> 89.58 | +16.67 [0.00, +20.75] | 8 / 0 | 14.29 -> 22.22 | +7.94 [0.00, +50.00] |
| iot_hue_lightoff | 61 | 96.72 -> 93.44 | -3.28 [-12.00, 0.00] | 0 / 2 | 73.25 -> 80.23 | +6.98 [-9.23, +23.35] |
| iot_hue_lighton (unresolved, n < 10) | 1 | 0.00 -> 100.00 | +100.00 [+100.00, +100.00] | 1 / 0 | 100.00 -> 100.00 | 0.00 [0.00, 0.00] |
| iot_hue_lightup | 32 | 96.88 -> 93.75 | -3.12 [-19.35, +7.50] | 1 / 2 | 80.00 -> 80.00 | 0.00 [0.00, 0.00] |
| iot_wemo_off | 22 | 86.36 -> 77.27 | -9.09 [-33.33, +10.00] | 1 / 3 | 69.05 -> 75.31 | +6.26 [0.00, +16.27] |
| iot_wemo_on | 21 | 80.95 -> 95.24 | +14.29 [0.00, +33.33] | 3 / 0 | 78.80 -> 75.40 | -3.40 [-15.96, +7.74] |
| lists_createoradd | 46 | 67.39 -> 63.04 | -4.35 [-10.17, 0.00] | 0 / 2 | 68.00 -> 87.03 | +19.03 [+6.20, +28.54] |
| lists_query | 63 | 46.03 -> 77.78 | +31.75 [0.00, +57.14] | 20 / 0 | 26.67 -> 54.55 | +27.88 [-2.39, +59.23] |
| lists_remove | 69 | 82.61 -> 97.10 | +14.49 [0.00, +25.74] | 11 / 1 | 68.65 -> 75.05 | +6.40 [-9.43, +21.66] |
| music_dislikeness | 10 | 100.00 -> 100.00 | 0.00 [0.00, 0.00] | 0 / 0 | 0.00 -> 0.00 | 0.00 [0.00, 0.00] |
| music_likeness | 43 | 76.74 -> 65.12 | -11.63 [-32.14, +8.33] | 1 / 6 | 18.93 -> 11.76 | -7.17 [-57.00, 0.00] |
| music_query | 39 | 76.92 -> 82.05 | +5.13 [0.00, +12.20] | 2 / 0 | 0.00 -> 0.00 | 0.00 [0.00, 0.00] |
| music_settings | 13 | 23.08 -> 38.46 | +15.38 [0.00, +25.00] | 3 / 1 | 66.67 -> 55.34 | -11.33 [-50.44, +40.00] |
| news_query | 90 | 80.00 -> 86.67 | +6.67 [0.00, +15.49] | 6 / 0 | 60.44 -> 65.51 | +5.07 [-28.15, +32.03] |
| play_audiobook | 71 | 64.79 -> 66.20 | +1.41 [0.00, +4.48] | 2 / 1 | 47.86 -> 59.18 | +11.31 [-0.25, +21.90] |
| play_game | 38 | 92.11 -> 92.11 | 0.00 [-11.43, +16.13] | 2 / 2 | 69.57 -> 72.34 | +2.78 [-11.87, +26.67] |
| play_music | 125 | 80.00 -> 90.40 | +10.40 [-0.89, +21.66] | 20 / 7 | 62.97 -> 75.39 | +12.42 [+0.88, +25.30] |
| play_podcasts | 105 | 87.62 -> 82.86 | -4.76 [-11.11, +3.75] | 3 / 8 | 34.40 -> 41.99 | +7.59 [-0.33, +12.19] |
| play_radio | 74 | 77.03 -> 74.32 | -2.70 [-5.81, 0.00] | 0 / 2 | 52.75 -> 53.99 | +1.24 [-5.10, +6.17] |
| qa_currency | 44 | 97.73 -> 100.00 | +2.27 [0.00, +7.14] | 1 / 0 | 71.40 -> 76.06 | +4.66 [-16.47, +34.29] |
| qa_definition | 57 | 89.47 -> 84.21 | -5.26 [-9.26, 0.00] | 0 / 3 | 81.16 -> 73.88 | -7.27 [-12.48, -0.19] |
| qa_factoid | 88 | 76.14 -> 86.36 | +10.23 [+2.86, +21.59] | 9 / 0 | 66.40 -> 62.34 | -4.06 [-11.06, +1.74] |
| qa_maths | 24 | 100.00 -> 100.00 | 0.00 [0.00, 0.00] | 0 / 0 | 0.00 -> 0.00 | 0.00 [0.00, 0.00] |
| qa_stock | 29 | 79.31 -> 79.31 | 0.00 [0.00, 0.00] | 0 / 0 | 76.09 -> 73.66 | -2.43 [-8.30, 0.00] |
| recommendation_events | 36 | 83.33 -> 86.11 | +2.78 [0.00, +10.34] | 1 / 0 | 51.32 -> 70.09 | +18.77 [+2.33, +33.64] |
| recommendation_locations | 23 | 100.00 -> 95.65 | -4.35 [-17.65, 0.00] | 0 / 1 | 74.74 -> 82.47 | +7.74 [-5.19, +16.87] |
| recommendation_movies | 28 | 100.00 -> 100.00 | 0.00 [0.00, 0.00] | 0 / 0 | 50.00 -> 62.50 | +12.50 [0.00, +43.33] |
| social_post | 54 | 94.44 -> 96.30 | +1.85 [0.00, +6.67] | 2 / 1 | 71.66 -> 74.93 | +3.28 [-2.25, +8.84] |
| social_query | 26 | 80.77 -> 80.77 | 0.00 [0.00, 0.00] | 0 / 0 | 68.07 -> 68.04 | -0.03 [-10.86, +13.45] |
| takeaway_order | 36 | 75.00 -> 69.44 | -5.56 [-24.24, +9.52] | 3 / 5 | 72.23 -> 82.93 | +10.70 [-3.05, +30.15] |
| takeaway_query | 36 | 86.11 -> 94.44 | +8.33 [0.00, +25.00] | 3 / 0 | 60.76 -> 75.20 | +14.44 [+0.78, +26.47] |
| transport_query | 34 | 91.18 -> 91.18 | 0.00 [0.00, 0.00] | 0 / 0 | 70.01 -> 75.14 | +5.14 [-0.31, +11.38] |
| transport_taxi | 18 | 100.00 -> 100.00 | 0.00 [0.00, 0.00] | 0 / 0 | 66.35 -> 85.71 | +19.36 [+8.76, +34.34] |
| transport_ticket | 35 | 97.14 -> 97.14 | 0.00 [0.00, 0.00] | 1 / 1 | 71.07 -> 81.13 | +10.06 [+2.89, +21.90] |
| transport_traffic | 22 | 100.00 -> 100.00 | 0.00 [0.00, 0.00] | 0 / 0 | 65.95 -> 74.30 | +8.35 [-11.28, +18.03] |
| weather_query | 89 | 98.88 -> 97.75 | -1.12 [-4.00, 0.00] | 0 / 1 | 64.09 -> 78.46 | +14.38 [+4.68, +26.80] |

Reading the strata (descriptive). Intent CI95 excluding zero: up in `audio_volume_mute` +10.23, `general_quirky` +15.38
and `qa_factoid` +10.23; none down. SLU CI95 excluding zero: up in `alarm_query`, `calendar_remove`, `datetime_query`,
`general_quirky`, `iot_cleaning`, `lists_createoradd`, `play_music`, `recommendation_events`, `takeaway_query`,
`transport_taxi`, `transport_ticket` and `weather_query`; down only in `qa_definition` -7.27 [-12.48, -0.19] (0 saves /
3 harms on intent). Intent harms concentrate in `play_podcasts` (3 / 8), `music_likeness` (1 / 6), `cooking_recipe`
(0 / 4) and `iot_wemo_off` (1 / 3). Small-denominator strata swing hard: `audio_volume_mute` SLU 30.00 -> 100.00 and
`audio_volume_other` rest on a handful of gold entities; read such rows as counts, not rates.

### 4.2 Scenario roll-up (natural weights, point estimates only; derived)

This note derived this table from the per-stratum counts in `scorer-strata-aggregate.json` and the registered population
weights (weights renormalised within each scenario). Intent is the weight-normalised mean of the scenario's intent
strata; SLU-F1 is F1 of the weighted pooled counts. The roll-up over all 58 strata reproduces the pooled post-stratified
levels exactly. No scenario CI is given: the registered bootstrap has no scenario-level draws. Every scenario has at
least 49 rows.

| scenario | intent strata | n | natural intent s2 / s3 % | natural intent d pp | natural SLU s2 / s3 % | natural SLU d pp |
| --- | ---: | ---: | --- | ---: | --- | ---: |
| alarm | 3 | 193 | 87.06 / 93.18 | +6.12 | 86.97 / 92.90 | +5.93 |
| audio | 4 | 214 | 84.39 / 92.73 | +8.34 | 43.62 / 74.71 | +31.09 |
| calendar | 3 | 285 | 85.46 / 88.78 | +3.32 | 71.51 / 76.36 | +4.85 |
| cooking | 1 | 49 | 97.96 / 89.80 | -8.16 | 76.26 / 71.91 | -4.35 |
| datetime | 2 | 89 | 96.05 / 94.70 | -1.35 | 75.55 / 80.63 | +5.08 |
| email | 4 | 236 | 89.43 / 91.38 | +1.95 | 63.26 / 67.74 | +4.48 |
| general | 2 | 175 | 31.78 / 44.85 | +13.06 | 43.78 / 55.39 | +11.61 |
| iot | 9 | 304 | 85.32 / 90.69 | +5.37 | 67.95 / 76.03 | +8.08 |
| lists | 3 | 178 | 65.20 / 80.42 | +15.21 | 64.71 / 76.43 | +11.72 |
| music | 4 | 105 | 74.86 / 72.32 | -2.55 | 28.56 / 21.75 | -6.81 |
| news | 1 | 90 | 80.00 / 86.67 | +6.67 | 60.44 / 65.51 | +5.07 |
| play | 5 | 413 | 79.14 / 82.45 | +3.30 | 53.29 / 63.04 | +9.75 |
| qa | 5 | 242 | 84.25 / 88.56 | +4.31 | 71.05 / 68.45 | -2.60 |
| recommendation | 3 | 87 | 92.86 / 92.70 | -0.16 | 61.78 / 73.47 | +11.69 |
| social | 2 | 80 | 90.00 / 91.26 | +1.25 | 71.23 / 73.88 | +2.65 |
| takeaway | 2 | 72 | 82.42 / 86.14 | +3.72 | 65.80 / 78.25 | +12.45 |
| transport | 4 | 109 | 95.88 / 95.88 | 0.00 | 69.56 / 79.72 | +10.17 |
| weather | 1 | 89 | 98.88 / 97.75 | -1.12 | 64.09 / 78.46 | +14.38 |

SLU-F1 gains in 15 of 18 scenarios and loses in cooking (-4.35), music (-6.81) and qa (-2.60). Music also lost SLU on
TRAIN Fold B in 268-B (-4.20) and was absent from the P3.1 DEV roster; qa gained +3.64 on DEV. Intent gains in 12, is flat
in transport and loses in cooking (-8.16, 0 / 4 rows), music (-2.55), datetime (-1.35), weather (-1.12) and
recommendation (-0.16). This note does not test why.

## 5. Efficiency and cost

| field | successor 2 (Instruct) | successor 3 (Thinking) | Thinking minus successor 2 |
| --- | ---: | ---: | ---: |
| contacts | 6,020 | 6,020 | 0 |
| contacts per row | 2.0000 | 2.0000 | 0 |
| role visits per row (histogram) | 2: 3,010 | 2: 3,010 | -- |
| prompt tokens per row | 14,048.5 | 12,074.5 | -1,974.0 |
| measured prefilled tokens per row | 8,479.5 | 6,508.4 | -1,971.0 |
| completion tokens per row (reasoning included) | 137.9 | 4,058.6 | +3,920.7 |
| GPU-active hours (serving monitor) | 3.7236 | 33.0447 | +29.3211 |
| GPU hours per 1,000 rows | 1.2371 | 10.9783 | +9.7412 |
| GPU hours per 1,080 rows (decision 75 frontier) | 1.3360 | 11.8566 | +10.5205 |
| generation wall seconds | 13,955.4 | 119,023.7 | +105,068.3 |
| contacts per minute | 25.88 | 3.03 | -22.85 |
| mean GPU utilisation % | 84.17 | 91.21 | +7.04 |
| repeated speech-audio seconds | 16,412.9 | 16,412.9 | 0 |
| summed call latency | -- | 102.77 h (61.5 s per contact, derived) | -- |
| tool calls | 0 | 0 | 0 |

Sources: `vs-comparator/efficiency.json`, `frontier.json`, `structural.json`; the summed latency from the generation
manifest and the ledger row. Reading the cost plainly:

- **The monitor hours include the two sleeps.** The Thinking generation wall (119,024 s, 33.06 h) and the monitor's
  GPU-active seconds (118,961 s) both span 23:33Z to 08:37Z, the two host-sleep gaps included (5,605 s + 18,612 s =
  6.73 h, derived from the registry timestamps). Awake wall is about **26.3 h** (derived), against the about 27.3 h
  expected and the **35.5 GPU-h** registered ceiling (v2 allowance, P3.1 rule `ceil_0.1(rows / 1.84 / 60 x 1.3)`);
  about 1.9 rows per awake minute (derived). The 33.04 GPU-h figure is therefore an upper bound on compute.
- **Slot-normalised:** 102.77 slot-hours / 4 slots = **25.69 slot-normalised GPU-h** (derived), consistent with the
  awake wall.
- **The reasoning is the cost.** Completion tokens rise 29 times per row; prompt and prefilled tokens fall about
  2,000 per row (`drop-reasoning-v1` and the Thinking packets). Frontier effect (raw, right minus left): intent +3.79 pp
  and SLU-F1 +6.40 pp at +10.52 GPU-h per 1,080 rows; 0.32 intent pp per GPU-h per 1,080 rows. The Thinking system is
  more accurate and about 8.9 times more expensive per row in monitored GPU-active time, sleeps included (derived; about
  7.1 times on the awake wall, derived); this read claims no Pareto statement.

**Per-node statistics are not in the read outputs.** The protocol lists per-node cap-hit / empty / forced-close counts
as reported beside the word, but the read's files carry none (no `nodes_by_arm` block as in P3.1). What the files do show
(`structural.json`, `delivery-conversion.json`): 3,010 / 3,010 rows admitted with a native episode receipt, 2 role visits
per row, 0 revisions, 0 tool calls; **10 rows / 10 contacts were context-fit compacted** on the Thinking arm (0 on
successor 2); every row delivered an answer (0 missing on both arms); the flown first-phase boundary sets equal the
arm's own pinned prepared supply on all 3,010 rows (0 mismatched, one permitted empty default per arm; boundary-selected
rows 2,627 vs 2,637); wire contacts equal sealed calls and prompt-token totals equal sealed cost on both arms. The v4g
delivery normaliser was applied on 3,010 Thinking rows and changed 1,018 answers (successor 2: applied 3,008, changed
599); label branches already-legal 2,976 / 2,868, r-action 26 / 133, edit-distance 8 / 7 (Thinking / successor 2). The
gold-bank extension is NOT_APPLICABLE on a final-report roster (coordinator ruling 2026-09-30).

## 6. What the verdict means and what it does not

- **It means** the Thinking system did not lose successor 2's accuracy on the signed sample, within what a cross-flight read against a declared null can resolve: NEUTRAL, no-harm PASS on both metrics.
- **It means, reported beside the word,** that the observed SLU-F1 and intent deltas are positive with CI95 lower bounds above zero and above the declared DEV twin offset in every weighting, and that the SLU point is at or above the 2.5 pp bar. The registered rule makes this a report, not a claim: `claims_benefit` is false and a claim would need its own replicated read.
- **Context (stated, not claimed).** The same contrast -- the locked system on the Thinking core minus the Instruct-era system -- has now been read on three rosters: TRAIN Fold B **+7.15 [+5.08, +9.26]** SLU / +2.31 [+0.56, +4.07] intent against the Instruct lock i3 with an in-chain twin (268-B, n 1,080); DEV-2000-ADDED **+7.52 [+5.46, +9.62]** / +2.50 [+1.00, +4.07] against the NX R5 composed column with an in-chain twin (P3.1, n 1,000); and this test sample **+6.41 [+4.44, +8.46]** / +3.97 [+2.26, +5.45] against the successor-2 column without a twin (n 3,010). The three comparators are Instruct-core systems of one lineage but not byte-identical, and only the first two reads carry a measured same-flight null. On intent, this read's lower bound (+2.26) clears the declared 1.6 pp offset, but that offset is borrowed from DEV, so the intent attribution caveat of P3.1 is not lifted by this read.
- **It does not mean** a lock, an admission or a test claim. The registered next steps (registry 2026-10-17 05:05Z and earlier) are the NX-T node rounds on the Thinking base under ruling 307: NX-T R1 rec2 (ruling 320 B, the checkpoint resume of the per-node thinking-policy column) flies next, then NX-T R2 (the per-node reasoning-budget column, ruling 318 A). Nothing in this read changes that order, and nothing here is a lock claim for v3.0.
- **It does not mean** superiority, generalisation, a SOTA position or a claim about other carriers. The SOTA comparison on the Thinking base is the separate step P3.5 (decision 285 deferred until the Thinking base is locked); this note makes none. Every number is development evidence (decisions 28, 86, 151, 301); the carriers stay held.
- **One-shot.** One attempt was flown under the allowance terms, with no smoke on the sample, no recovery, no resume, no re-score, no re-read and no selection; the two sleeps paused the one attempt and did not restart it. Nothing was tuned on the sample: the vote pool and the centroid key are TRAIN artifacts, v4g was selected on DEV and confirmed on TRAIN folds, COMP-1b was selected on DEV-2000-ADDED, and the Thinking transfer was read on Fold B and DEV without tuning. The sealed successor-2 run was not re-flown, re-scored or re-read beyond the registered pairing. **The next test-sample read needs a new owner allowance and fresh run ids.** These aggregates must not enter proposer contexts, knowledge construction, search selection, candidate selection or runtime memory.

## 7. Limitations

- **No in-chain replicate on the sample** (verbatim limitation in section 0, item 3). The null is the declared DEV P3.1 twin offset from a different roster and n. The intent offset (1.6 pp) exceeds the 0.65 pp intent guard.
- **Cross-flight, different days and sessions.** Successor 2 flew 2026-10-10 on the Instruct session; this arm flew 2026-10-15 to 2026-10-17 on the Thinking session with two host sleeps. Session drift is not measured; the 2.5 pp bar is what covers it.
- **One core, one encoder.** "Thinking core" means the Thinking decoder with its own audio tower and its own sample packets; this read cannot separate the two.
- **Sample, not the full test split.** 3,010 recordings / 682 prompts with 58 of 59 intents; post-stratified weights are renormalised over those 58; CIs are on the deltas only.
- **Per-node reasoning statistics** (cap hits, empty answers, forced closes) are not in the read outputs (section 5).
- **Inherited strings.** The generated pass README / `verdict.json` boilerplate (section 1, custody) and the `milestone_rule` text of both successor-3 allowances (which still describes "the fresh NX R5 composed arm ... read cross-flight against the SEALED successor-1 PLAN and COMP-1b columns") are carried over from successor 2; the binding fields (`permitted_run_ids`, `read_run_ids`, `preparation_run_ids`, status) are correct. `registered-facts-v1.json` `post_stratification_read` still names seed 20260929 and "arm minus MILESTONE-SUCCESSOR1-PLAN" in its carried text; the protocol's rule and every read artefact use seed 20261014 and the successor-2 comparator.

## 8. Pointers (sha256)

Analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-PAIRED-ANALYSIS-V1/`:

| file | sha256 |
| --- | --- |
| `successor3-verdict.json` (schema `saea-slurp-successor3-thinking-verdict-v1`) | `5412a175ddf1213cf616901952c1bc6579c1e9cca6dbb7f03d33a6645b8068e2` |
| `successor3-verdict.md` | `35f1fce51fc3df84c8f27999f28ee69c2683271f5dd903276e2f3d04c1761ab1` |
| `vs-comparator/verdict.json` | `c4b83a14363e720afb31d47cdee1d16211169eba2aad225c2e82468b6369ff36` |
| `vs-comparator/README.md` | `b7d6f375ace05a8822fe1915d52c5d44a03f59bc2349fe9fc141fdcf121af04a` |
| `vs-comparator/score-contrasts.json` | `78d92c0f5540f96b14fccb4007e70d402ee6c47750f6dfbb7252a95c2f177a2c` |
| `vs-comparator/per-scenario-tables.json` | `a1ae3c177c3223094fcc02cd4e3b4a34a204344fce61d5a110ac084a3713db5b` |
| `vs-comparator/scorer-strata-aggregate.json` (receipt `b3ad8b64...`) | `85286d9547e48269af3b5695f760e3e5ed77b30d0944a84b79d319731aae42c2` |
| `vs-comparator/delivery-conversion.json` | `6884b9a772cf0b3112e1590e084090f66b46dd02e32c120c826090599221d916` |
| `vs-comparator/efficiency.json` | `a095b0488bb75ba0c6419a79cb7e350d58c6700eb751d247846cea77b5ae8624` |
| `vs-comparator/frontier.json` | `28c18c9ae776c65cc8e0b2760d1a44757cd70b16a8d9bb135364fa45ffaed509` |
| `vs-comparator/structural.json` | `2590baddd02259ac6f16dea4045ac0780a5cb5ed4d374f323451883454ab25e2` |
| `vs-comparator/stop.json` | `3000f5d08f1df0d2535bd127e5df620c0e25fdc3b4bcafb8e7bcd008d8c06787` |

Repository (bytes at master `14f5c4ded`):

| file | sha256 |
| --- | --- |
| `docs/readiness/2026-10-14-slurp-milestone-successor3-thinking-system-v1/README.md` | `ed57d50c1cebe2bdb6d29b5879a0c5323f4f4dffef0546e60ecf548ee63ce988` |
| `.../protocol-registered-v1.json` | `c8bf0340cd9ba5d27d3bf44e3c420e06e38c0401ad3c585a7f95a65dbe19914d` |
| `.../registered-facts-v1.json` | `9fefc26fcfea85b648e4aeefec0d568ec1a68461b3f6f22cae51f132c4dadb3c` |
| `.../analysis-recipe-v1.json` | `e0ba4529c28a9c9b9335204c8b131ebef7d4712eec79450c2f5ab66f4d7d6bb3` |
| `.../population-counts-v1.json` | `7f8a536fc02db6ad7896cac818deaaa3faaf18f5f065bee0b2ee10ca5d5e0c66` |
| `.../read-qualification-v1.md` | `3697b164ffef0b770651f242fb697cc8dcf6c856fc4926c7dfe23fc7cb773318` |
| `.../successor-identity-map.json` | `c9eb5ffdacc5a75b89e734d21df8d3f7c65d5654c6dcb44fed5d8b2f88b16f35` |
| `.../generation-plan-registered-v1.json` | `29509afa7b41090fa24c52955c957e58f33f3f3511802e4834579e5d2b1d06ac` |
| `.../fit-plan-registered-v1.json` | `aa3ab153b3edaaa9057b401733106377dfaac2e4afd1d9c1924adbe771141ef1` |
| `docs/receipts/owner/2026-10-13-slurp-test-sample-allowance-successor-3.json` | `062f79e771376ea6da00121fda0e91e893c837f361c719c165faab3ebd9371df` |
| `docs/receipts/owner/2026-10-14-slurp-test-sample-allowance-successor-3-v2.json` | `efd20fb6cc47e142fe9015d918a17a783c43892a57fa3927ff2065e78621c318` |
| `docs/receipts/rosters/slurp-test-sample-3010-v1.json` | `48d9fb336ce99ad1725bf5ca0f74687d37711d685fa9fb4f594b2f1d88344e6d` |

Related notes: `docs/results/2026-10-10-slurp-milestone-successor2-composed-test-sample-read.md` (the comparator's own
read); `docs/results/2026-10-14-slurp-p31-thinking-system-dev2000-added-read.md` (the DEV read and the declared offset);
`docs/results/2026-10-13-slurp-268b-thinking-system-fold-b-read.md` (Fold B); registry
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, sections "Owner rulings 301-306 and the priority
correction 307" (2026-10-13 17:40Z), 308 A, "Successor-3 test read LAUNCHED at flight commit 73fd885f8" (2026-10-15
23:35Z), "CORRECTION: the two successor-3 stalls were host SLEEP" (2026-10-17 04:55Z) and "NX-T R1 rec2 (320 B)
registered in flight" (2026-10-17 05:05Z); exposure-ledger rows `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1`,
`...-THINKING-SYSTEM-FIT-V1` and `...-PAIRED-ANALYSIS-V1` (READ row countersigned 2026-10-17T08:39:20Z).

**Not verified here.**

- No registry section records the successor-3 seal or read as of master `14f5c4ded`; the NEUTRAL word is taken from
  `successor3-verdict.json` and `successor3-verdict.md`.
- The brief's flight start "23:31Z": the files give chain start 23:30:39Z and session attach 23:33:11Z; this note uses
  those. Seal 08:37:07Z and chain exit 08:38:28Z bracket the brief's "08:38Z".
- That the worker and server processes survived both sleeps without restart is taken from the registry correction
  section and the single uninterrupted attempt; no process log was read.
- Per-node reasoning statistics on the sample (section 5).
