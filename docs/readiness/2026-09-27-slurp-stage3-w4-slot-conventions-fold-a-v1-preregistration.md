# Cell W4 (slot conventions): preregistration

Registered 2026-09-27 at study commit `eb450736`, before any contact, from the retained AGREE
arm fragments by script (decision 58) with one pin moved, under owner decision 164. Development numbers only.

## The cell

| item | value |
| --- | --- |
| base | the retained AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (65.1575 / 85.8333), owner decision 161 |
| factor | `knowledge_stores.slot-contracts`: slot-contracts-v2 -> slot-contracts-w4-v1 (release `c7bdeee6e0859fbba6bce79cd3d42347a5b74770f7564094e3d3a0edfe003fb0`, snapshot content `51d634cfcb398038377feca89d2783f59a705546390839e7cf4dd7d15ad3b9d6`); 19 cards extended, intent bindings byte-identical |
| in-chain replicate | `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (the knowledge wave's shared A/A, registered by the coordinator) |
| primary / guard | official pooled SLU-F1 / intent accuracy (decision 133 scopes intent-primary to intent-acting mechanisms) |
| admission | NO HARM: SLU lower bound >= -1.2485, intent lower bound >= -0.9943 |
| runs | `SAEA-SLURP-STAGE3-W4-FOLD-A-V1` / `SAEA-SLURP-STAGE3-W4-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-W4-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-W4-FOLD-A-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1` |
| composed config hashes | arm `b5750327c95fc3f2c073e836242d2bdfd62fe52e23f6f64aa6762c6d571f1088`; smoke `e5ed40abe583ec703f6cea4499390bddcf641b8b517961115513ff5ef3bd8768` |
| protocol hashes | arm `5e963ce2eac84be846ba70dcdced8e0b480c3a8874b725b71a102ca941d4d5de`; smoke `435b283850789ad00a9d86354aeba2ee7f4f3ae0e6a153b1f153404cc380e489` |
| split identity | arm `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`; smoke `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |

## Decision rule (fixed here)

NO-HARM ADMITTED: against the knowledge wave's SHARED in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 flown in the same chain, the paired CI95 lower bound of the official pooled SLU-F1 delta (PRIMARY -- the mechanism acts on slots, so owner decision 133's intent-primary rule, scoped to intent-acting mechanisms, does not apply and decision 115's shape holds) is not below -1.2485 pp AND the paired CI95 lower bound of the intent-accuracy delta (the guard) is not below -0.9943 pp -- each at its own Fold A own-null half-width (docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d). HARMFUL: a measured loss on either metric (CI95 upper bound below zero, decision 25). A SLU-F1 CI95 lower bound above zero is REPORTED as a development-fold effect beside the no-harm verdict, never as an admission of benefit (the design's benefit floor is 2.5 pp and the measured analogue sits below it). Every verdict carries the per-scenario table in both weightings, the frontier row (decision 75), the per-type FN/FP table on the 19 revised types, the realised prompt-token delta per Solver/Reviewer/Planner contact and per row, and the K2/K3/K4 item classes of registered-facts-v1.json read on the sealed arm.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-W4-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM and nothing else: the slot-contracts-w4-v1 release loads by its pins, every extended card renders, every request fits and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-W4-FOLD-A-V1": {
      "admission": "no-harm",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "harm_margin_pp": 1.2485,
      "harm_margin_pp_by_metric": {
        "intent_accuracy": 0.9943,
        "slu_f1": 1.2485
      },
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "W4 acts on SLOTS, so SLU-F1 is primary and intent the guard (owner decision 133 scopes intent-primary to intent-acting mechanisms). The expectation is declared from the measured analogue only (row 139): M4b (cell B4b, the date/time slot-contract revision) moved official pooled SLU-F1 by +2.5519 (first) and +1.5403 (request-identical replicate) over 349 FN items on its eight revised types -- 0.004413 to 0.007312 pp per item; W4 targets 301 FN items on its 19 revised types where the card was delivered on the AGREE arm, so the analogue expects 1.3285 to 2.2009 pp (mean 1.7647). That is BELOW the design's 2.5 pp benefit floor at n = 1,080, so a benefit declaration would be refused (effect-below-floor) and the cell is declared NO-HARM: expected_effect_pp 0.0, claims_benefit false, harm_margin_pp 1.2485 (SLU, primary) with intent 0.9943 as the guard; the analogue is recorded in registered-facts-v1.json (expectation_basis) and never used as an admission bar. Read against the shared in-chain A/A flown in the same chain (rule 3).",
      "primary_metric": "official pooled SLU-F1 (primary: a slot-acting mechanism, owner decision 133's scope), intent accuracy the non-inferiority guard",
      "replicate_run_id": "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1",
      "rows": 1080
    }
  }
}
```

## Prohibitions

No test-split, Fold B or DEV contact; no re-flying of the comparator; no second factor; no paper-scale profile; no
flight before the receipt is minted, the shared A/A registered and the cells flipped; `--allow-output-change` never passed.
