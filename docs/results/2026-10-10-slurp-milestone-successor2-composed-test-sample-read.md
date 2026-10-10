# SLURP test-sample successor 2 (the NX R5 composed system, review-off COMP-1b on lock v2.2 with v4g): NEUTRAL under the registered rule; the no-harm claim holds; SLU-F1 +1.67 [+0.53, +2.83] and intent -0.47 [-1.04, +0.22] against the sealed successor-1 COMP-1b column, at 2.00 instead of 4.06 contacts per row

Read 2026-10-10 by Claude Opus 5.5 (results agent, on the coordinator's brief, Fable 5.1) in the worktree
`opus/ms2-results`. Model-free: this note opened no model, server, encoder, embedder, tokenizer, scorer or GPU, and
wrote nothing under the data root. It reads only the aggregate files of the registered read
`SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-PAIRED-ANALYSIS-V1` (passes `vs-comparator` and `vs-plan`), the
registration package, the signed allowance, the roster receipt (id counts only) and the exposure-ledger rows. No
per-row output, score, trace or anything under `runs/` was opened. No utterance text, transcript, gold value, slot
filler or model output was printed or persisted; only counts, rates, pp, CIs, ids, hashes and intent labels appear.

**Development evidence (owner decisions 28, 86, 151).** This is the second test-sample MILESTONE read. It is never a
test claim, never an admission, never a final read and never a system-level lock. The verdict word is the
coordinator's (owner decision 139); this note applies the rule fixed in
`docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1/protocol-registered-v1.json`
(`decision_rule_fixed_here`).

## 0. Answer in eight lines

1. Registered verdict: **NEUTRAL**, so the registered **NO-HARM claim HOLDS on both metrics**. Composed minus the sealed successor-1 COMP-1b column (post-stratified natural mixture, the primary weighting): SLU-F1 **+1.67 [+0.53, +2.83]**, intent **-0.47 [-1.04, +0.22]**. Both CI95 lower bounds are above -2.5. Neither upper bound is below -|o| (0.73 SLU / 0.20 intent), so the read is not HARM.
2. In the coordinator's words: no-harm PASS; a positive SLU-F1 observation of +1.67 whose lower bound is under the declared offset; development evidence under decision 28, not a test claim; the composed system's intent is unchanged vs COMP-1b and +5.34 vs PLAN. The lower bound (+0.53) sits under the declared cross-flight offset (0.73), so this design cannot separate the gain from flight-to-flight variation.
3. Levels on 3,010 recordings / 682 prompts / 58 of 59 intents: SLU-F1 64.98 -> **66.65**, intent 82.82 -> 82.36. The SLU point is larger than the DEV read of the same system (+1.24 [-0.29, +2.80], NEUTRAL) and than the declared +1.2429. Raw pooled: +2.15 [+0.89, +3.45]. Span-F1: +3.61 [+1.90, +5.39]. The equal-stratum weighting is weaker: **+0.95 [-0.97, +3.10]** SLU, -0.45 [-0.98, +0.38] intent.
4. Against the sealed PLAN column (context only): SLU-F1 64.18 -> 66.65 = **+2.46 [+0.88, +3.96]**; intent 77.02 -> 82.36 = **+5.34 [+3.67, +6.97]**. Per-row intent: +4.49 [+2.69, +6.42], 218 saves / 83 harms. Equal-stratum: SLU +1.87 [-0.16, +4.35], intent +2.57 [+0.85, +4.34].
5. The SLU-F1 gain comes from precision. In the pooled counts behind official SLU-F1, false positives fall 2,391.2 -> 1,708.9, true positives fall 3,782 -> 3,562 and false negatives rise 1,837.2 -> 1,912.9. The non-official per-row mean SLU F1 moves the other way: -1.72 [-2.79, -0.71] (177 saves / 219 harms).
6. Efficiency is the registered claim. Contacts per row are 2.00 vs 4.06 (6,020 vs 12,214 contacts). Prompt tokens per row fall 60.5 %, and active GPU hours fall 4.94 -> 3.72 (-24.6 %). There were 0 tool calls, all 3,010 rows delivered, and boundary supply matched on every row.
7. Decision 252, clause 3 (section 5). On this sample, composed intent 82.36 is above the published trained pipelines (HerMiT 78.33, SF-ID 72.06) and under the gold-transcript bound 84.84. Composed SLU-F1 66.65 is above SF-ID 64.02, **4.19 pp under HerMiT 70.84** and 11.54 pp under the gold-transcript bound 78.19. This is indicative, not a claim: the sample is not the full test split, and every published row is a trained system on the full split.
8. One-shot: one attempt, no re-read, no selection, and nothing tuned on the sample. The next test read needs a new allowance. Nothing here releases a carrier: decision 252 requires all three of its lock modes.

## 1. Inputs and identities

| item | value |
| --- | --- |
| composed arm (cell `slurp-milestone-successor2-composed-v1`) | run `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1`, attempt `attempt-slurp-milestone-successor2-composed-generation-v1`; run manifest `b638eef9e829ed660814dec029272d93dc3be0eb053848fb6d4d0c1e7f0a482c`; outputs `fe8cec8c219cb6420de7c66a61e8b83364e101c9da950e2f375beb94b8c71874`; scores `6534195faeafa96c36ef032ed1abb7192ffa2cbb5a7d0b8031ad4b8a7d94bd5e`; generation manifest `c4ddcbcc4784bb27b4e1ace37739d2c32a412b1a85e0c5db290657b8fa1fe73c`; flight receipts `8c31da5e640b31d3fc2deeced7305f3ef6a58c69cedf4adad16b5df9af6cde90`; prepared supply `56586c7f958b5d2db13d70d821406a4fa49d0a0a1fb333c3fe7be31543b5a33e` |
| what it is | the NX R5 composed arm with the R5 DEV cell's bytes and only the roster moved. COMP-1b's two components are ON (agree-vote-seed, w_agree 1.0, recall k 60, with the sample's own vote table; centroid-boundary-key), on module lock v2.2 with v4g at delivery and the Reviewer loop OFF (Perception then Solver, 2 contacts per row), policy `phase-native-module-v1-c2`. `successor-identity-map.json` lists every moved leaf |
| primary comparator (sealed, not re-flown) | successor-1 COMP-1b column: run `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-COMP1B-V1`, attempt `attempt-slurp-milestone-successor1-comp1b-generation-v1`; manifest `905a64623ef114945e52e1038b7aa2f0c3b018ba68107f83aa29420c27446b46`; outputs `f331db14b0da2fe5b5823d06475203471ba17cd3b314e838a4a8f20c96bb3803`; scores `fb8102970449ba569810533c5d77ccb71de206411912e1affa40092a47f365c5`. Flown 2026-10-01 with the same components, the full graph (Reviewer on) and the v3 normaliser |
| context comparator (sealed, not re-flown) | successor-1 PLAN column: run `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-PLAN-V1`, attempt `attempt-slurp-milestone-successor1-plan-generation-v1`; manifest `1d4fc02bbedbbf6932802eeb7e4aa91dff5a80c614a9ef33f57d06c8429a8898`; outputs `cb6edf909d5db3dabe6a1eec6faf851d1d436f755b9270b6c615adb06ec3c0ee`; scores `191989a0755dc2b77eb3f2e0f235ff84abb0498346c20d6459ab9f690cbd7ef6` |
| roster | `SLURP-TEST-SAMPLE-3010-V1`, `docs/receipts/rosters/slurp-test-sample-3010-v1.json` sha256 `48d9fb336ce99ad1725bf5ca0f74687d37711d685fa9fb4f594b2f1d88344e6d`; split identity `0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9`; 3,010 recordings, 682 distinct `utterance_id` (prompt) clusters, 1,456 headset / 1,554 far-field; 58 of 59 intents, `general_greet` absent |
| scorer | `slurp-slu-official-test` (official SLURP `evaluate.py`, TEST gold, read by the scorer after delivery only); one score job per arm; `stop.json` reproduces the official pooled SLU-F1 and span-F1 of both arms from the sealed per-sample scores to 1.1e-16 (status PASSED) |
| seal (ledger READ-row countersignature) | FINALIZED / COMPLETED at flight commit `25345cdd7`: 3,010 rows (all distinct), 6,020 contacts, 0 tool calls, 16,412.9 speech-seconds, 4 h 02 m arm wall time; arm-inspect pass; one attempt; driver-done 18:30:05Z; no serving restart |
| allowance | `docs/receipts/owner/2026-10-10-slurp-test-sample-successor2-allowance-v1.json` (v3; status `authorised`; decision 251 A); sha256 `4e04b23f89b9eb06c1b228649a6f991fb9399dea6efbaf4d168a4b731d9e388d`, re-verified on the committed bytes by this note |
| owner decisions | 233 and 241 (the second test-sample read); 250 A (cross-flight-no-replicate exception, declared offset, no-harm, margin 2.5); 251 A (allowance signed); 252 (SOTA rows beside the repo numbers) |
| read | recipe `slurp-milestone-successor2-composed-paired-analysis-v1`; driver `scripts/flights/nx/milestone_successor2_read.sh`; reader sha256 `5c95a2e3...` (contrast stages) and `da9485fc...` (stage-3 strata, delivery and frontier stages); zero model, tokenizer, encoder, scorer-process or network contacts in any stage |

Custody. The READ row's text stamps the countersignature at 18:40:00Z. The commit that carries it (`bbb7c549d`) is
dated 18:31:35Z, and the first analysis artefact (`stop.json`) is dated 18:31:59Z. By commit time, the
countersignature therefore precedes every opened score, as `read-qualification-v1.md` step 5 requires. The 18:40:00Z
label is a stamp discrepancy, not an order violation. As in successor 1, the generated pass READMEs carry inherited
boilerplate ("fresh-roster generalisation read of the already-locked v2.0 default plan against the bare frozen core";
"DEV-2000-ADDED is a development roster") that does not describe this pair. This note and the registered recipe state
the correct comparison. The generated tables call the 58 `scenario_action` intent strata "per-scenario".

## 2. Definitions

- **Contrast.** delta = composed minus comparator, paired per recording on the same 3,010 rows. The registered contrast uses the successor-1 COMP-1b column; the PLAN column is reported beside it as context and gates nothing.
- **Metrics.** PRIMARY: official pooled SLU-F1 (`slu_f1` of `evaluate.py`, pooled counts, never a mean of per-row F1). GUARD: intent accuracy (`scenario_action` exact).
- **Resampling.** Paired whole-cluster bootstrap with cluster key `utterance_id` (682 prompts), 10,000 draws, seed 20260915. The stratified weightings resample within gold-intent strata, computed inside the scorer (`--strata-inside-scorer`; no per-row gold bank exists).
- **Weightings.** *Post-stratified natural mixture* (primary, per decision 141 and the roster receipt): the full-population intent shares from `population-counts-v1.json` (sha256 `7f8a536f...`), renormalised over the 58 represented intents. Intent is sum_h w_h * accuracy_h. SLU-F1 is F1 of the weighted per-row TP/FP/FN. *Equal-stratum*: the unweighted mean over the 58 strata of the per-stratum deltas. *Raw*: the roster's own mixture, which is not a population estimate.
- **Declared offset.** |o| = 0.7274 pp SLU-F1 / 0.20 pp intent. It is borrowed from the DEV R5 read (replicate minus the sealed A2 in-chain A/A, DEV-2000-ADDED, n 1,000) and was not measured on the sample. No in-chain replicate exists on the sample, by design (decision 250 A).
- **Guard null (reported, not used by the rule).** Successor 1's FALLBACK: the DEV own null scaled to the sample, h_SLU 1.4492 / h_intent 1.3329 at the prompt level, with 0.7219 / 0.664 recording-scaled as the optimistic bound. Flagged: no own null exists for the sample.
- **Verdict words (the registered rule).** **NEUTRAL** iff the CI95 lower bound of the delta on SLU-F1 and on intent is >= -2.5 pp and the read is not HARM. This is an efficiency result and is never reported as a gain. **HARM** iff the CI95 upper bound on SLU-F1 or intent is below -|o|. **UNRESOLVED** iff a lower bound is under -2.5 pp while neither HARM nor NEUTRAL holds. NOMINATED is not a registered outcome (`claims_benefit: false`): a point above the bar would be reported, never claimed, and would need its own replicated read.

Applying the rule: the lower bounds are +0.53 (SLU) and -1.04 (intent), both >= -2.5. The upper bounds are +2.83 and
+0.22, so neither is below -0.73 / -0.20. The read is **NEUTRAL**: no-harm PASS. The SLU point +1.67 is under the
2.5 pp bar and is reported, not claimed.

## 3. Contrasts

### 3.1 Pooled official metrics, all weightings

| contrast | weighting | SLU-F1 left -> right % | SLU-F1 delta pp [CI95] | intent left -> right % | intent delta pp [CI95] |
| --- | --- | --- | --- | --- | --- |
| composed - COMP-1b (registered) | **post-stratified natural mixture (primary)** | 64.98 -> 66.65 | **+1.67 [+0.53, +2.83]** | 82.82 -> 82.36 | **-0.47 [-1.04, +0.22]** |
| composed - COMP-1b | equal-stratum | -- | +0.95 [-0.97, +3.10] (CI90 [-0.67, +2.82]) | -- | -0.45 [-0.98, +0.38] (CI90 [-0.89, +0.26]) |
| composed - COMP-1b | raw roster mixture (context) | 64.14 -> 66.30 | +2.15 [+0.89, +3.45] (CI90 [+1.10, +3.24]) | 83.59 -> 83.16 | -0.43 [-1.13, +0.20] |
| composed - PLAN (context) | post-stratified natural mixture | 64.18 -> 66.65 | +2.46 [+0.88, +3.96] | 77.02 -> 82.36 | +5.34 [+3.67, +6.97] |
| composed - PLAN | equal-stratum | -- | +1.87 [-0.16, +4.35] | -- | +2.57 [+0.85, +4.34] |
| composed - PLAN | raw roster mixture | 63.43 -> 66.30 | +2.86 [+1.19, +4.56] (CI90 [+1.47, +4.28]) | 78.67 -> 83.16 | +4.49 [+2.69, +6.42] |

Raw official span-F1 (pooled, context): COMP-1b 54.77 -> composed 58.38 = **+3.61 [+1.90, +5.39]**; PLAN 53.82 ->
58.38 = +4.56 [+2.42, +6.67].

Against the declarations. The declared expected effect vs COMP-1b was +1.2429 SLU (the R5 DEV point); the observed
primary point is +1.67. The declared vs-PLAN context was 6.30 intent (6.10 after the offset) and 2.04 SLU (1.31 after
the offset); the observed values are +5.34 and +2.46. The raw pooled SLU lower bound (+0.89) clears the offset, but the
registered weighting's lower bound (+0.53) does not, and the equal-stratum interval crosses zero. Only the
post-stratified row carries the claim.

### 3.2 Per-row channels (raw roster, cluster bootstrap; saves / harms are rows that flip)

| per-row metric | vs COMP-1b: left -> right % | delta pp [CI95] | saves / harms / ties | McNemar p | vs PLAN: left -> right % | delta pp [CI95] | saves / harms / ties |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| intent (`scenario_action_exact`) | 83.59 -> 83.16 | -0.43 [-1.13, +0.20] | 34 / 47 / 2,929 | 0.182 | 78.67 -> 83.16 | +4.49 [+2.69, +6.42] | 218 / 83 / 2,709 |
| `action_exact` | 86.25 -> 85.71 | -0.53 [-1.18, +0.07] | 27 / 43 / 2,940 | 0.072 | 80.63 -> 85.71 | +5.08 [+3.09, +7.39] | 224 / 71 / 2,715 |
| `scenario_exact` | 88.11 -> 87.97 | -0.13 [-0.60, +0.33] | 25 / 29 / 2,956 | 0.683 | 85.18 -> 87.97 | +2.79 [+0.95, +4.70] | 168 / 84 / 2,758 |
| per-row slot F1 (exact) | 34.05 -> 33.79 | -0.26 [-1.35, +0.86] | 142 / 127 / 2,741 | 0.393 | 33.20 -> 33.79 | +0.59 [-0.78, +1.97] | 214 / 166 / 2,630 |
| per-row SLU F1 (mean, NOT the official metric) | 40.98 -> 39.26 | -1.72 [-2.79, -0.71] | 177 / 219 / 2,614 | 0.039 | 39.97 -> 39.26 | -0.71 [-2.04, +0.52] | 253 / 270 / 2,487 |

Recording channel, intent (`scenario_action_exact`): vs COMP-1b, far-field -0.51 (18 / 26, n 1,554) and headset
-0.34 (16 / 21, n 1,456); vs PLAN, far-field +4.70 (123 / 50) and headset +4.26 (95 / 33). Per-row SLU F1 mean vs
COMP-1b: far-field -1.97, headset -1.45.

The per-row mean SLU F1 weights every row equally. It is not what `evaluate.py` reports, so it is never substituted
for the official pooled number. Its decrease agrees with the recall cost in section 4.3: fewer emitted entities lose
partial credit on some rows while the pooled false positives fall. This note records the direction and does not
interpret it further.

## 4. Per-intent tables and strata aggregates

### 4.1 The 58 intent strata (both contrasts)

These are conditional within-stratum values from `scorer-strata-aggregate.json`. They are the same in the natural and
equal weightings; only the pooled rows above weight them differently. The CIs come from the within-stratum paired
cluster bootstrap. They are descriptive, with no multiplicity correction, and no stratum selects or adopts anything.
Strata moving up / down / flat, vs COMP-1b: intent 9 / 17 / 32, SLU 34 / 18 / 6. vs PLAN: intent 30 / 15 / 13,
SLU 37 / 16 / 5.

| Intent stratum | n | Intent PLAN / COMP-1b / composed % | Intent d vs COMP-1b pp [CI95] | Intent d vs PLAN pp [CI95] | SLU PLAN / COMP-1b / composed % | SLU d vs COMP-1b pp [CI95] | SLU d vs PLAN pp [CI95] |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| alarm_query | 63 | 95.24 / 84.13 / 82.54 | -1.59 [-4.84, 0.00] | -12.70 [-27.87, 0.00] | 83.16 / 84.77 / 74.84 | -9.93 [-24.18, 0.00] | -8.32 [-24.92, 0.00] |
| alarm_remove | 48 | 87.50 / 89.58 / 87.50 | -2.08 [-7.32, 0.00] | 0.00 [0.00, 0.00] | 76.19 / 65.62 / 73.68 | +8.06 [0.00, +17.83] | -2.51 [-25.38, +13.35] |
| alarm_set | 82 | 87.80 / 87.80 / 90.24 | +2.44 [-2.38, +6.78] | +2.44 [-7.14, +10.84] | 82.36 / 85.80 / 93.63 | +7.83 [-0.58, +12.96] | +11.27 [+3.13, +17.43] |
| audio_volume_down | 32 | 93.75 / 96.88 / 93.75 | -3.12 [-10.00, 0.00] | 0.00 [-8.57, +11.43] | 75.42 / 71.57 / 78.07 | +6.50 [-8.20, +9.98] | +2.65 [-10.01, +9.98] |
| audio_volume_mute | 88 | 72.73 / 85.23 / 85.23 | 0.00 [-7.27, +5.26] | +12.50 [-3.70, +31.58] | 40.00 / 33.33 / 30.00 | -3.33 [-20.44, +25.10] | -10.00 [-34.12, +5.50] |
| audio_volume_other | 16 | 50.00 / 31.25 / 31.25 | 0.00 [0.00, 0.00] | -18.75 [-25.00, 0.00] | 31.32 / 31.32 / 31.32 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| audio_volume_up | 78 | 91.03 / 89.74 / 89.74 | 0.00 [0.00, 0.00] | -1.28 [-6.12, 0.00] | 0.00 / 0.00 / 0.00 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| calendar_query | 74 | 47.30 / 77.03 / 75.68 | -1.35 [-4.48, 0.00] | +28.38 [+15.94, +42.86] | 59.22 / 75.61 / 74.53 | -1.08 [-7.59, +5.29] | +15.31 [+0.50, +32.23] |
| calendar_remove | 66 | 93.94 / 89.39 / 89.39 | 0.00 [0.00, 0.00] | -4.55 [-16.67, +3.57] | 81.70 / 77.29 / 80.11 | +2.82 [-8.35, +21.09] | -1.59 [-18.86, +18.68] |
| calendar_set | 145 | 73.10 / 88.97 / 90.34 | +1.38 [-1.55, +4.71] | +17.24 [+6.77, +29.29] | 68.92 / 68.26 / 69.94 | +1.68 [-0.50, +4.45] | +1.02 [-3.19, +5.05] |
| cooking_recipe | 49 | 93.88 / 95.92 / 97.96 | +2.04 [0.00, +7.69] | +4.08 [0.00, +9.43] | 69.69 / 75.07 / 76.26 | +1.19 [-0.48, +2.13] | +6.58 [-0.27, +22.38] |
| datetime_convert | 22 | 81.82 / 72.73 / 72.73 | 0.00 [0.00, 0.00] | -9.09 [-22.22, 0.00] | 71.77 / 78.26 / 82.68 | +4.42 [+1.23, +9.40] | +10.91 [+1.72, +25.18] |
| datetime_query | 67 | 98.51 / 98.51 / 98.51 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 75.97 / 74.39 / 74.25 | -0.14 [-12.09, +4.60] | -1.72 [-13.29, +2.49] |
| email_addcontact | 32 | 96.88 / 93.75 / 93.75 | 0.00 [0.00, 0.00] | -3.12 [-5.56, 0.00] | 29.41 / 23.98 / 32.53 | +8.55 [0.00, +23.97] | +3.13 [-4.70, +8.94] |
| email_query | 91 | 85.71 / 86.81 / 86.81 | 0.00 [0.00, 0.00] | +1.10 [-4.29, +6.90] | 62.36 / 66.38 / 74.74 | +8.36 [+2.66, +17.64] | +12.38 [+4.99, +20.90] |
| email_querycontact | 32 | 71.88 / 84.38 / 81.25 | -3.12 [-10.34, 0.00] | +9.38 [0.00, +20.69] | 57.00 / 55.28 / 59.66 | +4.39 [-2.88, +13.52] | +2.66 [-7.89, +12.23] |
| email_sendemail | 81 | 90.12 / 93.83 / 93.83 | 0.00 [0.00, 0.00] | +3.70 [0.00, +8.82] | 52.19 / 57.03 / 58.23 | +1.20 [-7.34, +6.97] | +6.05 [-4.49, +14.45] |
| general_joke | 84 | 100.00 / 98.81 / 98.81 | 0.00 [0.00, 0.00] | -1.19 [-2.60, 0.00] | 60.92 / 64.24 / 70.83 | +6.60 [-21.21, +19.35] | +9.91 [-21.48, +21.57] |
| general_quirky | 91 | 14.29 / 20.88 / 18.68 | -2.20 [-8.57, +3.81] | +4.40 [-5.45, +15.30] | 46.41 / 42.57 / 37.35 | -5.21 [-14.02, +6.56] | -9.05 [-20.05, +6.26] |
| iot_cleaning | 51 | 72.55 / 74.51 / 72.55 | -1.96 [-3.95, 0.00] | 0.00 [-21.43, +11.32] | 62.80 / 56.12 / 52.55 | -3.58 [-12.14, +0.26] | -10.25 [-21.05, -4.86] |
| iot_coffee | 39 | 100.00 / 100.00 / 100.00 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 82.76 / 63.38 / 88.89 | +25.51 [0.00, +42.59] | +6.13 [0.00, +29.32] |
| iot_hue_lightchange | 29 | 75.86 / 82.76 / 82.76 | 0.00 [0.00, 0.00] | +6.90 [0.00, +20.00] | 82.19 / 85.71 / 90.91 | +5.19 [0.00, +13.89] | +8.72 [0.00, +17.97] |
| iot_hue_lightdim | 48 | 77.08 / 81.25 / 72.92 | -8.33 [-15.74, +26.67] | -4.17 [-8.11, +18.75] | 7.69 / 9.09 / 14.29 | +5.19 [0.00, +38.10] | +6.59 [0.00, +36.67] |
| iot_hue_lightoff | 61 | 91.80 / 96.72 / 96.72 | 0.00 [0.00, 0.00] | +4.92 [0.00, +13.33] | 59.51 / 63.48 / 73.25 | +9.77 [-0.06, +19.92] | +13.75 [-0.02, +25.56] |
| iot_hue_lighton | 1 | 0.00 / 0.00 / 0.00 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 100.00 / 100.00 / 100.00 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| iot_hue_lightup | 32 | 96.88 / 96.88 / 96.88 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 61.54 / 88.89 / 80.00 | -8.89 [-80.00, +20.00] | +18.46 [-47.09, +55.56] |
| iot_wemo_off | 22 | 81.82 / 81.82 / 86.36 | +4.55 [0.00, +13.64] | +4.55 [-11.76, +21.05] | 58.96 / 63.78 / 69.05 | +5.27 [-7.14, +11.30] | +10.10 [-5.24, +18.57] |
| iot_wemo_on | 21 | 95.24 / 80.95 / 80.95 | 0.00 [-14.29, +12.50] | -14.29 [-33.33, 0.00] | 82.91 / 77.67 / 78.80 | +1.14 [-7.08, +9.26] | -4.10 [-19.01, +7.37] |
| lists_createoradd | 46 | 65.22 / 71.74 / 67.39 | -4.35 [-10.17, 0.00] | +2.17 [0.00, +5.08] | 72.69 / 65.51 / 68.00 | +2.48 [-9.62, +18.44] | -4.69 [-17.35, +13.99] |
| lists_query | 63 | 47.62 / 44.44 / 46.03 | +1.59 [0.00, +6.98] | -1.59 [-2.86, 0.00] | 17.14 / 40.00 / 26.67 | -13.33 [-23.81, 0.00] | +9.52 [-16.97, +17.95] |
| lists_remove | 69 | 76.81 / 78.26 / 82.61 | +4.35 [0.00, +10.17] | +5.80 [-3.77, +13.33] | 61.21 / 57.89 / 68.65 | +10.76 [-2.47, +36.56] | +7.44 [-3.20, +31.82] |
| music_dislikeness | 10 | 100.00 / 100.00 / 100.00 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 / 0.00 / 0.00 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| music_likeness | 43 | 67.44 / 79.07 / 76.74 | -2.33 [-5.77, 0.00] | +9.30 [0.00, +23.08] | 12.85 / 20.40 / 18.93 | -1.46 [-9.34, +38.05] | +6.08 [0.00, +49.73] |
| music_query | 39 | 64.10 / 79.49 / 76.92 | -2.56 [-8.51, 0.00] | +12.82 [0.00, +31.58] | 0.00 / 0.00 / 0.00 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| music_settings | 13 | 38.46 / 30.77 / 23.08 | -7.69 [-25.00, 0.00] | -15.38 [-80.00, +50.00] | 53.85 / 66.67 / 66.67 | 0.00 [0.00, 0.00] | +12.82 [0.00, +42.86] |
| news_query | 90 | 82.22 / 82.22 / 80.00 | -2.22 [-6.67, 0.00] | -2.22 [-7.32, +2.70] | 54.75 / 48.11 / 60.44 | +12.34 [+1.10, +31.05] | +5.70 [-6.55, +23.90] |
| play_audiobook | 71 | 60.56 / 66.20 / 64.79 | -1.41 [-5.56, 0.00] | +4.23 [0.00, +10.91] | 49.85 / 53.48 / 47.86 | -5.61 [-9.77, -0.25] | -1.99 [-8.07, +6.81] |
| play_game | 38 | 89.47 / 89.47 / 92.11 | +2.63 [0.00, +9.38] | +2.63 [0.00, +9.38] | 63.22 / 62.07 / 69.57 | +7.50 [+1.04, +15.15] | +6.34 [-5.90, +17.93] |
| play_music | 125 | 64.80 / 83.20 / 80.00 | -3.20 [-8.25, +0.79] | +15.20 [+4.63, +26.92] | 68.79 / 66.52 / 62.97 | -3.55 [-8.97, +2.40] | -5.82 [-17.18, +4.51] |
| play_podcasts | 105 | 68.57 / 87.62 / 87.62 | 0.00 [-4.11, +1.92] | +19.05 [0.00, +35.29] | 36.33 / 34.75 / 34.40 | -0.36 [-4.29, +9.35] | -1.93 [-9.01, +16.34] |
| play_radio | 74 | 75.68 / 75.68 / 77.03 | +1.35 [0.00, +4.62] | +1.35 [-8.11, +12.12] | 50.44 / 45.07 / 52.75 | +7.68 [+2.24, +14.02] | +2.31 [-5.15, +10.19] |
| qa_currency | 44 | 100.00 / 100.00 / 97.73 | -2.27 [-7.15, 0.00] | -2.27 [-7.15, 0.00] | 66.64 / 69.55 / 71.40 | +1.85 [-2.34, +7.42] | +4.77 [0.00, +9.32] |
| qa_definition | 57 | 78.95 / 89.47 / 89.47 | 0.00 [0.00, 0.00] | +10.53 [0.00, +21.52] | 68.50 / 76.14 / 81.16 | +5.02 [-1.54, +10.62] | +12.66 [+1.82, +24.04] |
| qa_factoid | 88 | 71.59 / 77.27 / 76.14 | -1.14 [-4.05, 0.00] | +4.55 [-4.60, +13.70] | 63.07 / 62.31 / 66.40 | +4.09 [+1.49, +8.51] | +3.33 [+0.73, +7.84] |
| qa_maths | 24 | 100.00 / 100.00 / 100.00 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 72.73 / 72.73 / 0.00 | -72.73 [-100.00, 0.00] | -72.73 [-96.00, 0.00] |
| qa_stock | 29 | 86.21 / 79.31 / 79.31 | 0.00 [0.00, 0.00] | -6.90 [-34.62, +7.89] | 75.30 / 72.81 / 76.09 | +3.28 [0.00, +8.81] | +0.79 [-1.81, +7.23] |
| recommendation_events | 36 | 83.33 / 83.33 / 83.33 | 0.00 [0.00, 0.00] | 0.00 [-9.38, +7.14] | 51.23 / 48.03 / 51.32 | +3.28 [-6.48, +11.90] | +0.08 [-12.92, +12.70] |
| recommendation_locations | 23 | 86.96 / 95.65 / 100.00 | +4.35 [0.00, +16.67] | +13.04 [0.00, +30.43] | 69.53 / 76.04 / 74.74 | -1.31 [-7.83, +9.01] | +5.21 [-1.78, +17.87] |
| recommendation_movies | 28 | 96.43 / 100.00 / 100.00 | 0.00 [0.00, 0.00] | +3.57 [0.00, +14.29] | 45.00 / 46.51 / 50.00 | +3.49 [0.00, +18.62] | +5.00 [-2.11, +25.00] |
| social_post | 54 | 90.74 / 94.44 / 94.44 | 0.00 [0.00, 0.00] | +3.70 [0.00, +10.00] | 70.72 / 72.10 / 71.66 | -0.45 [-8.03, +3.98] | +0.93 [-4.68, +6.15] |
| social_query | 26 | 73.08 / 80.77 / 80.77 | 0.00 [0.00, 0.00] | +7.69 [0.00, +23.08] | 57.14 / 59.40 / 68.07 | +8.66 [-6.16, +25.60] | +10.92 [-3.03, +25.27] |
| takeaway_order | 36 | 41.67 / 75.00 / 75.00 | 0.00 [0.00, 0.00] | +33.33 [+4.17, +54.55] | 69.98 / 71.68 / 72.23 | +0.55 [-4.27, +9.25] | +2.25 [-4.73, +11.92] |
| takeaway_query | 36 | 97.22 / 86.11 / 86.11 | 0.00 [0.00, 0.00] | -11.11 [-29.03, 0.00] | 62.96 / 64.25 / 60.76 | -3.49 [-10.22, +2.46] | -2.20 [-10.54, +5.79] |
| transport_query | 34 | 91.18 / 91.18 / 91.18 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 74.70 / 72.73 / 70.01 | -2.72 [-12.96, +1.64] | -4.69 [-18.99, +2.61] |
| transport_taxi | 18 | 100.00 / 100.00 / 100.00 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 59.49 / 63.83 / 66.35 | +2.52 [-21.68, +14.88] | +6.86 [-10.89, +16.40] |
| transport_ticket | 35 | 91.43 / 97.14 / 97.14 | 0.00 [0.00, 0.00] | +5.71 [0.00, +17.14] | 73.23 / 69.57 / 71.07 | +1.50 [-4.78, +6.09] | -2.16 [-9.48, +2.07] |
| transport_traffic | 22 | 100.00 / 100.00 / 100.00 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 64.68 / 60.98 / 65.95 | +4.97 [-5.71, +25.45] | +1.28 [-10.10, +25.45] |
| weather_query | 89 | 95.51 / 98.88 / 98.88 | 0.00 [0.00, 0.00] | +3.37 [0.00, +9.78] | 62.03 / 65.26 / 64.09 | -1.17 [-4.94, +1.77] | +2.05 [-1.79, +5.58] |

Small-denominator strata swing hard. `qa_maths` (n 24) SLU 72.73 -> 0.00 rests on a handful of gold entities, and
`iot_hue_lighton` has n 1; read such rows as counts, not rates. vs COMP-1b, the per-stratum intent harms concentrate
in `iot_hue_lightdim` (2 saves / 6 harms) and `play_music` (3 / 7). The SLU strata with CI95 excluding zero are
`email_query` +8.36, `news_query` +12.34, `play_radio` +7.68, `play_game` +7.50, `qa_factoid` +4.09 and
`datetime_convert` +4.42 (up), and `play_audiobook` -5.61 (down).

### 4.2 Scenario roll-up (natural weights, point estimates only)

This note derived this table from the per-stratum counts in `scorer-strata-aggregate.json` and the registered
population weights. It reproduces the pooled post-stratified levels exactly: PLAN 77.02 / 64.18, COMP-1b
82.82 / 64.98, composed 82.36 / 66.65. Intent is the weight-normalised mean of the scenario's intent strata. SLU-F1 is
F1 of the weighted pooled counts. No scenario CI is claimed, because the registered bootstrap has no scenario-level
draws.

| Scenario | intent strata | n | Natural intent d vs COMP-1b | Natural SLU d vs COMP-1b | Natural intent d vs PLAN | Natural SLU d vs PLAN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 3 | 193 | +0.04 | +4.52 | -3.11 | +5.41 |
| audio | 4 | 214 | -0.44 | +2.95 | +5.52 | -1.70 |
| calendar | 3 | 285 | +0.25 | +1.32 | +16.90 | +3.01 |
| cooking | 1 | 49 | +2.04 | +1.19 | +4.08 | +6.58 |
| datetime | 2 | 89 | 0.00 | +0.68 | -0.87 | +0.16 |
| email | 4 | 236 | -0.31 | +4.66 | +2.79 | +7.75 |
| general | 2 | 175 | -1.84 | -3.27 | +3.48 | -5.75 |
| iot | 9 | 304 | -1.04 | +2.71 | +1.26 | +1.50 |
| lists | 3 | 178 | +0.86 | +5.43 | +2.12 | +6.09 |
| music | 4 | 105 | -2.62 | +2.69 | +8.64 | +10.75 |
| news | 1 | 90 | -2.22 | +12.34 | -2.22 | +5.70 |
| play | 5 | 413 | -1.15 | -1.55 | +10.73 | -2.40 |
| qa | 5 | 242 | -0.92 | +2.83 | +3.36 | +4.82 |
| recommendation | 3 | 87 | +1.35 | +2.11 | +4.98 | +3.53 |
| social | 2 | 80 | 0.00 | +0.76 | +5.00 | +2.11 |
| takeaway | 2 | 72 | 0.00 | -1.77 | +3.65 | -0.22 |
| transport | 4 | 109 | 0.00 | +0.32 | +1.90 | -1.39 |
| weather | 1 | 89 | 0.00 | -1.17 | +3.37 | +2.05 |

### 4.3 Pooled counts behind official SLU-F1 (raw roster, summed over the 58 strata)

| arm | TP | FP | FN | TP + FP (emitted) | official SLU-F1 = 2TP / (2TP + FP + FN) | intent correct / 3,010 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| PLAN (successor 1) | 3,724 | 2,382.63 | 1,910.63 | 6,106.63 | 63.43 | 2,368 |
| COMP-1b (successor 1) | 3,782 | 2,391.18 | 1,837.18 | 6,173.18 | 64.14 | 2,516 |
| composed (successor 2) | 3,562 | 1,708.92 | 1,912.92 | 5,270.92 | 66.30 | 2,503 |

These are the counts the official SLU-F1 pools. FP and FN carry `evaluate.py`'s fractional distance credits, so they
are not exact-match entity counts, and TP + FN is not constant across arms. The aggregate reproduces each arm's official
pooled SLU-F1 exactly. Against COMP-1b, the composed system emits 902 fewer (weighted) entity predictions: FP -682.3,
TP -220, FN +75.7. The SLU-F1 gain is a precision gain bought with some recall. This READ's aggregates do not carry
the exact-match entity TP/FP/FN or the zero-gold-row false-entity counts that successor 1 reported from its
completion package (TP 1,401 -> 1,437, FP 1,320 -> 1,325, FN 1,084 -> 1,048; 1,255 zero-gold rows). Those counts are
**not available** for successor 2 without a new read, which this note does not perform.

## 5. Decision 252, clause 3: the published SLURP rows beside the repo numbers

| system | split / population | intent (`scenario_action`) % | SLU-F1 % | source and caveat |
| --- | --- | ---: | ---: | --- |
| Gold / HerMiT | full official test split (2,974 sentences / 13,078 recordings), **gold transcripts** | 84.84 | 78.19 | arXiv:2011.13205 Tables 7-8; an oracle-transcript **upper bound, never a peer** |
| Multi-SLURP / HerMiT | full test split, audio | 78.33 | 70.84 | arXiv:2011.13205 Tables 7-8; strong ASR-to-NLU pipeline **trained on SLURP** |
| Google / SF-ID | full test split, audio | 72.06 | 64.02 | arXiv:2011.13205 Tables 7-8; commercial ASR into a trained SLU model (the weakest published trained pipeline) |
| ChatGPT, 0-shot prompt-only | gold (oracle) transcripts, 60 intents | 79.25 | -- | He and Garner, arXiv:2305.13512; text-only on oracle transcripts; no published SLU-F1 |
| repo: bare frozen core (direct call) | **DEV-2000-ADDED only** (1,000 devel recordings); no test-sample arm exists | 61.7 | 38.09 | `docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md`; a different split, shown for scale only |
| repo: PLAN (successor 1) | test sample, post-stratified natural mixture (raw 78.67 / 63.43) | 77.02 | 64.18 | this read, `vs-plan` |
| repo: COMP-1b (successor 1) | test sample, post-stratified natural mixture (raw 83.59 / 64.14) | 82.82 | 64.98 | this read, `vs-comparator` |
| **repo: composed v2.2 (successor 2)** | test sample, post-stratified natural mixture (raw 83.16 / 66.30) | **82.36** | **66.65** | this read |

Published values are quoted, not recomputed, from `docs/readiness/2026-09-04-scoring-alignment-audit-slurp-earnings.md`
(sections 2 and 2.1), `docs/readiness/2026-09-19-slurp-test-split-one-read-protocol-v1-draft.md` (published ladder) and
`docs/results/2026-09-26-slurp-intent-label-ceiling-audit.md`.

Gaps, in pp, composed minus the published row. Intent: +4.03 vs HerMiT, +10.30 vs SF-ID, +3.11 vs ChatGPT 0-shot,
-2.48 vs the gold-transcript bound. SLU-F1: +2.63 vs SF-ID, **-4.19 vs HerMiT**, -11.54 vs the gold-transcript bound.
The SLU-F1 gap to the strong trained pipeline narrowed from 5.86 (COMP-1b) to 4.19 on this sample. As every headroom
table on file has said, the remaining distance is entities, not intent.

**This comparison is indicative, not a claim.** (1) The sample is 3,010 recordings / 682 prompts drawn from the test
split, with 58 of 59 represented intents (`general_greet` absent) and post-stratified weights renormalised over those
58. It is **not the full test split**, and our numbers carry sample CIs only on the deltas, not on the levels.
(2) Every published audio row is a system **trained on SLURP** and scored on the full split. Ours is a frozen,
zero-parameter core behind an API-shaped boundary with a training-free control plane. (3) The ChatGPT and gold-HerMiT
rows read oracle transcripts. (4) Scoring here is free-form `{scenario, action}` strings against gold with the
official `evaluate.py`; the published label-space conventions differ (60 / 65 / 69 intents are reported downstream).
(5) This is a development milestone (decision 28). Decision 252 makes the SOTA comparison on the test set one of three
lock modes. Whether this sample observation counts toward that mode is the owner's ruling, not this note's.

## 6. Efficiency and cost

| field | PLAN (successor 1) | COMP-1b (successor 1) | composed (successor 2) | composed vs COMP-1b |
| --- | ---: | ---: | ---: | ---: |
| contacts | 12,305 | 12,214 | **6,020** | -6,194 (-50.7 %) |
| contacts per row | 4.0880 | 4.0578 | **2.0000** | -2.0578 |
| role visits per row (histogram) | 2: 32, 4: 2,879, 7: 99 | 2: 30, 4: 2,912, 7: 68 | 2: 3,010 | Reviewer loop off |
| prompt tokens per row | 34,053.8 | 35,524.0 | 14,048.5 | -21,475.5 (-60.5 %) |
| measured prefilled tokens per row | 8,390.3 | 8,963.1 | 8,479.5 | -483.6 (-5.4 %) |
| completion tokens per row | 247.7 | 245.5 | 137.9 | -107.6 |
| active GPU hours (serving monitor) | 4.6854 | 4.9392 | **3.7236** | -1.2156 (-24.6 %) |
| GPU hours per 1,000 rows | 1.5566 | 1.6409 | 1.2371 | -0.4039 |
| GPU hours per 1,080 rows (decision 75 frontier) | 1.6811 | 1.7722 | 1.3360 | -0.4362 |
| generation wall seconds | 17,251.4 | 18,074.5 | 13,955.4 | -4,119.1 (-22.8 %) |
| contacts per minute | 42.80 (derived) | 40.55 | 25.88 | -14.66 |
| mean GPU utilisation % | 84.06 | 85.28 | 84.17 | -1.10 |
| repeated speech-audio seconds | 33,645.6 | 33,354.7 | 16,412.9 | -16,941.8 |
| tool calls | 0 | 0 | 0 | 0 |

The composed arm halves the contacts and cuts prompt tokens by about 60 %. GPU time falls by only about a quarter,
because most of COMP-1b's extra prompt tokens were served from the prefix cache: measured prefilled tokens per row are
nearly equal. The ledger's 4 h 02 m is the arm wall time; the 13,955 s (3 h 52.6 m) above is the generation stage
alone. Frontier effects, composed vs COMP-1b: intent -0.43 pp and SLU-F1 +2.15 pp (raw) at -0.44 GPU-h per 1,080 rows.
Composed vs PLAN: intent +4.49 pp at -0.35 GPU-h per 1,080 rows, 3.36 intent pp per GPU-h per 1,080 rows. Quality and
cost move together here, but this read claims no Pareto dominance beyond these measured rows.

Structural and delivery (gold-free). All three arms admitted 3,010 / 3,010 rows with a native episode receipt, 0
context-fit compactions and 0 tool calls. Every arm delivered 3,010 answers, with 0 missing. Each arm's flown
first-phase boundary sets equal its own pinned prepared supply on all 3,010 rows. Mismatched rows are 0; one row per
arm uses the permitted empty default. Boundary-selected rows: PLAN 2,547, COMP-1b 2,659, composed 2,637. Wire contacts
equal sealed calls and prompt-token totals equal sealed cost in every arm. The delivery normaliser changed 599
composed answers (v4g) against 313 (COMP-1b, v3) and 327 (PLAN, v3). Its label branches: already-legal 2,868 / 2,895 /
2,874, r-action 133 / 104 / 125, edit-distance 7 / 8 / 10 (composed / COMP-1b / PLAN). The gold-bank extension is
NOT_APPLICABLE on a final-report roster (coordinator ruling 2026-09-30).

## 7. What the verdict means and what it does not

- **It means** the composed system did not lose COMP-1b's accuracy on the signed sample, within what a cross-flight read can resolve. It did so at half the contacts and about three quarters of the GPU time. The registered question (`the_question`) is answered yes. This is the efficiency result the cell registered.
- **It means** the SLU-F1 point is positive with CI95 excluding zero in the primary and raw weightings. The point is larger than on DEV, where the same system was NEUTRAL at +1.24 [-0.29, +2.80]. The DEV read attributed most of that +1.24 to the v4g delivery gain (+0.98 offline on the A2 arm), with the review-off change itself at +0.27 [-1.17, +1.72]. This flight did not separate v4g from review-off on the sample.
- **It does not mean** a resolved SLU-F1 gain. The primary lower bound (+0.53) is under the declared offset (0.73), the equal-stratum interval crosses zero, and the cell's `claims_benefit` is false. Under the registered rule, a point above the bar would be reported and would need its own replicated read; +1.67 is under the 2.5 bar in any case.
- **It does not mean** an intent change. vs COMP-1b, intent is flat (-0.47 [-1.04, +0.22]; 34 saves / 47 harms). The +5.34 vs PLAN is the COMP-1b intent gain carried over: successor 1 measured +5.80 [+4.04, +7.42] on this sample, and `docs/results/2026-10-09-slurp-intent-lock-comp1b-v1.md` locks intent at COMP-1b.
- **It does not mean** a test claim, a final read, superiority, generalisation, or a claim about other carriers. Every number is development evidence (decisions 28, 86, 151). The carriers stay held under decision 242 until the decision-252 lock (all three modes) holds.
- **One-shot.** One attempt was flown under the allowance v3 terms, with no smoke, no recovery, no re-score, no re-read and no selection. Nothing was tuned on the sample: the vote pool and centroid key are TRAIN artifacts, v4g was selected on DEV and confirmed on TRAIN folds (`docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md`), and COMP-1b was selected on DEV-2000-ADDED. The sealed successor-1 columns were not re-flown, re-scored or re-read beyond the registered pairing. **The next test-sample read needs a new owner allowance and fresh run ids.** These aggregates must not enter proposer contexts, knowledge construction, search selection, candidate selection or runtime memory.

## 8. Pointers (sha256)

Analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-PAIRED-ANALYSIS-V1/`:

| file | `vs-comparator/` | `vs-plan/` |
| --- | --- | --- |
| score-contrasts.json | `4ceed95bc3aa178f9925b750c6eb92fb510736f136ffe616ce97121ba38b024c` | `61171f49e0e27f3714e5e11573d333a84bbebfc108f553901a4b421894fb781c` |
| per-scenario-tables.json | `1bed91f81148b7681300e66029bba3cef47810c0edb42c47cfe6d1e0b6f61d6f` | `5f93050b818b4dbfe022c1435e018a40fdcd8826cbea635e0af39c60114a026e` |
| scorer-strata-aggregate.json | `08186df53d8133d73573919193c677c9743200306b5d8d9f3ac67cc7cfc34bad` (receipt `f4f9e885...`) | `9482b2e7110f31bce1a757f3cc9032118415e9b15849bedf1e6aa0da918b9576` |
| delivery-conversion.json | `ac54fc966edc02669b9450e959e249cde60f4e80c5d9b79f489965573224be27` | `a55aab26597b47ec210cb7860f86a734be1f7e61a2975420c559d146c343d9ca` |
| efficiency.json | `7150d9b8315baef5ad58e48afc4c5b63819a8b5caa7e7960da2899bf36732c45` | `7e2ae73a96fd36a3c733249c4aa79a178e7cf5679ecb804c337073f94620d926` |
| frontier.json | `3cbf0b989a188ce4c7f8f2b4ab3325195cb8457404d4868fe1c43f2f1485c705` | `563ddea8ed622e9f4ccd18d736cac69b5a613a5b787be67c247784a7fbbb0fb9` |
| structural.json | `809abe9c6315acca00339b5937c3feaf91061c26ba1f1f63263784889d9a1833` | `212914731c3e08d24f056efe08c749a9f8bfbe3084dff6bb3901390ab4ea5363` |
| stop.json | `81841f1a4f4ac5eee9b686a137f33875956e81ea0b539dc68964e92025d1de8b` | `ded9036fe3488c73439f0f5fd4df8f2b1cd9d8a5686d4997c30836159261f432` |
| verdict.json | `ffc29ab92b4931731e1eb99923ea45f2502a58bd5e3d23a35ac54707cf145320` | `38130ead4ebee011757ff15f628b05bdf56145a3e43b9a1f50232cde6ef0a9b0` |
| README.md | `f514cc79037948d42646e3bf588aa425eeb0c5f97e04557c9a0f27008a4e65fe` | `ae96fb0f90f29200bf749dad0633f34692d633dbd0e725e5ac471ba81f7f19bf` |

Repository (bytes at master `dbf46d209`):

| file | sha256 |
| --- | --- |
| `docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1/README.md` | `2f2aa8e648164208e55c09f2ddbac0904c248687770b19a492bd16f7715656b0` |
| `.../protocol-registered-v1.json` | `dfa5f8685504f189211491503f82e87b2cdac5eefb101d8b3765809869be0fbc` |
| `.../registered-facts-v1.json` | `493da5ab58a7394756618735985a8fb6637b5c500f60607da221eeccc47df976` |
| `.../analysis-recipe-v1.json` | `3743537441f9d9e9425509f2a3a76781a486face119db424675bb5c97844c72e` |
| `.../population-counts-v1.json` | `7f8a536fc02db6ad7896cac818deaaa3faaf18f5f065bee0b2ee10ca5d5e0c66` |
| `.../read-qualification-v1.md` | `2d748ac18f10124274957db0ee9445994428ed9975d04b8cf848feff31e347a7` |
| `.../successor-identity-map.json` | `d0b3e1a4a410886ebb4882511f9e0230d72d2299a6e59f122d38a3867465a67f` |
| `.../generation-plan-registered-v1.json` | `e2d3a86774cba6f3cb84a948a88a484b02f43e9d4d7e658025130aaade686ec7` |
| `.../fit-plan-registered-v1.json` | `e7623f1daf465e025d9f0cd13e12ba91eb5a9b56cb0f29524048fd3bc51633bc` |
| `docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1-preregistration.md` | `1f0ee0387a7fe4b64c9c9ec43d89c47be4d08194673c8098170c6789875ca207` |
| `docs/receipts/owner/2026-10-10-slurp-test-sample-successor2-allowance-v1.json` | `4e04b23f89b9eb06c1b228649a6f991fb9399dea6efbaf4d168a4b731d9e388d` |
| `docs/receipts/rosters/slurp-test-sample-3010-v1.json` | `48d9fb336ce99ad1725bf5ca0f74687d37711d685fa9fb4f594b2f1d88344e6d` |
| `docs/results/2026-10-01-slurp-milestone-successor1-read.md` (format model; successor-1 numbers) | `ec16ec12c67701d5384b53708b759a467e40b7b2ede8d621171b7baeb3028281` |
| `docs/results/2026-10-10-slurp-nx-r5-composed-dev2000-added-read.md` (the DEV read of this system) | `8fdd454efeb689dd7d7fe1abdbbd60c47962269dd86d90183e36e4a154932b54` |

Related notes: `docs/results/2026-10-09-slurp-intent-lock-comp1b-v1.md` (intent lock at COMP-1b, decision 229);
`docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md` (v4g lock); `docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md`
(bare core vs PLAN on DEV); `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, section "Decisions
249-252 ruled by the owner, 2026-10-10"; exposure-ledger rows `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1`,
`...-COMPOSED-FIT-V1` and `...-PAIRED-ANALYSIS-V1` (the READ row's countersignature carries the seal facts in section 1).
