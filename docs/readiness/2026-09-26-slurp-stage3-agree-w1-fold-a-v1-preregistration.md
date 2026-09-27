# Cell AGREE: preregistration

Registered 2026-09-26 at study commit `c452c048`, before any contact, from the sealed cell PLAN
fragments by script (decision 58). Development numbers only (owner decisions 28 and 86); never a test
claim.

## The cell

| item | value |
| --- | --- |
| base | the locked v2.0 plan, the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` (63.6304 / 82.2222) |
| factor | The intent-boundary Perception channel reads its own registered w_agree term over a pre-computed, self-excluded exemplar-intent vote: w_agree 1.0, w_cos unchanged at 1.0, w_prior unchanged at 0.0, and the DELIVERED width unchanged at 8 entries (fuse_coverage m 8 / c 1 / top_l 8). The RECALL width k moves from 8 to the store's full 60, because k is the provider's top_k_per_dimension and truncates by cosine BEFORE the ranker runs -- at 8 the agreement term is inert, measured. The widening is a proven no-op on its own: the in-chain A/A control carries k 60 at w_agree 0.0 and reproduces the sealed comparator's first-phase output digest AND its rendered request bytes exactly, so the two arms differ in w_agree alone. Nothing else moves. |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, program and its 11-contact ceiling, all three stores and their pins, exemplar k = 20, role graph, templates, normaliser, scorers, budgets |
| comparator | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, sealed, never re-flown |
| in-chain replicate | `SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1`, the locked form re-flown in the SAME campaign chain |
| margins | the plan's own null on this roster (PLANr): h_SLU 1.2485, h_intent 0.9943 |
| smoke | four engineering rows, structural acceptance, never scored |
| runs | `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` / `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1` / `SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-FIT-V1` |
| authority | the model-free read docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md (sections 2, 3, 5 and 6); the measurement instrument docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md (rules 3 and 4); the class headroom of docs/results/2026-09-24-slurp-plan-bad-case-bank.md (sections 1 and 8); owner decisions 28 and 86 (development numbers), 101 (the Stage-3 algorithm label) and 110 |

## Decision rule (fixed here)

NEUTRAL: both guards non-inferior at the plan's own null -- the CI95 lower bound of the paired official pooled SLU-F1 delta above -h_slu and of the intent delta above -h_intent, each measured against the IN-CHAIN A/A arm, not against the sealed comparator alone. ADMITTED: NEUTRAL and the SLU CI95 lower bound above zero against the in-chain A/A. HARMFUL: a measured loss on either guard (decision 25). Every verdict carries the per-stratum table in both weightings, the frontier row (decision 75), the delivery-rate check (did the flown arm deliver the gold intent's boundary entry on the rows the offline replication says it would?) and the measured token delta.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The A/A replicate is the INSTRUMENT, not a claim: it re-flies the locked plan's own form so the AGREE delta is read against a within-chain null. Its expected effect is exactly zero by construction, and a non-zero read on it is a measurement of the instrument, which is what it is for.",
      "primary_metric": "slu_f1",
      "replicate_run_id": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
      "rows": 1080
    },
    "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM and nothing else: that the agreement table loads and hash-verifies, that the boundary channel still delivers eight entries, that every request fits and that the episode completes. Scored by no one, read by no one; under the measurement instrument's rule 5 a batch of four rows can never be evidence of benefit.",
      "primary_metric": "slu_f1",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1": {
      "claims_benefit": true,
      "expected_effect_pp": 2.96,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "Re-declared 2026-09-27 from the CONV probe (owner decisions 139 and 143): m = 32 of 70 newly-delivered rows converted wrong->gold (45.71 %, Wilson CI95 [34.57, 57.30] %), so the expectation is 32 x 0.092615 = 2.96 pp intent against this design's 2.5 pp bar at n = 1,080. Under the retired SLU-F1 framing it would be 1.33 pp. The position read's finding that the term also moves gold to position 1 on 35 of the 86 already-delivered-but-wrong rows is a PRIOR this arm measures, not part of the declared expectation. CONV's row interval [24.2, 40.1] spans 27, so a NEUTRAL-by-width read remains possible; per rows 127 and 139 its disposition is then taken on the number, in conversation. Delivery is not correctness.",
      "primary_metric": "intent accuracy (scenario_action exact), official SLU-F1 the non-inferiority guard (owner decision 133)",
      "replicate_run_id": "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1",
      "rows": 1080
    }
  }
}
```

## How `expected_effect_pp` was derived, and what it is not

DELIVERY IS NOT CORRECTNESS. Every measured quantity above is a count of rows that would RECEIVE their own gold intent's boundary entry; not one of them is a count of rows that would then ANSWER correctly. The conversion between the two is unmeasured, so the declared expected_effect_pp is a construction. It is stated at the midpoint conversion and is reported beside its own ceiling and its whole sweep. It is not a prediction, it is not evidence, and it must not be read as either.

Arithmetic:

- per-row SLU headroom, INTENT-UNCOVERED = 5.41 / 130 = 0.041615 pp
- per-row SLU headroom, INTENT-COVERED   = 2.35 / 61 = 0.038525 pp
- net newly delivered: 70 uncovered, 0 covered
- ceiling at conversion 1.0 = 70 x 0.041615 + 0 x 0.038525 = 2.9131 pp SLU-F1
- conversion = persuasion 0.5 (UNMEASURED) x P(correct | covered) 0.9358 (measured, an upper bound: 889 of 950) = 0.4679
- declared expectation = 2.9131 x 0.4679 = 1.3630 pp SLU-F1

Sweep over the unmeasured conversion (official pooled SLU-F1, pp):
- conversion persuasion 0: 0
- conversion persuasion 0.1: 0.2726
- conversion persuasion 0.25: 0.6815
- conversion persuasion 0.5: 1.363
- conversion persuasion 0.75: 2.0445
- conversion persuasion 1: 2.726

The floor this design must clear at n = 1,080 is 2.5 pp, so the declared expectation
**DOES NOT CLEAR** it. Stated plainly rather than engineered around.

## Budgets and failure rule

Ceilings as cell PLAN's, per generation cell: 11880
generation calls (run-cumulative), 47520 FIT
endpoints, 33930 repeated speech seconds,
12.0 GPU hours, one official complete score. The
smoke: 44 /
176 /
117 s, no score. Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run.

## Prohibitions

No paper-scale profile. No confirmatory or test-split contact. No Fold B or DEV read from this cell. No re-flying of the sealed comparator. No second factor. No w_prior change. No k change. No store rebuild or release. No admission entry from this registration, and no flight before root mints the decision receipt and all three cells are flipped.
