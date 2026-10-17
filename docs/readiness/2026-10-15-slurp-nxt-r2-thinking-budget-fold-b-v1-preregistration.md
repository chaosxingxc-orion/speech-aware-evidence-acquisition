# NX-T R2: the per-node reasoning-budget column, preregistration (DRAFT / HELD)

Registered 2026-10-15 at study commit `6f387e5bf71f1d11921fb5e7c4e8c7d3e5bf2d24` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1` / `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-NXT-R2-THINKING-BUDGET-FOLD-B-READ-V1`.

The node words and the read rule are in `docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1/README.md`.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows prove FORM only: the phase-native-module-v1-c6 module program with 3 arms loads on the Thinking session, each arm's requests carry their own reasoning budget and reserve at the unchanged cap, the forced close fires earlier at a lower budget, the live phase fit passes and the v5 receipt seals. Scored by no one; four rows claim nothing under instrument rule 5.",
      "primary_metric": "none (structural form, per-arm per-node decode cost and the forced-close behaviour only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1": {
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "same-flight-node-column",
      "note": "A per-node cost attribution, not a benefit claim: the question is how much reasoning each node needs, so the expected effect of a cheaper budget is 0.0 pp SLU-F1 (no resolvable loss) and the deliverable is the saving (the throughput table). NO twin flies (owner decision 313 A): the null is the DECLARED same-core A/A offset |o| = 1.15 pp SLU (the larger of the two measured offsets, 268-B +1.15 and P3.1 -0.61) with the paired floor 0.7 pp; the design resolves a per-arm contrast of 1.49 pp SLU / 0.65 pp intent at n = 1,080 (decision 190 node-column floors), which are also the no-resolved-loss margins.",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 1080,
      "template_variants": {
        "candidate_arms": 2,
        "node": "perception",
        "twin": false
      },
      "tuning_roster": "none",
      "variant_cost": {
        "extra_audio_seconds": 12619.19,
        "extra_contacts_per_row": 4
      },
      "variant_kind": "thinking-budget"
    }
  }
}
```
