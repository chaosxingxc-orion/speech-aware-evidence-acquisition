# Preregistration: consumption-module all-off arm on audio2tool (2026-09-30, HELD)

Package `docs/readiness/2026-09-30-a2t-native-stage3-module-alloff-v1/`. The all-off block of profile `audio2tool` compiles to the carrier's direct layer; the cell is
a FORM proof of the carrier admission gate (design 2b.3). No benefit is claimed and no number from it admits anything.

```json
{
  "stage3_measurement": {
    "SAEA-A2T-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Form proof of the consumption module's carrier admission gate (design 2b.3): the all-off arm is the carrier's direct baseline bytes; nothing is expected to move and no benefit is claimed.",
      "primary_metric": "a2t-toolcall-official (paper-facing, arXiv:2604.22821 Table 3 calibration) beside a2t-toolcall-v2 / a2t-toolcall / cost",
      "read_roster": "A2T-PAIRED-400-V1 (docs/receipts/rosters/a2t-paired-400-v1.json)",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-A2T-NATIVE-STAGE3-MODULE-ALLOFF-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Form proof of the consumption module's carrier admission gate (design 2b.3): the all-off arm is the carrier's direct baseline bytes; nothing is expected to move and no benefit is claimed.",
      "primary_metric": "a2t-toolcall-official (paper-facing, arXiv:2604.22821 Table 3 calibration) beside a2t-toolcall-v2 / a2t-toolcall / cost",
      "read_roster": "A2T-PAIRED-400-V1 (docs/receipts/rosters/a2t-paired-400-v1.json)",
      "rows": 400,
      "tuning_roster": "none"
    }
  }
}
```
