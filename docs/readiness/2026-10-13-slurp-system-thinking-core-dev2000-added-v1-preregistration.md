# P3.1: the locked system on the Thinking core, DEV-2000-ADDED replicate, preregistration (DRAFT / HELD)

Registered 2026-10-13 at study commit `aabd72d6893ecf53129c4fb0d9e4b10413237771` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-LOCK-V1` / `SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-LOCK-FIT-V1`; twin `SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-AA-V1` / `SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-AA-FIT-V1`; `SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-SMOKE-4-FIT-V1`; read `SAEA-SLURP-SYSTEM-THINKING-CORE-DEV2000-ADDED-READ-V1`; packets `SAEA-SLURP-DEV2000-ADDED-THINKING-PACKETS-GPU-V1`.

The verdict words and the read rule are in `docs/readiness/2026-10-13-slurp-system-thinking-core-dev2000-added-v1/README.md`.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-AA-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The request-identical twin of the Thinking system arm: it measures the same-core offset the cross-flight contrast is judged against; expected_effect_pp is 0.0 because a request-identical pair is registered to look for no effect.",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-DEV-2000-ADDED-V1",
      "replicate_run_id": "SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-LOCK-V1",
      "rows": 1000,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-LOCK-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 7.15,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "Replicate, not an admission: the declared prior is the 268-B Fold B contrast (+7.15 pp SLU-F1, +2.31 intent) and claims_benefit is false. The Thinking system arm is read cross-flight against the sealed Instruct lock column SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1 (same roster, same system) with the in-chain request-identical twin as the A/A replicate.",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-DEV-2000-ADDED-V1",
      "replicate_run_id": "SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-AA-V1",
      "rows": 1000,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four DEV-2000-ADDED rows prove FORM only: the module program loads on the Thinking session, the DEV Thinking packets resolve, reasoning stays out of the delivered content, the live phase fit passes at the cap and the episode completes; the per-node decode cost is reported. Scored by no one; four rows claim nothing under instrument rule 5.",
      "primary_metric": "none (structural form and per-node decode cost only)",
      "read_roster": "SLURP-DEV-2000-ADDED-V1",
      "rows": 4,
      "tuning_roster": "none"
    }
  }
}
```
