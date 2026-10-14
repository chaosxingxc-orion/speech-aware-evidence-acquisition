# NX-T R1: the per-node thinking-policy column, preregistration (DRAFT / HELD)

Registered 2026-10-14 at study commit `8132badd8` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1` / `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1`.

The node words and the read rule are in `docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/README.md`.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows prove FORM only: the c10 module program with five arms loads on the Thinking session, each arm's requests carry their own thinking fields, enable_thinking false answers without reasoning bytes or a think marker (or does not: the table says), the live phase fit passes and the v5 receipt seals. Scored by no one; four rows claim nothing under instrument rule 5.",
      "primary_metric": "none (structural form, per-arm per-node decode cost and the no-think behaviour only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1": {
      "aa_arm_id": "both-on-twin",
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 7.15,
      "measurement_design": "same-flight-node-column",
      "note": "A per-node attribution, not a benefit claim: the largest contrast the column can show is both-off against both-on, expected at about 7.15 pp SLU-F1 (the 268-B read: the Thinking system 71.61 against the Instruct system 64.45; the no-think core on the same weights is expected near the Instruct system). The two single-node arms split that gap in an unknown way; the design resolves a per-node contrast of 1.49 pp SLU / 0.65 pp intent at n = 1,080 (decision 190 node-column floors), so the column's resolving power is the per-node attribution. The in-flight twin both-on-twin is the A/A null; the 268-B cross-flight twin offset (+1.15) is the external reference.",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 1080,
      "template_variants": {
        "candidate_arms": 3,
        "node": "perception",
        "twin": true
      },
      "tuning_roster": "none",
      "variant_cost": {
        "extra_audio_seconds": 25238.38,
        "extra_contacts_per_row": 8
      },
      "variant_kind": "thinking-policy"
    }
  }
}
```
