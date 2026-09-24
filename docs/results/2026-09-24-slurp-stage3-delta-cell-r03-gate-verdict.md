# Cell CELL-3 verdict: the coverage-gated stage3-deltas-v2 store on the fresh roster DEV-2000-ADDED (Stage-3 S3-6 iteration 3; provisional decision 110, ratified; owner decisions 83, 99, 101, 106, 107)

Read 2026-09-24 by the coordinator (Fable 5.1). Driver: `scripts/analysis/slurp_paired_roster_read.py`
via `scripts/flights/batch/cell3_read.sh own-null | arm | twin` (the B6 precedent; the driver writes
status DESCRIPTIVE and the registered rule of `docs/readiness/2026-09-24-slurp-stage3-delta-cell-r03-gate-v1/protocol-registered-v1.json`
is applied here). Analysis roots under `$SPEECHRL_DATA_DIR/analysis/`:
`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-OWN-NULL-V1` (score-contrasts `1cba957e...`),
`SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-PAIRED-ANALYSIS-V1`, `SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-TWIN-PAIRED-ANALYSIS-V1`.
Model-free: zero model / tokenizer / encoder / server contacts; scorer contacts only through the sealed
per-sample official (devel) scores. No utterance text, gold or model output is printed.

## 1. Verdict

| item | result |
| --- | --- |
| status | **HARMFUL on the SLU guard by the registered rule (decision 25 Method B: CI95 upper bound below zero); intent NEUTRAL.** The twin is NEUTRAL, so the loss is attributed to the store's CONTENT on this roster, not to the form of carrying a supply. |
| factor | the locked v2.0 plan plus the stage3-deltas-v2 store applied through the row-level scenario gate (`majority-candidate-scenario-not-in-v1` over general / alarm / music / social / iot / play / news on Solver / Reviewer / Planner; Perception unconditional route dropped); 355 of 1,000 rows gate-closed, 568 supplied, 120 of 200 values reached |
| comparator | the sealed B6 PLAN arm on DEV-2000-ADDED (`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1`, official SLU-F1 65.40 / intent 76.60) |
| own null (sealed before the arm's contrast) | PLAN vs PLANr-DEV2000 (`...-REPLICATE-V1`, flown 12:44-14:36 UTC, 4,090 contacts, 1.649 GPU-h): SLU -0.25 [-1.52, +0.98], intent +0.20 [-0.99, +1.31]; **h_SLU 1.2525 / h_intent 1.1520** |
| flown | 2026-09-24 12:44-18:32 UTC, SAEA-Batch-Chain-CELL3 (PLANr 12:44-14:36; smoke 14:36-14:37, arm 14:37-16:33; twin smoke 16:34-16:35, twin 16:35-18:31), flight commit `a9b48dfc`, session `serving-slurp-native-candidate-five-train-a-np4-v1` |

## 2. Headline contrasts (CELL-3 minus PLAN; paired, utterance-clustered bootstrap, 913 clusters, 10,000 draws, seed 20260915)

| metric | PLAN | arm | delta pp | CI95 | margin | guard |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| official pooled SLU-F1 | 65.40 | 63.95 | **-1.44** | [-2.88, -0.05] | 1.2525 | FAILS: measured loss |
| span-F1 micro | 57.05 | 54.91 | -2.14 | [-3.92, -0.41] | -- | diagnostic |
| intent (scenario_action exact) | 76.60 | 76.60 | 0.00 | [-1.01, +1.00] | 1.1520 | non-inferior |
| per-row SLU-F1 mean | 47.35 | 46.99 | -0.36 | [-1.47, +0.78] | -- | saves 57 / harms 69 |

## 3. The derangement twin (form control) and the attribution

| metric | PLAN | twin | delta pp | CI95 |
| --- | ---: | ---: | ---: | --- |
| official pooled SLU-F1 | 65.40 | 65.78 | +0.38 | [-0.97, +1.75] |
| span-F1 micro | 57.05 | 57.50 | +0.46 | [-1.15, +2.01] |
| intent | 76.60 | 76.60 | 0.00 | [-1.21, +1.20] |
| per-row SLU-F1 mean | 47.35 | 47.98 | +0.63 | [-0.49, +1.78] |

Arm minus twin: **-1.82 pp SLU**, 0.00 intent (descriptive). The same gate and the same 200 values
re-attached by a within-node derangement leave the plan unharmed; the values on their intended
targets harm it. On this roster the store's content is the loss; carrying a supply is not.

## 4. Where the loss sits (`docs/results/2026-09-24-slurp-cell3-fresh-roster-loss-diagnostic.md`)

| pair | split | n | pooled SLU delta pp | CI95 |
| --- | --- | ---: | ---: | --- |
| PLAN -> CELL-3 | gated (byte-identical prompts) | 355 | -2.20 | [-4.38, -0.03] |
| PLAN -> CELL-3 | supplied | 568 | -1.61 | [-3.46, +0.28] |
| PLAN -> PLANr | gated | 355 | +0.61 | [-1.45, +2.69] |
| PLAN -> PLANr | supplied | 568 | -1.26 | [-2.79, +0.25] |

Run-to-run noise on 355-row splits is about +-2 pp; the store's attributable part on supplied rows
is -0.35 pp above its own null, an entity-precision cost (`date` +29 FP behind date-bearing
slot-contract / reviewer-criterion deltas); harm is diffuse over 120 values (top 20 = 45.6 % of
harm mass); Fold A winners do not transfer (sign agreement 49/96); a perfect gate reaches only
64.89 (-0.51 [-1.40, +0.37]). The gate itself is stable (replay 1000/1000; 2.2 % flips under PLAN's
own candidates). Per channel: far-field per-row SLU -0.47, headset -0.24.

## 5. Per scenario

No gold per-scenario labels exist on DEV-2000-ADDED (`stratum_withheld_per_item: true`); the
predicted-majority-scenario split and the gate-closed / gate-open split above stand in for the
per-scenario table, stated as such (registered in the preregistration, section 9b).

## 6. Cost

| number | arm | twin | comparator |
| --- | ---: | ---: | ---: |
| contacts per row | 4.178 | 4.084 | 4.071 |
| GPU-h per 1,000 rows | 1.742 | (see efficiency.json) | 1.655 |
| prompt tokens per row | 37,686 | -- | 35,913 |

## 7. Caveats

- A development number (decisions 28 / 86 / 107); the first out-of-fold read of the Stage-3 delta line.
- Two changes ride together as one application policy (the gate and the dropped Perception route: 80 of
  the 200 values are unreachable by construction); the verdict credits the policy, never the gate alone.
- The gated set was chosen on TRAIN Fold A; this read is decision 99's fresh-roster replicate venue.

## 8. Records

Ten flight rows and the two paired-analysis rows of this family are closed in `docs/exposure-ledger.md`
(the own-null row was closed at 14:50 UTC); a results-ledger entry and the decision-110 / 111 outcome
lines are appended. Owner decision 111 (2026-09-24) closes the semantic-delta application line; the
next route is inference-time aggregation and construction-variant rollouts (decision 112; handoff
`docs/handoff/2026-09-24-fable51/HANDOFF-STAGE3-FOR-CHATGPT-v1.md`, section 7).
