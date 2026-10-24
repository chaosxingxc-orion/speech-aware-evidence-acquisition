# L338: the lever column, preregistration (DRAFT / HELD)

Registered 2026-10-24 at study commit `a3ade87c0e1629f2d26f2bd785a774caddea7c59` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-L338-LEVER-COLUMN-FOLD-B-V1` / `SAEA-SLURP-STAGE3-L338-LEVER-COLUMN-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-L338-LEVER-COLUMN-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-L338-LEVER-COLUMN-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-L338-LEVER-COLUMN-FOLD-B-READ-V1`.

The arm words and the read rule are in `docs/readiness/2026-10-19-slurp-l338-lever-column-fold-b-v1/README.md`.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-L338-LEVER-COLUMN-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows prove FORM only: the phase-native-module-v1-c15 module program with 4 sampling arms loads on the resident Thinking session, each sampled contact carries the lock's thinking fields, its sample index, derived seed and the arm's decoding, no node hits its cap, the live phase fit passes and the v6 receipt seals. Scored by no one; four rows claim nothing under instrument rule 5.",
      "primary_metric": "none (structural form, per-arm decode cost and the sampling receipt only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-L338-LEVER-COLUMN-FOLD-B-V1": {
      "aa_arm_id": "aa",
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "same-flight-node-column",
      "note": "A per-arm nomination, not a benefit claim: the round maps two sampling levers on the Thinking core, so no effect is assumed (0.0 pp SLU-F1) and the deliverable is the paired contrast with its cost. The null is the in-flight twin aa; the design resolves a per-arm contrast of 1.49 pp SLU / 0.65 pp intent at n = 1,080 (decision 190 node-column floors). L1 is judged on SLU with an intent guard, L2 on intent with an SLU guard. The summary key template_variants names the node-column summary of the effect-floor gate, not the template axis.",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "primary_metric_key": "slu",
      "primary_metric_key_by_arm": {
        "l1-support": "slu",
        "l2-union": "intent"
      },
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 1080,
      "template_variants": {
        "candidate_arms": 2,
        "node": "perception",
        "twin": true
      },
      "tuning_roster": "none",
      "variant_cost": {
        "extra_audio_seconds": 41012.37,
        "extra_contacts_per_row": 13
      },
      "variant_kind": "solver-sampling",
      "variant_kind_by_arm": {
        "l1-support": "solver-sampling",
        "l2-union": "perception-sampling"
      }
    }
  }
}
```
