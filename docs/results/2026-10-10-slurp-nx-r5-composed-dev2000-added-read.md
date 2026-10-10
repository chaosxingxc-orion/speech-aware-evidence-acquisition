# NX round R5 (the composed system, review-off COMP-1b on lock v2.2 with v4g, DEV-2000-ADDED): NEUTRAL under the registered rule; SLU-F1 +1.24 [-0.29, +2.80] and intent +0.50 [-0.51, +1.52] against the sealed A2 arm at 2.00 instead of 4.05 contacts per row; under one normaliser the review-off change itself is +0.27 [-1.17, +1.72]

Read 2026-10-10 by Claude Opus 5.5 (results agent, on the coordinator's brief, Fable 5.1) in the worktree
`opus/nx-r5-results`. Model-free: this note opened no model, server, encoder, embedder, tokenizer, scorer or GPU and
wrote nothing under the data root. It reads the on-file outputs of the registered read
`SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-PAIRED-ANALYSIS-V1` (four stage-3 paired passes and the v4g contrast
report) and the exposure-ledger countersign text for the two sealed arms. No utterance text, transcript, gold value,
slot filler, note body or model output was printed or persisted. Only counts, rates, pp, CIs, ids, hashes and
scenario labels appear below.

**DESCRIPTIVE.** These are development numbers on the DEV-2000-ADDED roster (owner decisions 28 and 86). They are
never a test claim, never an admission and never a system-level claim. The verdict word is the coordinator's (owner
decision 139); this note applies the rule registered in the package README section 5.

## 0. Answer in eight lines

1. Verdict under the registered rule: **NEUTRAL**. Composed minus the sealed A2 arm: SLU-F1 +1.24 [-0.29, +2.80], intent +0.50 [-0.51, +1.52]. Both CI95 lower bounds are above -2.5 pp. The SLU lower bound is not above the offset |o| = 0.73, and the point is under the 2.5 pp bar, so the read is not NOMINATED. No upper bound is below -|o|, so it is not HARM.
2. It is an efficiency result. The review-off composition keeps the full graph's SLU-F1 and intent within the cross-flight resolution at 2.00 contacts per row against 4.05 (-2.05): -0.32 GPU-h per 1,000 rows, -103.9 completion and -22,687 prompt tokens per row.
3. Delivered official pooled SLU-F1 on the same 1,000 rows: A2 A/A 65.40, A2 arm 65.93, in-chain replicate 66.13, composed **67.18**. The composed column is the highest of the four.
4. The offset instrument behaved. Replicate minus A2 A/A is SLU +0.73 [-0.53, +2.02] and intent +0.20 [-0.90, +1.31], inside the cross-flight floor (1.2525 / 1.152).
5. Under ONE normaliser (v4g applied offline to the sealed v3 columns), v4g(A2 arm) 66.91 to composed 67.18 is SLU **+0.27 [-1.17, +1.72]**. The offline v4g gain on the A2 arm is +0.98 [+0.25, +1.71]. So the delivered SLU gain over A2 is the v4g delivery gain; the review-off change itself is +0.27 with a half-width of about 1.4.
6. Same chain, replicate (COMP-1b components off, full graph, v3) to composed: intent **+4.90 [+2.93, +6.86]** (75 saves / 26 harms on per-row intent). This is the third replication of the COMP-1b intent gain, after A2 +4.60 on this roster and +5.80 on the signed test sample. SLU is +1.05 [-0.77, +2.86]; under v4g it is +0.41 [-1.34, +2.16].
7. The equal-stratum weighting is weaker than the natural mixture on the claim contrast: SLU -0.73 delivered and -0.96 under v4g, intent -0.13. Strata with 4 to 9 rows carry equal weight there.
8. The registered no-harm claim holds within resolution; no gain is claimed. Under owner decision 241, a NEUTRAL R5 read means the second test-sample allowance is drafted next.

## 1. Inputs and identities

