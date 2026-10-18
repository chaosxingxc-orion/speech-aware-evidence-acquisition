# NX-T R4: the Solver decoding-policy column, preregistration (DRAFT / HELD)

Registered 2026-10-18 at study commit `56853bba4a4b33b7574008f8853d34e20d0ea248` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-NXT-R4-SOLVER-DECODING-FOLD-B-V1` / `SAEA-SLURP-STAGE3-NXT-R4-SOLVER-DECODING-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-NXT-R4-SOLVER-DECODING-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-NXT-R4-SOLVER-DECODING-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-NXT-R4-SOLVER-DECODING-FOLD-B-READ-V1`.

The arm words and the read rule are in `docs/readiness/2026-10-18-slurp-nxt-r4-solver-decoding-fold-b-v1/README.md`.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-NXT-R4-SOLVER-DECODING-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows prove FORM only: the phase-native-module-v1-c7 module program with 6 Solver arms loads on the resident Thinking session, each arm's request carries the lock's thinking fields and its own sampling parameters, no node hits its cap, the live phase fit passes and the v6 receipt seals. Scored by no one; four rows claim nothing under instrument rule 5.",
      "primary_metric": "none (structural form, per-arm Solver decode cost and the forced-close behaviour only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-NXT-R4-SOLVER-DECODING-FOLD-B-V1": {
      "aa_arm_id": "aa",
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "same-flight-node-column",
      "note": "A per-arm nomination, not a benefit claim: the round maps four Solver sampling policies on the Thinking core, so no effect is assumed (0.0 pp SLU-F1) and the deliverable is the paired contrast with its cost. The null is the in-flight twin aa; the design resolves a per-arm contrast of 1.49 pp SLU / 0.65 pp intent at n = 1,080 (decision 190 node-column floors). The summary key template_variants names the node-column summary of the effect-floor gate, not the template axis.",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 1080,
      "template_variants": {
        "candidate_arms": 4,
        "node": "solver",
        "twin": true
      },
      "tuning_roster": "none",
      "variant_cost": {
        "extra_audio_seconds": 15773.99,
        "extra_contacts_per_row": 5
      },
      "variant_kind": "solver-decoding"
    }
  }
}
```
