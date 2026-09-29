# Cell W4-SV (same-flight supply-variant read of the W4 slot conventions): preregistration

Registered 2026-09-28 at study commit `190e178db`, before any contact, from the retained AGREE
arm fragments by script (decision 58) under owner decision 172 and the coordinator's W4 verdict. Status `REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP`.
Development numbers only.

Arm-B proof: registered on ARM-B-INERT (proof sha256 `913c5487d5c7cb37e6c323433dc55976e614f7d86676efd370ee9f669e3ea55d`); re-run 2026-09-29 after the renderer fix `3f6688de` at study commit `c24824a46` over 120 rows: ARM-B-VARIES (arm b-w4 differs from a-agree on 120, equals it on 0); arm A IDENTICAL-MODULO-PROGRAM-FIELDS, twin mismatches 0; proof sha256 `5f2ce2400e65ee4004869af6a1aa1ad4c76c02accd0327abffc2dcc8e389eee5`.

## The cell

| item | value |
| --- | --- |
| base | the retained AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (65.1575 / 85.8333) |
| arms (first Solver visit) | `b-w4` release swap to slot-contracts-w4-v1; `t-twin` replicate of a-agree; `a-agree` delivering |
| design / claim | `same-flight-supply-variant` / `nominated` |
| primary / guard | official pooled SLU-F1 of the b-w4 minus a-agree column / intent accuracy |
| expected effect / floor / bar | 0.79 pp / 0.3163 pp provisional / the twin null |
| runs | `SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1` / `SAEA-SLURP-STAGE3-W4SV-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-W4SV-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-W4SV-FOLD-A-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-W4SV-FOLD-A-COLUMN-READ-V1` |
| composed config hashes | arm `ba34275543f0da154584d33884a957aceb9d0e87ab7f719f8cda34d440f9e890`; smoke `ba4fb50c35f6e9d38b358150490abdde862f48ff1c6a6cb8ae6e4881aad04300` |
| protocol hashes | arm `a5134bcb7554bd2063bfdf77d1a9048fc1bee26baf1735e9e5a1d726df4a8c3a`; smoke `f38cf4a55cf406876f4d2c4efaa3e93641ba09b75ae18a832c7a9ba4c7ba2c3b` |
| split identity | arm `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`; smoke `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |

## Estimand

ESTIMAND CAVEAT. The expectation is transferred from cell W4's CROSS-FLIGHT full-system read (docs/results/2026-09-28-slurp-w4-fold-a-read.md: official pooled SLU-F1 +0.79 pp CI95 [-0.56, +2.12] against the shared wave A/A). In that flight the W4 cards reached EVERY node whose request carries the slot-contract supply: the realised prompt tokens rose +1,207.8 per Solver, +1,207.4 per Reviewer and +1,201.9 per Planner contact (the registration had projected +724.5 per Solver contact). Here only arm b-w4's FIRST Solver request carries them: the Reviewer, the Planner and the Solver revisit see the AGREE v2 cards and never see an arm's output. B minus A is therefore the Solver-local first-visit effect of the W4 cards, a DIFFERENT estimand from the +0.79 pp system effect (which also includes the Reviewer and Planner reading the conventions and any revision they drive); 0.79 pp is declared only as the size to look for, not as the value this read should reproduce.

## Decision rule (fixed here)

Columns: the first-visit Solver answers of arm b-w4 (B), the twin t-twin (T) and the delivering arm a-agree (A), each rendered through the delivered row's deliver normaliser and projection (AT1 self-check) and scored ONCE as a complete column with slurp-slu-official-train (stage3_rollout_score.py --mode supply-variants), paired by row (sample_id), 10,000 draws, seed 20260928. THE NULL: T minus A on official pooled SLU-F1 and intent accuracy; its bar is |T - A delta| + the T - A CI95 half-width (the same law as the cross-flight in-chain A/A), never below the provisional floor 0.3163 pp SLU-F1 (the ROLL-AA anchor 0.735 pp at n = 200 scaled to n = 1,080, scripts/checks/stage3_effect_floor_check.py). INSTRUMENT FAULT (no verdict): the T - A CI95 excludes zero on either metric. NOMINATED (the claim ceiling; Q6 ruling): the B - A official pooled SLU-F1 delta exceeds the bar AND its CI95 lower bound is above zero AND the B - A intent CI95 upper bound is not below zero (the guard: no measured intent loss). HARMFUL: the B - A CI95 upper bound below zero on either metric. Otherwise NOT NOMINATED (width). A nomination only sends the composed policy to a full-system read against an in-chain A/A; it is never an admission and never a system-level claim. Every verdict carries the per-scenario table in both weightings and the per-type exact TP/FP/FN of the 19 revised types, B vs A and T vs A.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-W4SV-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM and nothing else: the alternate loads when arm b-w4 selects it, three arms fan out at the first Solver visit only, the twin's wire bytes equal the delivering arm's, every request fits, the episode seals (I7, I7n, I7v). Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-A-V2",
      "rows": 4,
      "tuning_roster": [
        "size-pool-annotated-exemplars-minus-r01",
        "slurp-slot-conventions-w4-support-v1"
      ]
    },
    "SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1": {
      "aa_arm_id": "t-twin",
      "admission": "benefit",
      "claim": "nominated",
      "claims_benefit": true,
      "expected_effect_pp": 0.79,
      "measurement_design": "same-flight-supply-variant",
      "note": "Expected 0.79 pp from the cross-flight W4 read; provisional floor 0.3163 pp at n = 1,080; bar = the twin null. ESTIMAND CAVEAT. The expectation is transferred from cell W4's CROSS-FLIGHT full-system read (docs/results/2026-09-28-slurp-w4-fold-a-read.md: official pooled SLU-F1 +0.79 pp CI95 [-0.56, +2.12] against the shared wave A/A). In that flight the W4 cards reached EVERY node whose request carries the slot-contract supply: the realised prompt tokens rose +1,207.8 per Solver, +1,207.4 per Reviewer and +1,201.9 per Planner contact (the registration had projected +724.5 per Solver contact). Here only arm b-w4's FIRST Solver request carries them: the Reviewer, the Planner and the Solver revisit see the AGREE v2 cards and never see an arm's output. B minus A is therefore the Solver-local first-visit effect of the W4 cards, a DIFFERENT estimand from the +0.79 pp system effect (which also includes the Reviewer and Planner reading the conventions and any revision they drive); 0.79 pp is declared only as the size to look for, not as the value this read should reproduce.",
      "primary_metric": "official pooled SLU-F1 of the first-visit Solver column b-w4 minus a-agree (intent accuracy the guard)",
      "read_roster": "SLURP-EVO-FOLD-A-V2",
      "rows": 1080,
      "tuning_roster": [
        "size-pool-annotated-exemplars-minus-r01",
        "slurp-slot-conventions-w4-support-v1"
      ],
      "variant_cost": {
        "extra_audio_seconds": 6169.057,
        "extra_contacts_per_row": 2
      }
    }
  }
}
```

## Prohibitions

No test-split, Fold B or DEV contact; no re-flying of a sealed cell; no second factor; no paper-scale profile; no claim
above `nominated`; no flight while arm b-w4 is inert; `--allow-output-change` never passed.