| item | value |
| --- | --- |
| composed arm (cell `slurp-native-stage3-nx-r5-composed-dev2000-added-v1`) | run `SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1`, attempt `attempt-slurp-native-stage3-nx-r5-composed-dev2000-added-generation-v1`; run manifest `2312315eb2af7a3e98e558dd01f0c9a1a401839022139ed8d0421aa74e99af3d`; outputs `4e4c7f54593f37f2ecbcac585a9859af6dd3bd2cee519c5eda16ce2eabdcb12b`; scores `281b9ab494a6a6263e25eff7994064b39bc2b00a5a36997fc26be0ea37b1572c`; generation manifest `8e77c4d20e25db57770221327c4f35ad2ac525584fbca6cdc7cc0d5079fa5e0c`; flight receipts `ae45346bab4f27e00bf7479165204223da567f2f59265ee75c8f0ccb9af9e871` |
| in-chain replicate (module OFF arm, package `docs/readiness/2026-09-30-slurp-stage3-module-comp1b-dev2000-added-v1/`) | run `SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1`, attempt `attempt-slurp-native-stage3-module-comp1b-aa-dev2000-added-generation-v1`; run manifest `f25f41315120644774efb9dbb81b82903247b575c6a0849f2a6c987cb6158cca`; outputs `7e58cb3ea0135200c1cfb081e34ab23315b60ca5070dd9de9eb8890c6176a47d`; scores `335c80d63c016c20a387d9b5c16ea3df9a0b5ebdc48e1ec6a6c98486143bbfe0`; generation manifest `3c892e7f3810fb31fc94cd6660da60c2e414a0342b111c1f5305f182be8243c6`; flight receipts `7be5c92bdcd34c5a5090b90e722cdbce74aff59e63253f102f1facda4ab52295` |
| sealed A2 arm (the registered comparator) | run `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1`, attempt `attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1`; manifest `8192451a0471638ec60f57f5e5416b72718898dc94d923ac4f88870c125a5ed8`; outputs `25e6dd9dae842c333e692391280ca4845705666f34e87fab9f78296bc776f4e3`; scores `878babaa69577c5f94bd3f0563e44a6f336535322c6ced3ba757383c872880a9` (flight commit `310110be`) |
| sealed A2 in-chain A/A (offset left side) | run `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1`, attempt `attempt-slurp-native-stage3-comp1-aa-dev2000-added-generation-v1`; manifest `e0aaef84a04eca9bf73b834b69ee4955939a45588310dd000633916dda83a017`; outputs `016b09dcf329178272913a3a6452772c21f724430228dfe1a81693015489f5d9`; scores `0543d025a5a2cbc4e4bb25688ded294fc48dd8ea0f11fba64c4734fce31ac4c6` |
| flight commit (both R5 cells, one campaign chain) | `9a0a3384b0eea234ef612bc6d44d7e1a6bb2e123`; both FINALIZED / COMPLETED, arm-inspect pass, one official score job each; driver-done 06:37:48Z, chain exit 0, no serving restart (ledger countersign text) |
| roster | DEV-2000-ADDED `SLURP-DEV-2000-ADDED-V1`, 1,000 rows (913 `utterance_id` clusters), roster file `docs/receipts/rosters/slurp-dev-2000-added-v1.json` sha256 `f78dd8ad2894b1fd02bfe6050e39e3fb2c5d178a649e5d20e85ea4ecf4b8dc58`, split identity `ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67`; every pass's stop check PASSED |
| READ run | `SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-PAIRED-ANALYSIS-V1`, root countersigned 2026-10-10T06:50:00Z, after both seals and before any score was opened |
| recipe | `slurp-nx-r5-composed-dev2000-added-paired-analysis-v1`, `docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1/analysis-recipe-v1.json` sha256 `f54b5a0d16701f6cc2b189b57087602fea9d1dcdb1fec5b3b7dab940b6ab5758` |
| bootstrap | paired, cluster `utterance_id`, 10,000 draws, seed 20260915 (every pass and the v4g report) |
| scorer | `slurp-slu-official` (DEV sibling), one complete scoring per sealed cell; the read re-derived the official pooled SLU-F1 and span-F1 to within 1.2e-16 (`stop.json`, `official_reproduction_1e6`) |
| normaliser in the offline columns | `saea-deliver-normalise-v4g` |
| read contacts | model, encoder, tokenizer, scorer 0 in every pass; the v4g report also records embedder, GPU, network, paid API and server 0 |

The composed arm is the evidence-consumption module `saea-evidence-consumption-module-v1` (profile slurp) compiled
onto lock v2.2 (lock v2.1 plus the delivery normaliser v4g). The Reviewer loop is off: Perception then Solver, no
Planner or Reviewer visit, no tool schema on any role, program `phase-native-module-v1-c2`. COMP-1b's two components are on
(`agree-vote-seed` w_agree 1.0, recall k 60; `centroid-boundary-key`). The Solver uses the locked
`configs/probes/slurp_native_role_solver_v2.txt`. The replicate is the module OFF arm on lock v2.1 with the full graph
and v3 delivery. It is request-identical to the sealed A2 A/A except in two named leaves (package README section 3).

## 2. Definitions

The registered verdict words, quoted from `docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1/README.md` section 5:

