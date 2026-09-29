# Cell A2 (COMP-1b on DEV-2000-ADDED): preregistration

Registered 2026-09-29 at study commit `64ab71d14`, before any contact (owner decision 198).
Development numbers only (owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| composition | A2 is COMP-1b's composed plan with only the roster moved, equivalently the superseded COMP-1 DEV-2000-ADDED placeholder with the citation contract reverted: the locked v2.0 plan as the sealed DEV-2000-ADDED plan arm flew it + (1) the agreement term (w_agree 1.0 over the exemplar-intent vote, recall k 60, delivered 8-1-8; this roster's own vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) + (2) the centroid boundary key (facet_source prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl) + (3) NO citation contract: policy phase-native-candidates-review-revise-v1, Solver probes/slurp_native_role_solver_v2.txt, no response format, deliver_normaliser saea-deliver-normalise-v3 + (4) nothing else. |
| roster | DEV-2000-ADDED (SLURP-DEV-2000-ADDED-V1), 1,000 rows, split role dev, scorer slurp-slu-official |
| in-chain A/A | `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1`, flown in the same campaign before the arm |
| margins | this roster's own null: h_intent 1.152, h_SLU 1.2525 |
| smoke | four rows, structural acceptance, never scored |
| runs | `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1` / `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-FIT-V1`; `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1` / `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-FIT-V1`; `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-SMOKE-4-FIT-V1` |
| composed config hashes | arm `7390b142c52f46c2146618088ea17ce3f9fb89af11c96668fcdcece8a1b42354`; A/A `71462277daeea3f0c9b08c1f099b64fd79949a3f8659177013756871ecac7dd3`; smoke `86129b67e9ca5a206ef5cb5e21feed9737bc96dededed1ac6fbf85a7454bc1b4` |
| protocol hashes | arm `16541c9afe2fe43f6a1fd9092d48b0035bbe8e5c9a599bc6964dcdb70172f294`; A/A `5bc29d22e2fa75481cfe3ff9158fbe1e6388657a7f57de83fac2446bee18488c`; smoke `351a6048f2c6f480bee824a3b4d95d59377c2ec95c474ebfe84c44b3a569a081` |
| supersedes | `docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1` (arm and smoke) |

## Decision rule (fixed here)

Read against the in-chain A/A flown in the same campaign. PRIMARY: intent accuracy (scenario_action exact), paired per utterance, 10,000 bootstrap draws. GUARD: official pooled SLU-F1 (slurp-slu-official) non-inferior at this roster's own null (h_SLU 1.2525). REPLICATED: the intent CI95 lower bound above zero, the point at or above the 2.6 pp cross-flight bar at n = 1,000, AND the guard holds. NEUTRAL: both guards non-inferior at the own null (h_intent 1.152 / h_SLU 1.2525) without a replicated gain. HARMFUL: a measured loss on either guard (decision 25). Every verdict carries the per-stratum tables in both weightings and the attribution classes.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-SMOKE-4-V1": {
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM only; scored by no one, read by no one (instrument rule 5).",
      "primary_metric": "intent accuracy (scenario_action exact)",
      "primary_metric_key": "intent",
      "read_roster": "SLURP-DEV-2000-ADDED-V1",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1": {
      "claim": "nominated",
      "claims_benefit": true,
      "expected_effect_pp": 3.8,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "A2 = COMP-1b on DEV-2000-ADDED (owner decision 198). expected_effect_pp 3.8 is the COMP-1b TRAIN Fold A read's intent point estimate (docs/results/2026-09-29-slurp-comp1b-fold-a-read.md: intent +3.80 pp CI95 [+1.94, +5.65], official pooled SLU-F1 -0.60 pp [-2.29, +1.07] against the in-chain A/A SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 (n = 1,080); zero-gold entity emission 161 vs 162 rows; coordinator bar NOMINATED (intent), SLU non-inferiority open on width); owner decision 139: a number measured on a sealed read is not a prior. The SLU-F1 guard is THIS roster's own null h_SLU 1.2525 (h_intent 1.152), docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d, row 'cross-flight A/A, DEV-2000-ADDED' (the B6 pair). The cross-flight bar at n = 1,000 is about 2.6 pp. tuning_roster / read_roster (item D3, owner decision 190): the agreement vote pool and the centroid key are TRAIN construction-pool artifacts disjoint from DEV-2000-ADDED by the roster receipt's disjointness_proof, and the vote table on this roster is its own (0 self-excluded exemplars measured); nothing in this cell was tuned on DEV-2000-ADDED.",
      "own_null": {
        "h_intent": 1.152,
        "h_slu": 1.2525,
        "measured_offset_slu_pp": -0.25,
        "n": 1000,
        "source": "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d, row 'cross-flight A/A, DEV-2000-ADDED' (the B6 pair)"
      },
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 (slurp-slu-official, DEV sibling) the non-inferiority guard (owner decision 133)",
      "primary_metric_key": "intent",
      "read_roster": "SLURP-DEV-2000-ADDED-V1",
      "replicate_run_id": "SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1",
      "roster": "DEV-2000-ADDED (SLURP-DEV-2000-ADDED-V1, split identity ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67)",
      "rows": 1000,
      "tuning_roster": "slurp-train-construction-pool-agree-kprobe-r01-excluded"
    }
  }
}
```

## Where the declared 3.8 pp comes from

The COMP-1b TRAIN Fold A read, docs/results/2026-09-29-slurp-comp1b-fold-a-read.md: intent +3.80 pp CI95 [+1.94, +5.65], official pooled SLU-F1 -0.60 pp [-2.29, +1.07] against the in-chain A/A SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 (n = 1,080); zero-gold entity emission 161 vs 162 rows; coordinator bar NOMINATED (intent), SLU non-inferiority open on width. It is a prediction to be tested on a fresh
roster, not a foregone conclusion.

## Prohibitions

- No flight before root countersigns the rows, mints the decision receipt and the three cells are flipped in one converged cycle.
- No re-flying of the sealed DEV plan arm; no test, DEV-1000 or Fold B contact.
- No citation contract; no k, tau, fuse_coverage, w_prior, store, release, snapshot, roster or geometry change.
- No paper-scale profile. --allow-output-change is never passed.
