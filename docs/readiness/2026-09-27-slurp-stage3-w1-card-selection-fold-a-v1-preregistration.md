# Cell W1 (slot-card selection): preregistration

Registered 2026-09-27 at study commit `88edc193272f9bdb11f5099124b03cbb39f7d5b0`, before any contact, from the retained AGREE
fragments by script (`scripts/flights/derive_slurp_w1_cells.py`, decision 58) with one key added, under owner decisions 127, 161 and 164.
Development numbers only (owner decisions 28 and 86); never a test claim.

| item | value |
| --- | --- |
| base | the retained AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (intent 85.8333 / SLU 65.1575), sealed, never re-flown |
| factor | Composed key knowledge_stores.slot-contracts.candidate_supply.solver.candidate_legality_source: absent -> the pinned legality table prepared/SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1/legality.json (sha256 59b507b4e36970d4328b3442a31c790c2be48e2e47f4247bd3764bf2fddd1bad); the card route's authored index (402 pairs) narrowed to the 286 pairs the released exemplar store carries in at least two distinct utterances; nothing added. |
| in-chain replicate | `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`, the AGREE arm's own bytes, registered by the coordinator, flown in the SAME chain |
| admission | NO HARM: intent CI95 lower bound against the A/A not below -0.9943, SLU not below -1.2485; never reported as a gain |
| declared ceiling | -1185.83 tokens per Solver contact (mean), -3629.596 per row; pre-flight card envelope 57,846 -> 50,030 bytes |
| registered risk | 5 rows / 5 gold items lose their type's card (1 delivered right by AGREE) |
| runs | `SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1` / `SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-FIT-V1`; READ `SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1` |
| composed config hashes | arm `bcf7471661837bb63104d89bfc8bd1e4ed86a350edf0a65d4d72188ed61950b0`; smoke `1daf0fed20686170b688f175674ba673d1acd0fb981c2128612cd2726f423ce1` |
| protocol hashes | arm `c647b73d2310246cb726a25e7d340bf622decdafe88238fae5594a6a2063f53f`; smoke `3ed39903556d37426c9a89b16a40167b9049dd69c56a8db28aa16edb36920a31` |
| split identity | arm `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`; smoke `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |

## Decision rule (fixed here)

NO-HARM ADMITTED (owner decision 127): against the SHARED in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 (the retained AGREE arm's own bytes, registered by the coordinator for wave items W1-W4) flown in the same chain, the paired CI95 lower bound of the intent-accuracy delta (primary, decision 133) is not below -0.9943 pp AND the paired CI95 lower bound of the official pooled SLU-F1 delta (the guard) is not below -1.2485 pp -- each at its own Fold A own-null half-width (PLAN vs PLANr, docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d; the G5 precedent). HARMFUL: a measured loss on either metric (CI95 upper bound below zero, decision 25). NEUTRAL-BY-WIDTH IS THE ADMISSION (decision 127). Never reported as a gain; two base items are never assumed to add (decision 138). Every verdict carries the per-scenario table in both weightings, the frontier row (decision 75), the measured Solver prompt-token delta per contact and per row from the sealed COST records, and the registered harm rows (5 rows that lose a gold-type card) read row by row.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM and nothing else: that the legality table loads and verifies, that the card route narrows without error, that every request fits and that the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1": {
      "admission": "no-harm",
      "claims_benefit": false,
      "declared_ceiling": {
        "cards_per_row": {
          "flown": 12.904,
          "w1": 9.869
        },
        "kind": "form: prompt room freed, not a task-quality expectation",
        "preflight_solver_card_envelope_utf8_bytes": {
          "flown": 57846,
          "w1": 50030
        },
        "preflight_solver_rendered_tokens": {
          "after": 19272,
          "before": 21278
        },
        "source": "docs/readiness/2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1/card-selection-measurement-v1.json (sha256 4303999d7f7df3b26fabfe54ffb266d635fda8705750f0466bc6564ec200df53)",
        "tokens_per_1080_row_flight": 3919964,
        "tokens_per_row_mean_over_every_contact_rendering_the_block": 3629.596,
        "tokens_per_solver_contact_mean": 1185.83,
        "tokens_per_solver_contact_median": 1070,
        "tokens_per_solver_contact_p95": 2483
      },
      "expected_effect_pp": 0.0,
      "harm_margin_pp": 1.2485,
      "harm_margin_pp_by_metric": {
        "intent_accuracy": 0.9943,
        "slu_f1": 1.2485
      },
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "A row-127 FORM item (knowledge-wave W1, owner decision 164), admitted on NO HARM and never reported as a gain: expected_effect_pp is 0.0 because the cell registers no effect to look for, claims_benefit is false, and the harm margin is the measured floor of this design at n = 1,080 (the Fold A own-null half-width of PLAN vs PLANr, SLU 1.2485 in the gate's field, intent 0.9943 applied by the read), exactly as G5 declared it. The delta is read against the shared in-chain A/A of the AGREE arm's own bytes flown in the same chain, never against the sealed AGREE arm alone. The declared ceiling is the prompt room freed (declared_ceiling), measured model-free on the sealed AGREE arm; the measured risk is 5 rows / 5 gold items whose slot card W1 drops (1 delivered exactly right by AGREE).",
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
      "replicate_run_id": "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1",
      "rows": 1080
    }
  }
}
```

## Budgets and failure rule

Arm 11,880 generation contacts (run-cumulative), 47,520 FIT endpoints, 33,930
repeated speech seconds, 12.0 GPU hours, one official complete score; smoke 44 / 176 /
117 / 1.0, never scored. Expected about 4,385 contacts at the AGREE arm's rate. Stop and preserve on
the first failure; AT MOST ONE root-diagnosed recovery re-registration.

## Prohibitions

Never reported as a gain. No paper-scale profile, no test-split, Fold B or DEV contact, no comparator re-flight, no
second factor, no flight before root mints the receipt and the cells are flipped, and `--allow-output-change` is never
passed.