- **NOMINATED** "iff the CI95 lower bound of (composed minus A2) on SLU-F1 is above |o| (beyond the replicate offset) AND the point estimate is at or above the 2.5 pp bar AND the intent guard shows no HARM".
- **NEUTRAL** "iff the CI95 lower bound of (composed minus A2) on SLU-F1 and on intent is at or above -2.5 pp (the preregistered harm margin) and the read is neither NOMINATED nor HARM: the composition keeps the full-graph accuracy within what a cross-flight read can see at about half the contacts -- still an efficiency result, never reported as a gain."
- **HARM** "iff the CI95 upper bound of (composed minus A2) on SLU-F1 or on intent is below -|o| (a resolved loss beyond the flight offset, owner decision 25)."
- **UNRESOLVED**: "A read whose lower bound is under -2.5 pp while neither HARM nor NOMINATED is UNRESOLVED (the design cannot rule out a margin loss) and is reported as such, not as NEUTRAL."

Measurement block (`registered-facts-v1.json`, `stage3_measurement`): design `cross-flight-with-in-chain-replicate`,
n = 1,000, primary official pooled SLU-F1 (`primary_metric_key: slu`), intent (scenario_action exact) the guard,
`admission: no-harm`, `claims_benefit: false`, `harm_margin_pp` 2.5 on both metrics, bar 2.5 pp, own null h_SLU 1.2525 /
h_intent 1.152. The declared `expected_effect_pp` is **+0.07**: the review-off N100 read -1.48 [-5.33, +2.72] plus the v4g
Fold B delivered gain +1.55 [+0.81, +2.33]. The declared claim is "no loss at about half the contacts plus the v4g
delivered gain". Tuning exception (declared): the v4 rule set that v4g extends was selected offline on the A2 pool of this
roster, so the v4g gain here is in-sample for the rule choice and descriptive only.

**The offset o.** The replicate is the instrument of the sealed A2 flight's base arm, flown in the R5 chain. Replicate
minus the sealed A2 A/A is the flight-to-flight offset on the same rows, including the two leaves in which they differ.
The registered claim (composed minus A2 arm) is read beyond |o|. Here o = +0.73 pp SLU-F1 and +0.20 pp intent.

## 3. The contrasts

All deltas are right minus left, in pp. CIs are CI95 from `v4g-contrast/report.json` (the source of the registered
decision arithmetic). Intent is scenario_action exact.

### 3a. Delivered columns (as sealed)

| contrast | role | left SLU % | right SLU % | SLU-F1 delta [CI95] | intent delta [CI95] | span-F1 delta |
| --- | --- | ---: | ---: | --- | --- | ---: |
| A2 reproduction: A2 A/A -> A2 arm | context (the A2 read on file) | 65.40 | 65.93 | +0.53 [-1.05, +2.09] | +4.60 [+2.59, +6.72] | +0.04 |
| **claim: A2 arm -> composed** | **registered claim** | 65.93 | 67.18 | **+1.24 [-0.29, +2.80]** | **+0.50 [-0.51, +1.52]** | +2.04 |
| offset: A2 A/A -> replicate | offset o | 65.40 | 66.13 | +0.73 [-0.53, +2.02] | +0.20 [-0.90, +1.31] | +0.03 |
| same chain: replicate -> composed | context | 66.13 | 67.18 | +1.05 [-0.77, +2.86] | **+4.90 [+2.93, +6.86]** | +2.05 |
| sealed base: A2 A/A -> composed | context | 65.40 | 67.18 | +1.77 [-0.09, +3.68] | +5.10 [+3.15, +7.09] | +2.08 |

### 3b. Under one normaliser (v4g applied offline to the sealed v3 columns; the composed column is already v4g)

| contrast | left SLU % | right SLU % | SLU-F1 delta [CI95] | intent delta [CI95] | span-F1 delta |
| --- | ---: | ---: | --- | --- | ---: |
| offline gain: A2 arm -> v4g(A2 arm) | 65.93 | 66.91 | +0.98 [+0.25, +1.71] | 0.00 [0.00, 0.00] | +2.01 |
| offline gain: replicate -> v4g(replicate) | 66.13 | 66.77 | +0.64 [-0.11, +1.35] | 0.00 [0.00, 0.00] | +1.73 |
| **claim: v4g(A2 arm) -> composed** | 66.91 | 67.18 | **+0.27 [-1.17, +1.72]** | +0.50 [-0.51, +1.52] | +0.02 |
| offset: v4g(A2 A/A) -> v4g(replicate) | 66.45 | 66.77 | +0.31 [-1.02, +1.66] | +0.20 [-0.90, +1.31] | -0.17 |
| same chain: v4g(replicate) -> composed | 66.77 | 67.18 | +0.41 [-1.34, +2.16] | +4.90 [+2.93, +6.86] | +0.32 |
| sealed base: v4g(A2 A/A) -> composed | 66.45 | 67.18 | +0.72 [-1.06, +2.53] | +5.10 [+3.15, +7.09] | +0.15 |

### 3c. The registered rule, applied (`report.json` `decision_rule_arithmetic`)

