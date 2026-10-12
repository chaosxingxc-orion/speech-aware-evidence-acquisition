# 268-B: the locked system on the Thinking core, preregistration (DRAFT / HELD)

Registered 2026-10-12 at study commit `22bdee18d93abdb952658d68cb3e980371ab5eda` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-LOCK-V1` / `SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-LOCK-FIT-V1`; twin `SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-AA-V1` / `SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-AA-FIT-V1`; `SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-SYSTEM-THINKING-CORE-FOLD-B-READ-V1`.

The verdict words and the read rule are in `docs/readiness/2026-10-12-slurp-system-thinking-core-fold-b-v1/README.md`.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-AA-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The request-identical twin of the Thinking system arm: it measures the same-core offset the cross-flight contrast is judged against; expected_effect_pp is 0.0 because a request-identical pair is registered to look for no effect.",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "replicate_run_id": "SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-LOCK-V1",
      "rows": 1080,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-LOCK-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 11.9,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "Transfer of a core lever, not an admission: the declared prior is the bare-core delta of 266-E (+11.9 pp SLU-F1, +4.35 intent) and claims_benefit is false. The Thinking system arm is read cross-flight against the Instruct lock column of loop iteration 3 (SAEA-SLURP-STAGE3-TFRL-LOOP-I3-FOLD-B-V1, same roster, same system) with the in-chain request-identical twin as the A/A replicate.",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "replicate_run_id": "SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-AA-V1",
      "rows": 1080,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows prove FORM only: the module program loads on the Thinking session, the Thinking packets resolve, reasoning stays out of the delivered content, the live phase fit passes at the cap and the episode completes; the per-node decode cost is reported. Scored by no one; four rows claim nothing under instrument rule 5.",
      "primary_metric": "none (structural form and per-node decode cost only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    }
  }
}
```
