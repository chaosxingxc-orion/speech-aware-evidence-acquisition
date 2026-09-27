# Cell REV-TFRL-1: preregistration

Registered 2026-09-27 at study commit `97eb3288`, before any contact, from the committed AGREE
arm fragments by script (decision 58) with one pin moved, under owner decision 165. Development numbers only (owner
decisions 28 and 86); never a test claim. The design, the credit table and the offline selection are in
[`2026-09-27-slurp-stage3-reviewer-tfrl-v1/README.md`](2026-09-27-slurp-stage3-reviewer-tfrl-v1/README.md).

## The cell

| item | value |
| --- | --- |
| base (= the in-chain A/A) | the AGREE arm (w_agree 1.0, k 60, fuse 8-1-8; sealed `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`, intent 85.83 / SLU-F1 65.16) with G5's Reviewer instruction `probes/slurp_native_role_reviewer_v1_g5_v1.txt` |
| factor | `phase_material.reviewer.instruction_template`: `probes/slurp_native_role_reviewer_v1_g5_v1.txt` -> `probes/slurp_native_role_reviewer_contrastive_v1.txt` (sha256 `2b6de3b6cfdba2c248efc5a36e1d29b58220c09e0b673a9285cb1cf2ad51e3cf`), the contrastive review form selected offline |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, program and its 11-contact ceiling, the agreement term, the three stores, the Perception / Solver / Planner templates, normaliser, scorers, budgets; `phase_tools` absent |
| in-chain replicate | `SAEA-SLURP-STAGE3-REVTFRL-AA-FOLD-A-V1` |
| admission | NO HARM (owner decision 127): intent CI95 lower bound against the in-chain A/A not below -0.9943, SLU lower bound not below -1.2485; never reported as a gain |
| declared expectation | +0.80 pp intent, the measured transfer of the offline selection statistic (below the benefit bar; claims_benefit false) |
| node credit (beside the verdict) | loop value over the trajectory's own first draft on each arm, per-class credit table |
| runs | `SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-V1` / `SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-REVTFRL-AA-FOLD-A-V1` / `SAEA-SLURP-STAGE3-REVTFRL-AA-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-READ-V1` |
| composed config hashes | arm `f7cc105d59c0828a37cacb7f8e6814ee864ccc5dc7b2faea31fe68970c9ea873`; A/A `ffc36ddcb8a48665786d664f45358d296b8879d39ca437abfddaffa07dcc4844`; smoke `399c9f3ac6542918afafc7281c7411f6db2f1a5f5379618c3ef7cd8da877e495` |
| protocol hashes | arm `d976235252f997c258b50329f6fc256b8275325c8ef2219912cba03132a76fc1`; A/A `978db2dca95467b7c95d87fcda31a1b7b012839b5a4ec95ed21d81fce7ceb368`; smoke `aee8ecadf5868a2bb9f1c58e9632797126984dbf82e339f62e50196ae2dc1e1d` |
| split identity | arm and A/A `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`; smoke `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |
| stage3_algorithm | `sealed-credit-system-policy-v1` (arm and smoke, operators_used `context_application`); `none` on the A/A |

## Decision rule (fixed here)

NO-HARM ADMITTED (owner decision 127): against the IN-CHAIN A/A arm flown in the same chain, the paired CI95 lower bound of the intent-accuracy delta (primary, decision 133) is not below -0.9943 pp AND the paired CI95 lower bound of the official pooled SLU-F1 delta (the guard) is not below -1.2485 pp -- each metric at its own Fold A own-null half-width (docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d). HARMFUL: a measured loss on either metric (CI95 upper bound below zero, decision 25). NEUTRAL-BY-WIDTH IS THE ADMISSION. The cell is NEVER reported as a gain, whatever the point estimate. Beside the verdict, never instead of it, the read reports the NODE CREDIT: on each arm, the loop value (delivered answer minus the same trajectory's first Solver draft, intent and official pooled SLU-F1, paired within the flight, cluster CI95) and the per-visit credit table by pre-review error class computed by scripts/analysis/slurp_reviewer_credit_table.py's own functions; the arm-minus-A/A difference of loop values set beside the declared expectation +0.80 pp; the Reviewer contact rate and REVISE rate; the per-scenario table in both weightings and the frontier row (decision 75); and a model-free count of Reviewer responses narrating a tool call on each arm.

## Expectation (measured, decision 139)

Measured, never a prior (decision 139): on the SAME 625 TRAIN R01C rows (outside Fold A), the contrastive form's review loop moved intent by +2.56 pp over its own first drafts and the locked form's by +0.738 pp (mean of 11 sealed pools); paired per row the difference is +1.697 pp CI95 [+0.263, +3.143] (whole-utterance cluster bootstrap, 2000 draws, seed 20260927). A review loop can only act on a wrong draft, so the transfer to the base scales by the first-draft intent-wrong rate: R01C 1920/6399 = 30.00 % under the locked form, the base 14.17 % (the sealed AGREE arm's official intent 85.83, docs/results/2026-09-27-slurp-agree-w1-fold-a-read.md). Expected intent effect 1.697 x 0.1417 / 0.3000 = +0.80 pp (interval +0.12 to +1.48), BELOW the cross-flight benefit bar of about 2.5 pp at n = 1,080 and below the intent own-null half-width 0.9943: the design cannot see it as a gain, so the cell claims none and is admitted on NO HARM; the node's own within-trajectory loop value is read beside it.

## The confound, stated before contact

The selection's measured object is the review loop of the sealed candidate-recovery control arm, which also changed the Planner's routing text, the Solver's instruction and the candidate proposal. This cell moves the Reviewer instruction ALONE (the brief scopes the optimisation to the node); the Planner keeps the locked routing text and the Solver the locked revision clause. The transfer is therefore an assumption stated here and tested by the read: the arm's own per-visit credit (REVISE rate per class, helped / hurt per revision, the entity-error delta on CORRECT drafts) is compared with the source arm's sealed credit, and a loop value far below the source's is read as 'the lift lived in the Planner / Solver texts', which names the next round's node.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-REVTFRL-AA-FOLD-A-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The in-chain null: the base (AGREE with G5's Reviewer instruction) re-flown in the same chain. Its expected effect is zero by construction.",
      "primary_metric": "intent accuracy and official pooled SLU-F1, as the instrument",
      "replicate_run_id": "SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-V1",
      "rows": 1080
    },
    "SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM only: the new instruction loads by its relpath, every request fits, the Reviewer answers with findings and no tool call, the episode completes. Never scored or read.",
      "primary_metric": "none (structural form only)",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-V1": {
      "admission": "no-harm",
      "claims_benefit": false,
      "expected_effect_pp": 0.8,
      "harm_margin_pp": 1.2485,
      "harm_margin_pp_by_metric": {
        "intent_accuracy": 0.9943,
        "slu_f1": 1.2485
      },
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "Admitted on NO HARM and never reported as a gain. expected_effect_pp is the MEASURED transfer of the offline selection statistic (registered-facts-v1.json expectation_arithmetic), below the design's benefit bar, which is why claims_benefit is false; the harm margin is the design's measured sampling floor at n = 1,080 (Fold A own null, PLAN vs PLANr). The node credit (within-flight loop value per arm) is read beside the verdict and is the next optimisation round's reward signal.",
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
      "replicate_run_id": "SAEA-SLURP-STAGE3-REVTFRL-AA-FOLD-A-V1",
      "rows": 1080
    }
  }
}
```

## Prohibitions

Never reported as a gain. No Fold A gold was used for selection. No paper-scale profile, no test-split, Fold B or DEV
contact, no re-flying of any sealed cell, no second factor. No flight before root mints the decision receipt and the
cells are flipped; `--allow-output-change` is never passed.