| rule set | SLU delta [CI95] | intent delta [CI95] | abs offset (SLU / intent) | NOMINATED? | HARM? | lower bounds >= -2.5? | word |
| --- | --- | --- | --- | --- | --- | --- | --- |
| delivered (registered) | +1.24 [-0.29, +2.80] | +0.50 [-0.51, +1.52] | 0.73 / 0.20 | no (LB -0.29 not above 0.73; point under 2.5) | no | yes | **NEUTRAL** |
| under v4g (context) | +0.27 [-1.17, +1.72] | +0.50 [-0.51, +1.52] | 0.31 / 0.20 | no | no | yes | NEUTRAL |

Read together: the delivered SLU gain over A2 (+1.24) is mostly the v4g delivery gain (+0.98 offline on the A2 arm).
After v4g is applied to both sides, the review-off change is +0.27 with a CI half-width of about 1.4 pp. Intent does not
move under v4g on any column, so the intent rows are the same in 3a and 3b.

## 4. Per-scenario and per-channel tables

### 4a. Per-scenario (from `v4g-contrast/report.json`)

The four stage-3 passes write `per-scenario-tables.json` with status **NOT_AVAILABLE** in both weightings. The roster sets
`stratum_withheld_per_item: true`, and the official per-sample rows carry no scenario field. Their aggregate roster
allocation is calendar 221, play 203, qa 157, email 96, weather 65, general 62, iot 57, lists 52, transport 48, news 20,
datetime 9, recommendation 6, social 4. The model-free v4g contrast script (`scripts/analysis/nx_r5_v4g_contrast.py`)
groups rows by the scored gold scenario at read time. It reports the tables below, which are the per-stratum tables this
read has. The equal-stratum weighting gives the 4-, 6- and 9-row strata the same weight as the 221-row one.

Weightings, delivered (SLU-F1 / intent, pp):

| contrast | natural mixture | equal stratum |
| --- | --- | --- |
| A2 reproduction: A2 A/A -> A2 arm | +0.53 / +4.60 | +1.55 / +1.29 |
| **claim: A2 arm -> composed** | **+1.24 / +0.50** | **-0.73 / -0.13** |
| offset: A2 A/A -> replicate | +0.73 / +0.20 | +0.30 / +0.87 |
| same chain: replicate -> composed | +1.05 / +4.90 | +0.53 / +0.29 |
| sealed base: A2 A/A -> composed | +1.77 / +5.10 | +0.82 / +1.16 |

Weightings, under v4g (SLU-F1 / intent, pp):

| contrast | natural mixture | equal stratum |
| --- | --- | --- |
| offline gain: A2 arm -> v4g(A2 arm) | +0.98 / 0.00 | +0.23 / 0.00 |
| offline gain: replicate -> v4g(replicate) | +0.64 / 0.00 | -0.09 / 0.00 |
| **claim: v4g(A2 arm) -> composed** | **+0.27 / +0.50** | **-0.96 / -0.13** |
| offset: v4g(A2 A/A) -> v4g(replicate) | +0.31 / +0.20 | +0.14 / +0.87 |
| same chain: v4g(replicate) -> composed | +0.41 / +4.90 | +0.61 / +0.29 |
| sealed base: v4g(A2 A/A) -> composed | +0.72 / +5.10 | +0.76 / +1.16 |

Per scenario, the claim contrast and the same-chain contrast (delta pp, SLU-F1 / intent; point estimates, no per-stratum CI):

| scenario | rows | claim delivered: A2 arm -> composed | claim under v4g: v4g(A2 arm) -> composed | same chain delivered: replicate -> composed | same chain under v4g |
| --- | ---: | --- | --- | --- | --- |
| calendar | 221 | -0.53 / +0.90 | -0.91 / +0.90 | +1.91 / +11.31 | +1.25 / +11.31 |
| play | 203 | +4.89 / +1.48 | +3.45 / +1.48 | +1.41 / +2.96 | +0.32 / +2.96 |
| qa | 157 | +2.29 / +0.64 | +1.32 / +0.64 | +1.80 / +5.73 | +1.32 / +5.73 |
| email | 96 | -4.25 / -1.04 | -3.63 / -1.04 | -0.89 / +6.25 | +1.01 / +6.25 |
| weather | 65 | +3.84 / +1.54 | +1.84 / +1.54 | -0.36 / +3.08 | -1.23 / +3.08 |
| general | 62 | -0.30 / +1.61 | -4.06 / +1.61 | -0.34 / +9.68 | -4.51 / +9.68 |
| iot | 57 | -1.84 / -1.75 | 0.00 / -1.75 | +0.62 / -5.26 | +1.82 / -5.26 |
| lists | 52 | -1.12 / 0.00 | -2.63 / 0.00 | -4.17 / 0.00 | -5.18 / 0.00 |
| transport | 48 | +1.74 / 0.00 | +0.59 / 0.00 | -3.30 / 0.00 | -3.30 / 0.00 |
| news | 20 | -8.65 / -5.00 | -8.50 / -5.00 | -8.65 / -5.00 | -6.34 / -5.00 |
| datetime | 9 | -5.58 / 0.00 | 0.00 / 0.00 | -4.01 / 0.00 | 0.00 / 0.00 |
| recommendation | 6 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| social | 4 | 0.00 / 0.00 | 0.00 / 0.00 | +22.83 / -25.00 | +22.83 / -25.00 |

