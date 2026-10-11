# Preregistration: consumption-module all-off arm on earnings22 (2026-10-11, HELD)

Package `docs/readiness/2026-10-11-earnings22-module-alloff-v1/`. The all-off block of profile `earnings22` compiles to the carrier's direct layer; the cell is
a FORM proof of the carrier admission gate (design 2b.3). No benefit is claimed and no number from it admits anything.

```json
{
  "stage3_measurement": {
    "SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Form proof of the consumption module's carrier admission gate (design 2b.3): the all-off arm is the carrier's direct baseline bytes; nothing is expected to move and no benefit is claimed.",
      "primary_metric": "asr-wer-whisper only (corpus-level Whisper English-normalizer WER, the paper-facing metric; no ConEC, entity or numeric layer exists for Earnings-22). Scorer variant: the PLAIN window-form scorer, NOT the ESB short-form tail-2 s variant of docs/readiness/2026-09-05-scoring-alignment-conclusions.md (15.937 sealed vs 9.2377 under the 2.0 s digital-silence tail, deviation D-TS2-3): this cell appends no tail silence, reads whole 90 s windows of whole dev calls rather than ESB test utterances, and so none of 15.937 / 9.2377 / 9.79 / 12.3 is a comparator and no alignment band is claimed",
      "read_roster": "Earnings-22 whole dev split, 10 calls / 451 native windows (split identity 89b178d6...)",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Form proof of the consumption module's carrier admission gate (design 2b.3): the all-off arm is the carrier's direct baseline bytes; nothing is expected to move and no benefit is claimed.",
      "primary_metric": "asr-wer-whisper only (corpus-level Whisper English-normalizer WER, the paper-facing metric; no ConEC, entity or numeric layer exists for Earnings-22). Scorer variant: the PLAIN window-form scorer, NOT the ESB short-form tail-2 s variant of docs/readiness/2026-09-05-scoring-alignment-conclusions.md (15.937 sealed vs 9.2377 under the 2.0 s digital-silence tail, deviation D-TS2-3): this cell appends no tail silence, reads whole 90 s windows of whole dev calls rather than ESB test utterances, and so none of 15.937 / 9.2377 / 9.79 / 12.3 is a comparator and no alignment band is claimed",
      "read_roster": "Earnings-22 whole dev split, 10 calls / 451 native windows (split identity 89b178d6...)",
      "rows": 451,
      "tuning_roster": "none"
    }
  }
}
```
