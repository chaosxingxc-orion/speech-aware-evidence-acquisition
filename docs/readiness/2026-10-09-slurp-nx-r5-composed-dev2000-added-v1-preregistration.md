# NX Stage J round R5 (the composed read on DEV-2000-ADDED): preregistration

Registered 2026-10-09 at study commit `4434a89b71cc9ff6de4ac502b8aa6a6d521f5893`, before any contact (programme `docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md` C2 R5;
decision 238 PROPOSED; module step 7). Development numbers only (owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| composition | The evidence-consumption module saea-evidence-consumption-module-v1 (profile slurp) compiled onto lock v2.2 (module step 7: lock v2.1 with the delivery normaliser saea-deliver-normalise-v4g, version 1) with the Reviewer loop OFF (review_loop off: Perception then Solver, Planner and Reviewer iterations 0, max_revisions 0, no tool schema on any role; the compiled program phase-native-module-v1-c2, ceiling 2) and COMP-1b's two components ON -- agree-vote-seed (w_agree 1.0, recall k 60, THIS roster's vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) and centroid-boundary-key (SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) -- every other catalogued component OFF (no citation contract, no scope-rule stage, no re-listen, no Perception column, no template column). The Solver instruction template is the locked configs/probes/slurp_native_role_solver_v2.txt (sha256 18bff5c5...). Every policy block is the module compiler's output; the roster pins are DEV-2000-ADDED's own. |
| roster | DEV-2000-ADDED (SLURP-DEV-2000-ADDED-V1), 1,000 rows, split role dev, scorer slurp-slu-official |
| in-chain replicate | `SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1` (the module OFF arm, lock v2.1 + v3), flown in the same campaign before the composed arm; registered in `docs/readiness/2026-09-30-slurp-stage3-module-comp1b-dev2000-added-v1` |
| comparator | the sealed A2 arm `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1`; offset instrument: the sealed A2 A/A `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1` |
| margins | harm margin 2.5 pp; bar 2.5 pp; this roster's own null: h_intent 1.152, h_SLU 1.2525 |
| smoke | four rows, structural acceptance, never scored |
| runs | `SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1` / `SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-FIT-V1`; `SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-SMOKE-4-FIT-V1` |
| composed config hashes | arm `aa359613f3c0fb2be8f4bcef2cf3b2adb3a2ec54eee754830611394401f9c346`; smoke `9b7d0b4ac4679369e3dbcd07065d44e16675d4e064ed156a278cd7a58bfef2c0`; replicate `d01a0fd68e83a491bfed1b2ea23e95ccb3f3ba957d9caf95e0f199dd5e350204` (post-flip value; registration-time snapshot `4772f6811c7b…`)` |
| protocol hashes | arm `5cbdb9f2ce8709943d58eba74fbe78134850db1ef678867f544f77e2c023bd63`; smoke `d091b56a7f0025ffd24737f3214500e8b7021f14ecc0d347910e0fc0c516ab10`; replicate `fb8f7249f5fa95ecaee1fe9233eec163bcf90574933e1e17596b62f99338e54c` (post-flip; registration-time `85ead97641fb…`)` |
| status | HELD. Decision 238 (close Stage S at the Solver node, compose Stage J = R5) is PROPOSED, not ruled, and the R1 iteration-2 verdict (does the Solver template enter the composition?) is pending. This package registers the composition decision A names WITHOUT a new Solver template; if the iteration-2 pick is delivered it is a swap (see the README), not a new cell. |

## Decision rule (fixed here)