The claim contrast's natural-mixture SLU gain sits in play, qa, weather and transport. Email, news, iot and lists go
the other way. The equal-stratum mean is pulled below zero by email, news and datetime (96, 20 and 9 rows). The
same-chain intent gain is concentrated in calendar (+11.31 on 221 rows), general, email and qa. The per-scenario rows of
the offset, the sealed-base and the A2-reproduction contrasts are in `report.json`.

### 4b. Per-row metrics and per-channel (stage-3 passes; their own bootstrap)

Per-row exact-match metrics with saves / harms / ties and McNemar p (`score-contrasts.json`, rendered in each pass's
README). CI95 here is the stage-3 driver's per-row bootstrap.

| pass | metric | delta pp [CI95] | saves / harms | McNemar p |
| --- | --- | --- | --- | ---: |
| vs-comparator (A2 arm -> composed) | intent (scenario_action exact) | +0.50 [-0.51, +1.57] | 17 / 12 | 0.458 |
| | action exact | +0.70 [-0.30, +1.79] | 18 / 11 | 0.265 |
| | scenario exact | +0.30 [-0.51, +1.19] | 11 / 8 | 0.648 |
| | slot F1 (per-row mean) | -0.95 [-2.30, +0.39] | 52 / 53 | 1.000 |
| | SLU-F1 (per-row mean) | -2.11 [-3.42, -0.88] | 67 / 84 | 0.193 |
| vs-aa (replicate -> composed) | intent | +4.90 [+2.98, +6.90] | 75 / 26 | 1e-6 |
| | slot F1 (per-row mean) | -0.58 [-2.30, +1.08] | 75 / 76 | 1.000 |
| | SLU-F1 (per-row mean) | -1.75 [-3.34, -0.17] | 97 / 111 | 0.367 |
| offset (A2 A/A -> replicate) | intent | +0.20 [-0.90, +1.30] | 16 / 14 | 0.856 |
| | SLU-F1 (per-row mean) | +0.36 [-0.71, +1.42] | 55 / 51 | 0.771 |
| composed-vs-a2aa (A2 A/A -> composed) | intent | +5.10 [+3.18, +7.06] | 77 / 26 | <1e-6 |
| | SLU-F1 (per-row mean) | -1.39 [-3.01, +0.23] | 96 / 104 | 0.621 |

The per-row mean SLU-F1 moves opposite to the pooled micro SLU-F1 on the claim contrast. Per row it is -2.11 with a
CI95 upper bound below 0 (84 harms vs 67 saves). Pooled it is +1.24 (CI crosses 0), and pooled span-F1 is +2.04 [+0.18, +3.91]
in the pass's own bootstrap. The registered primary is the pooled official SLU-F1. The per-row mean is reported beside
it and gates nothing. This note does not attribute the divergence.

Per channel (headset n = 460, far-field n = 540), delta pp (saves / harms):

| pass | metric | headset | far-field |
| --- | --- | --- | --- |
| vs-comparator (A2 arm -> composed) | intent | +0.65 (8 / 5) | +0.37 (9 / 7) |
| | slot F1 (per-row) | -0.99 (25 / 25) | -0.91 (27 / 28) |
| | SLU-F1 (per-row) | -1.95 (28 / 34) | -2.25 (39 / 50) |
| vs-aa (replicate -> composed) | intent | +3.70 (28 / 11) | +5.93 (47 / 15) |
| | slot F1 (per-row) | -2.47 (30 / 38) | +1.03 (45 / 38) |
| | SLU-F1 (per-row) | -3.27 (35 / 53) | -0.45 (62 / 58) |
| offset (A2 A/A -> replicate) | intent | +0.22 (5 / 4) | +0.19 (11 / 10) |
| | SLU-F1 (per-row) | +1.12 (23 / 18) | -0.28 (32 / 33) |
| composed-vs-a2aa (A2 A/A -> composed) | intent | +3.91 (30 / 12) | +6.11 (47 / 14) |
| | SLU-F1 (per-row) | -2.16 (38 / 50) | -0.73 (58 / 54) |

