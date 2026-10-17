# NX-T R2b: the Solver reasoning-budget raise, preregistration (DRAFT / HELD)

Registered 2026-10-17 at study commit `c878ec3d1f647b5b2c83f6eb9e1e7c85d798e764` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-V1` / `SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-NXT-R2B-SOLVER-BUDGET-FOLD-B-READ-V1`.

The node words and the read rule are in `docs/readiness/2026-10-17-slurp-nxt-r2b-solver-budget-fold-b-v1/README.md`.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows prove FORM only: the phase-native-module-v1-c4 module program with 2 arms loads on the raised-cap Thinking session, each arm's requests carry their own reasoning budget and cap, no node hits its cap, the live phase fit passes at the raised cap and the v5 receipt seals. Scored by no one; four rows claim nothing under instrument rule 5.",
      "primary_metric": "none (structural form, per-arm per-node decode cost and the forced-close behaviour only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-V1": {
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "same-flight-node-column",
      "note": "A per-node attribution, not a benefit claim: the question is whether untruncated Solver reasoning moves the score, so no effect is assumed (0.0 pp SLU-F1) and the deliverable is the contrast with its cost (the throughput table). NO twin flies (owner decision 313 A): the null is the DECLARED same-core A/A offset |o| = 1.15 pp SLU (the larger of the two measured offsets, 268-B +1.15 and P3.1 -0.61) with the paired floor 0.7 pp; the design resolves a per-arm contrast of 1.49 pp SLU / 0.65 pp intent at n = 1,080 (decision 190 node-column floors), which are also the no-resolved-effect margins.",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 1080,
      "template_variants": {
        "candidate_arms": 1,
        "node": "perception",
        "twin": false
      },
      "tuning_roster": "none",
      "variant_cost": {
        "extra_audio_seconds": 6309.59,
        "extra_contacts_per_row": 2
      },
      "variant_kind": "thinking-budget"
    }
  }
}
```