Read in ONE chain: the replicate then the composed arm (campaign plan configs/campaign/slurp-native-stage3-nx-r5-composed-dev2000-added-v1.json). PRIMARY: official pooled SLU-F1 (slurp-slu-official), paired per utterance cluster (10,000 draws, seed 20260915), composed minus the sealed A2 arm (SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1). GUARD: intent (scenario_action exact), same contrast. OFFSET o: replicate minus the sealed A2 in-chain A/A (SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1), same metrics. THE BAR: 2.5 pp at n = 1,000 (instrument rule 3). NOMINATED iff the CI95 lower bound of (composed minus A2) on SLU-F1 is above |o| (beyond the replicate offset) AND the point estimate is at or above the 2.5 pp bar AND the intent guard shows no HARM; this is NOT expected (declared effect +0.07 pp) and would be a surprise to replicate before any use. NEUTRAL iff the CI95 lower bound of (composed minus A2) on SLU-F1 and on intent is at or above -2.5 pp (the preregistered harm margin) and the read is neither NOMINATED nor HARM: the composition keeps the full-graph accuracy within what a cross-flight read can see at about half the contacts -- still an efficiency result, never reported as a gain. HARM iff the CI95 upper bound of (composed minus A2) on SLU-F1 or on intent is below -|o| (a resolved loss beyond the flight offset, owner decision 25). A read whose lower bound is under -2.5 pp while neither HARM nor NOMINATED is UNRESOLVED (the design cannot rule out a margin loss) and is reported as such, not as NEUTRAL. Reported beside, CONTEXT ONLY and never the bar: composed minus the in-chain replicate (the whole composition against its same-chain base, intent and SLU-F1, with no offset correction needed); composed minus the sealed A2 in-chain A/A; the same contrasts with the v4g normaliser applied offline to the A2 and replicate columns so all columns are compared under v4g (isolating graph and supply from the normaliser); per-scenario tables in natural-mixture and equal-stratum weightings; the cost table. The verdict word is the coordinator's (owner decision 139).

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM only: the lock-v2.2 review-off program loads, no Reviewer or Planner is visited, the delivery node renders v4g, every request fits and the episode completes. Scored by no one, read by no one (instrument rule 5).",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-DEV-2000-ADDED-V1",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1": {
      "admission": "no-harm",
      "bar_pp": 2.5,
      "claim": "no-harm",
      "claims_benefit": false,
      "comparator_attempt_id": "attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1",
      "comparator_run_id": "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1",
      "expected_effect_basis": {
        "primary": "official pooled SLU-F1 (slurp-slu-official, DEV sibling), composed minus the sealed A2 arm",
        "reading": "+0.07 pp is the sum of an unresolved loss and a confirmed gain and sits far under the 2.5 pp rule-3 bar a cross-flight read at n = 1,000 can resolve; the cell therefore claims NO benefit. Its claim is NO LOSS at about half the contacts (2.0 per row against 4.05 for the sealed A2 arm) plus the v4g delivered gain.",
        "review_off_vs_full_graph_pp": -1.48,
        "review_off_vs_full_graph_source": "docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md section F2: the N100 read, review-off minus full graph -1.48 [-5.33, +2.72] (unresolved; n = 100); a descriptive number, not a prior (owner decision 139), and the only measured one",
        "sum_pp": 0.07,
        "v4g_delivery_gain_pp": 1.55,
        "v4g_delivery_gain_source": "docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md section 2 step 5: v4g(lock) minus lock on the TRAIN Fold B R1 delivering column +1.55 [+0.81, +2.33] (offline; the A2 DEV pool read is +0.98 [+0.21, +1.74] and is the roster the rules were selected on, so descriptive only). In the delivered cross-flight contrast it accrues to the composed side only."
      },
      "expected_effect_pp": 0.07,
      "harm_margin_pp": 2.5,
      "harm_margin_pp_by_metric": {
        "intent_accuracy": 2.5,
        "slu_f1": 2.5
      },
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "NX Stage J round R5: the composed system -- COMP-1b on lock v2.2 (v4g at delivery), Reviewer loop off, locked Solver template -- read cross-flight against the sealed A2 arm (COMP-1b, full graph, lock v2.0 + v3) with the module OFF-arm replicate flown in the SAME chain (instrument rule 3). Primary: official pooled SLU-F1; intent the guard (owner decision 133 scopes intent-primary to intent-acting mechanisms; this round's mechanism acts on delivery and the graph, so SLU-F1 is primary). The claim is NO LOSS at about half the contacts plus the v4g delivered gain; expected_effect_pp +0.07 is declared from measured numbers (expected_effect_basis) and is far under the 2.5 pp bar, so claims_benefit is false and the cell is admitted on a no-harm reading (harm_margin_pp 2.5, not tighter than the cross-flight sampling floor 1.2525 at n = 1,000). The replicate is the module OFF arm: it is request-identical to the sealed A2 in-chain A/A except the lock-v2.1 Reviewer template and the recall k (a proven supply no-op), so replicate-minus-A2-A/A is the flight-to-flight OFFSET the composed-minus-A2 contrast is read beyond. The v4 rule selection on this very roster is declared in tuning_exception.",
      "offset_pair": {
        "left_attempt_id": "attempt-slurp-native-stage3-comp1-aa-dev2000-added-generation-v1",
        "left_run_id": "SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1",
        "right_attempt_id": "attempt-slurp-native-stage3-module-comp1b-aa-dev2000-added-generation-v1",
        "right_run_id": "SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1"
      },
      "own_null": {
        "h_intent": 1.152,
        "h_slu": 1.2525,
        "n": 1000
      },
      "primary_metric": "official pooled SLU-F1 (slurp-slu-official, DEV sibling), composed minus the sealed A2 arm beyond the replicate offset; intent accuracy (scenario_action exact) the non-inferiority guard",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-DEV-2000-ADDED-V1",
      "replicate_run_id": "SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1",
      "roster": "DEV-2000-ADDED (SLURP-DEV-2000-ADDED-V1, split identity ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67)",
      "rows": 1000,
      "tuning_exception": "the v4 rule set (fx-article, fx-oclock, scope, ti1, ee10) that saea-deliver-normalise-v4g extends was SELECTED offline on the A2 DEV pool (431 combinations + 10 single rules on DEV-2000-ADDED, COMP-1b delivered column; docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md), which is this cell's read roster; it was confirmed on TRAIN Fold A, its guards were located on Fold A and checked on A2, and the lock was confirmed on TRAIN Fold B (docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md). The v4g delivered gain on this roster is therefore in-sample for the rule choice and descriptive only; the declared expectation quotes the Fold B confirmation.",
      "tuning_roster": [
        "slurp-train-construction-pool-agree-kprobe-r01-excluded",
        "SLURP-EVO-FOLD-A-V2"
      ]
    }
  }
}
```

## Where the declared +0.07 pp comes from

Review-off minus full graph -1.48 pp [-5.33, +2.72] (N100 read, unresolved, descriptive) plus the v4g delivered gain
+1.55 pp [+0.81, +2.33] (TRAIN Fold B lock column, offline; docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md). Neither is a prior (owner
decision 139) and their sum is under the 2.5 pp bar, so no benefit is claimed.

## Prohibitions

- No flight before decision 238 is ruled and the coordinator decides it flies, root countersigns the rows of BOTH packages, mints BOTH receipts, and the three cells are flipped in one converged cycle.
- No re-flying of any sealed cell; no test, DEV-1000, Fold A or Fold B contact.
- No component beyond the declared block; no k, tau, fuse_coverage, w_prior, store, release, snapshot, roster, template or geometry change outside the compiler.
- No scope-rule stage and no solver-citation-contract on this block (refused on lock v2.2); no template column.
- No paper-scale profile. --allow-output-change is never passed.