The same-chain intent gain is larger on far-field rows (+5.93) than on headset rows (+3.70).

### 4c. Delivery and conversion (gold intent boundary among the flown Perception items)

| pass | delivered left / right | newly delivered | newly lost | converted (newly delivered, left wrong, right right) |
| --- | --- | ---: | ---: | ---: |
| vs-comparator | 956 / 956 | 0 | 0 | 0 |
| vs-aa | 815 / 956 | 150 | 9 | 38 of 114 |
| offset | 815 / 815 | 0 | 0 | 0 |

Delivery is identical between the A2 arm and the composed arm (956 / 956, no row changes delivery). The review-off and
v4g change therefore acts only through the graph and the delivery normaliser, not through supply. On the rows delivered
in both, the composed arm turns 16 A2-arm intent errors right and 12 rights wrong.

## 5. Efficiency and cost

From `efficiency.json` (vs-comparator and vs-aa) and the ledger countersign text:

| field | A2 arm (sealed) | replicate (R5 chain) | composed (R5 chain) | composed - A2 arm | composed - replicate |
| --- | ---: | ---: | ---: | ---: | ---: |
| rows | 1,000 | 1,000 | 1,000 | 0 | 0 |
| contacts | 4,050 | 4,111 | 2,000 | -2,050 | -2,111 |
| contacts per row | 4.050 | 4.111 | 2.000 | -2.050 | -2.111 |
| prompt tokens per row | 37,345.7 | 36,273.0 | 14,658.8 | -22,686.9 | -21,614.2 |
| completion tokens per row | 241.7 | 213.0 | 137.7 | -103.9 | -75.3 |
| GPU-h (= per 1,000 rows) | 1.6955 | 1.6548 | 1.3800 | -0.3155 | -0.2748 |
| GPU-active seconds | 6,103.7 | 5,957.2 | 4,968.1 | -1,135.7 | -989.1 |
| generation wall seconds | 6,220.5 | 6,123.6 | 5,130.8 | -1,089.7 | -992.8 |
| mean GPU utilisation % | 86.4 | 74.1 | 75.8 | -10.6 | +1.7 |
| contacts per minute | 39.1 | 40.3 | 23.4 | -15.7 | -16.9 |
| repeated speech seconds | 12,056.9 | 12,290.0 | 5,967.1 | -6,089.8 | -6,322.9 |
| tool calls | 0 | 0 | 0 | 0 | 0 |

- Composed structure (`structural.json`): 2 role visits on all 1,000 rows, no Planner action, 0 revisions, 1,000
  admitted. The v4g delivery normaliser applied on 999 rows and changed the delivered value on 201 (replicate, v3: 996 /
  125).
- Replicate structure: role visits 4 on 963 rows and 7 on 37; 37 revisions executed. The ledger records dispositions
  `planner_action_illegal` 1 and `revision_limit` 5. Its about 106 min end to end and the composed arm's about 84 min are
  the ledger's figures. The table's generation wall is the efficiency file's.
- Frontier rows (per 1,080 rows): GPU-h 1.8311 (A2 arm) vs 1.4904 (composed). Prefilled tokens per row 9,574.2 vs
  9,092.6. Prompt tokens per row fall by 61 % but prefilled tokens per row only by 5 %; GPU-h falls by 18.6 %, not by half.
- Budget use: the composed arm used exactly its 2,000-contact cap and its 5,968 repeated-audio-second cap (5,967.05 s).
  The registered planned GPU-h was 1.5 against a measured 1.38.

## 6. What the verdict means and does not

- It means the review-off composition on lock v2.2 is not distinguishable from the full COMP-1b graph within a
  cross-flight read at n = 1,000 (SLU-F1 and intent lower bounds above -2.5 pp, no resolved loss beyond the offset). It
  costs 2.00 contacts per row instead of 4.05. The delivered SLU-F1 level (67.18) is the highest of the four columns
  compared here. The coordinator's record states it is the highest delivered level on this roster so far; this note
  did not re-derive that.
- It does not mean a gain. The SLU delta over A2 does not clear the offset or the bar. Under one normaliser it is +0.27
  [-1.17, +1.72], and v4g itself was selected on this roster's A2 pool (the declared tuning exception). The equal-stratum
  claim delta is negative (-0.73 SLU), and the per-row mean SLU-F1 moves against the pooled number.
- The same-chain intent +4.90 [+2.93, +6.86] is a third replication of the COMP-1b intent gain on the same arm-family
  bytes. The composed side also differs from the replicate in review-off and v4g. v4g leaves intent unchanged on every
  column. The review-off change on its own reads +0.50 [-0.51, +1.52] intent.
