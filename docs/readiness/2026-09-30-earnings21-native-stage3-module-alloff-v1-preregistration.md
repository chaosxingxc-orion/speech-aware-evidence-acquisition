# Preregistration: consumption-module all-off arm on earnings (2026-09-30, HELD)

Package `docs/readiness/2026-09-30-earnings21-native-stage3-module-alloff-v1/`. The all-off block of profile `earnings` compiles to the carrier's direct layer; the cell is
a FORM proof of the carrier admission gate (design 2b.3). No benefit is claimed and no number from it admits anything.

```json
{
  "stage3_measurement": {
    "SAEA-EARNINGS21-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Form proof of the consumption module's carrier admission gate (design 2b.3): the all-off arm is the carrier's direct baseline bytes; nothing is expected to move and no benefit is claimed.",
      "primary_metric": "asr-wer-whisper (Whisper-normalised WER) beside conec-entity-wer-official, numeric-value-accuracy-v1, semantic-high-impact-error-rate-v1 and cost",
      "read_roster": "Earnings-21 full discovery, 44 calls / 1,593 native windows (split identity fcc1b0bc...)",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-EARNINGS21-NATIVE-STAGE3-MODULE-ALLOFF-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Form proof of the consumption module's carrier admission gate (design 2b.3): the all-off arm is the carrier's direct baseline bytes; nothing is expected to move and no benefit is claimed.",
      "primary_metric": "asr-wer-whisper (Whisper-normalised WER) beside conec-entity-wer-official, numeric-value-accuracy-v1, semantic-high-impact-error-rate-v1 and cost",
      "read_roster": "Earnings-21 full discovery, 44 calls / 1,593 native windows (split identity fcc1b0bc...)",
      "rows": 1593,
      "tuning_roster": "none"
    }
  }
}
```
