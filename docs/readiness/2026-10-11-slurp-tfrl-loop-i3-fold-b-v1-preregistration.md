# Loop iteration 3 (supply column): preregistration (DRAFT / HELD)

Registered 2026-10-11 at study commit `0000000000000000000000000000000000000000` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-TFRL-LOOP-I3-FOLD-B-V1` / `SAEA-SLURP-STAGE3-TFRL-LOOP-I3-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-TFRL-LOOP-I3-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-TFRL-LOOP-I3-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-TFRL-LOOP-I3-FOLD-B-COLUMN-READ-V1`.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-TFRL-LOOP-I3-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows prove FORM only: the phase-native-module-v1-c4 program loads, the supply arms fan out with the delivering arm last, the empty ace-playbook-i0 route renders zero bytes on the non-ace arms, every swap resolves its alternate and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-TFRL-LOOP-I3-FOLD-B-V1": {
      "aa_arm_id": "aa",
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "same-flight-supply-variant",
      "nomination_rule": "official-column",
      "note": "Loop iteration 3: arms ace, aa, lock over the delivering lock arm, paired per row inside one flight, preregistered selection rule in docs/readiness/2026-10-11-slurp-tfrl-loop-v1/tfrl-loop-protocol-v1.json. The expected effect is the typed arm's predicted effect when one flies (at least 1.5 pp, decision 192) and is 0.0 with claims_benefit false when the typed arm is empty (the iteration then measures the ACE comparator, the twin null and the offline delivery reads).",
      "primary_metric": "official SLURP pooled SLU-F1 (micro), paired per row",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 1080,
      "tuning_roster": "none",
      "variant_cost": {
        "extra_audio_seconds": 5.842217,
        "extra_contacts_per_row": 2
      }
    }
  }
}
```