- Status: DESCRIPTIVE, DEV roster, owner decision 28. No admission entry and no module-class harness entry (package
  README section 8 item 2). No test, generalisation, carrier or paper-scale claim.
- Next step on file (owner decision 241, "As you suggest"): the second test-sample allowance is drafted once R5 reads
  NOMINATED or NEUTRAL.

## 7. Pointers

Analysis root: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-PAIRED-ANALYSIS-V1/`.

| file | sha256 |
| --- | --- |
| `v4g-contrast/report.json` (schema `saea-nx-r5-v4g-contrast-v1`) | `b3205b338af97858fb3d47ad09a426e084d31ba69c16e564dfea52e125be6f9d` (measured; no tables.md beside it) |
| `vs-comparator/verdict.json` (status DESCRIPTIVE) | `29da2681c1a49cd475788be928b94b0eeb807695ebd7cf9016192b09d632ab86` (measured) |
| `vs-comparator/README.md` | `40d392452cf220a5ceea4ea30d2bd17ef8ab70cef2d23dc32f7f1331e5833799` |
| `vs-comparator/score-contrasts.json` | `9f455ebe1dd8fa9cc69655dd970ad58922725afe41579ee5c6535dea6214c713` |
| `vs-comparator/per-scenario-tables.json` | `0344ad5ecdbaf6ba8a230ed39350341f4582c1c73b1ab9d4cb246b33766c7f82` |
| `vs-comparator/efficiency.json` | `ff6cf0cc0dc84de22b42948ddaf79b8730bca83b3e6926eb3b0adf2a66cfea1c` |
| `vs-comparator/frontier.json` | `a5f9ae72d76fede8ce024640b76080d4defc5f284aeaa905698ffe2c7e19d32e` |
| `vs-comparator/delivery-conversion.json` | `e7a68a733d3181c031e16595c7e374126e03f7befcce42a27fa108cc081ce362` |
| `vs-comparator/structural.json` | `5026c7d392a1e86e8fb2c802513af2039cfabc79b393860c99e913aa21121235` |
| `vs-comparator/stop.json` (PASSED) | `360964efbda11a296385f1f4e276ac99215630cecbbb43fc10dc8b0e8b22484b` |
| `vs-aa/verdict.json` | `05edf29aea1b4f2bbdd8bc81388db9ab7ffba8683917e6bb18bf343cb92e12dd` (measured) |
| `vs-aa/README.md` | `7cdb6b87d664b2881ecf4c7560605de5607aa26614374844a7a853f21a8362df` |
| `vs-aa/score-contrasts.json` | `9fb39e491c524e2e084c199b0ed99a06d0d9ae6db3e1c3cd081eda991144b096` |
| `vs-aa/per-scenario-tables.json` | `af04e7d1ea702eee0d271778be4248a3f4f46eb9263678c07eefdb672eb02dab` |
| `vs-aa/efficiency.json` | `7c0bb90ecc3664c999379849cb0cb067ec704bd69d773b78c4944cb6d9ae86cb` |
| `vs-aa/frontier.json` | `0bfefdb4f09f3376886e2edb82a890f03d5d5d2344d205739869d247b22a3d60` |
| `vs-aa/delivery-conversion.json` | `18c34324ed6264e6ddd166a0fb309a1e76fad00c41939fd81ad6ee3730d0b80e` |
| `vs-aa/structural.json` | `6595fc5dd4ad3d294500d06d21adcc47cc4d3802d54c9bd56e7805da3aed4a4d` |
| `vs-aa/stop.json` | `558404e5d0c535cb9854a01f9bef92db318198ad6896008b8390c29534bebe63` |
| `offset-replicate-vs-a2aa/verdict.json` | `e2c91229292d178e9f3bb5ec16357aeedc99b3fcf59d77ca4c128d3456847168` (measured) |
| `offset-replicate-vs-a2aa/README.md` | `4d0ed88b76997edc1bd56947564149d9e5c8996c8fcb9ee9d0fca526f948425f` |
| `offset-replicate-vs-a2aa/score-contrasts.json` | `68d2a79603a3490e974b7e3b515bd6bc84ab4eb12d55f29fe42dbad2f060d39a` |
| `offset-replicate-vs-a2aa/per-scenario-tables.json` | `d8b0fb4434ed084cabae9f235ea00312615adb40d62dcf99d63b5bdef2704c94` |
| `offset-replicate-vs-a2aa/efficiency.json` | `49dab25fbce50fd814e3242c0e274a9b34191c69bbe1d91bb9e50b2afe05302e` |
| `offset-replicate-vs-a2aa/frontier.json` | `2e502eb37d8170324d7950ef98d7b28d4bfce7a7c02bb38f929a3350e2c22cda` |
| `offset-replicate-vs-a2aa/delivery-conversion.json` | `f7701a327313c812bda940b10d96f76842d3ea421e4de53765ef55be8e01ff8c` |
| `offset-replicate-vs-a2aa/structural.json` | `58e3e9c5564fe0d6401bea4ea3037e00ec4ee9afa9f2f7baf3d5a96572736871` |
| `offset-replicate-vs-a2aa/stop.json` | `e55160d40da9b4480aeb0247b66f92008f9d0c09ad23c52f4dc3ee2e4d9b6ad7` |
| `composed-vs-a2aa/verdict.json` | `e0e728748265ef9a3e3cf945b8718314d008ded5040ca7858a6d0ac57e28c236` (measured) |
| `composed-vs-a2aa/README.md` | `c3d3652d5b8c8d7c0ee82c2fc0ae60bcff2949b4e0780532b0fb04f83370e42b` |
| `composed-vs-a2aa/score-contrasts.json` | `3b444277aadbde3a0dfc58695290be2be67e4f96e08a47888325bf43f17eccf7` |
| `composed-vs-a2aa/per-scenario-tables.json` | `bdb675663e1126bf57f0325472416f05b71d831f944bfdb486e1f296f81803ea` |
| `composed-vs-a2aa/efficiency.json` | `2dc44d4075e19bce057b91db59c3b6e370aca9f6cf5c98337ace33f4c3171046` |
| `composed-vs-a2aa/frontier.json` | `0955c30e3c81049dd0c658524bc0aad533b00e29416334184bd0a8c83a676f34` |
| `composed-vs-a2aa/delivery-conversion.json` | `f49020e151f5b4a4f0cfcb599846977747c93fc066775cb997da84235e8670bf` |
| `composed-vs-a2aa/structural.json` | `0fb8cbf217a4fde1bc2409cd11daf00ea5cc2aabfb5e45cb67919d8b5d269fa7` |
| `composed-vs-a2aa/stop.json` | `e65fad9c50bca8c2b6d412d088cd3dd79e71c526816c7f96087866b6a70b5680` |
| pass drivers (copied beside each pass) | `slurp_paired_roster_read.py` `5c95a2e3627573bda69c10dff1158c0e1c5172b2da8d4fbdcc86ec87ff3161bc`; `stage3_paired_read.py` `da9485fca9b52ccad58caf388dda183e947636d1febba5514a452669be83b40d` |

Repository files (sha256 measured at this note's base `e13e25909`):

| file | sha256 |
| --- | --- |
| `docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1/README.md` | `81f92171530e064a2f63e54f25f860e9d36e3b7c387da07be00d0125414943c6` |
| `docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1/registered-facts-v1.json` | `74aaac803933db4024a64a4a93c7acd07768a1baa9ba3b910ec37ad3e3370801` |
| `docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1/analysis-recipe-v1.json` | `f54b5a0d16701f6cc2b189b57087602fea9d1dcdb1fec5b3b7dab940b6ab5758` |
| `docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1/generation-plan-registered-v1.json` | `b5bac81ba1a3904d694aa4e39c3786d48ff12aa7451654c05916f36eda52f287` |
| `docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1/protocol-registered-v1.json` | `d89cba087e39ed2616854f207c3d9cd908b46d9038a308b1eaea98de0bb6b936` |
| `scripts/flights/nx/nx_r5_read.sh` | `6ad1ecb83ab4c6683ebc654b753f56f3b6c68c60c36173e4a32585dfac01dc83` |
| `scripts/analysis/nx_r5_v4g_contrast.py` | `d08ae8e98c8bae4321f49821b9f9308a41ee71de3a9946c4668a08b6c23ef609` |

Related results: `docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md` (A2: COMP-1b vs its A/A, intent +4.60
[+2.58, +6.73], SLU +0.53 [-1.04, +2.09]; its CIs are from the A2 recipe's seed 20260929, so they differ slightly from
the A2-reproduction row of section 3a); `docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md` (v4g lock, Fold B
+1.55 [+0.81, +2.33]; A2 pool +0.98 [+0.25, +1.71], reproduced here); `docs/results/2026-10-09-slurp-intent-lock-comp1b-v1.md`
(intent lock at COMP-1b, decision 229); `docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md` (floors:
cross-flight A/A at n = 1,000, SLU 1.2525 / intent 1.152); `docs/exposure-ledger.md` READ row
`SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-PAIRED-ANALYSIS-V1` (seal facts).

CI sources. Section 3 and section 0 quote `report.json`. The stage-3 passes bootstrap the pooled SLU-F1 separately
(same seed, different implementation), and their CIs differ in the second decimal: claim SLU [-0.26, +2.77], offset
[-0.55, +1.99], same chain [-0.79, +2.88], sealed base [-0.12, +3.67]. No word changes under either set.
