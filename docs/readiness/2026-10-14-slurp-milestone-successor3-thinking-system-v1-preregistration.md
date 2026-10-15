# Successor 3: the Thinking system on the signed test sample, preregistration (DRAFT / HELD)

Registered 2026-10-15 at study commit `727d96336` by script. Development numbers only.

Runs: `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1` / `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-FIT-V1`; packets `SAEA-SLURP-TEST-SAMPLE-3010-THINKING-PACKETS-GPU-V1`; read `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-PAIRED-ANALYSIS-V1`.

The decision rule, the declared DEV twin offset and its limitation are in `docs/readiness/2026-10-14-slurp-milestone-successor3-thinking-system-v1/README.md` and `docs/readiness/2026-10-14-slurp-milestone-successor3-thinking-system-v1/protocol-registered-v1.json`.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1": {
      "admission": "no-harm",
      "bar_pp": 2.5,
      "claim": "no-harm",
      "claims_benefit": false,
      "comparator_attempt_id": "attempt-slurp-milestone-successor2-composed-generation-v1",
      "comparator_run_id": "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1",
      "declared_flight_offset": {
        "intent_pp": 1.6,
        "scope": "DECLARED, borrowed from the DEV P3.1 read (the in-chain twin aa minus the lock arm, DEV-2000-ADDED, n 1,000): the sample has NO in-chain replicate by design. LIMITATION: the DEV twin offset is a different roster and a different n; it is the null this read uses, not a measured null of the sample. The intent offset (1.6 pp) is large against the intent guard (0.65 pp) and is carried as read.",
        "signed": {
          "intent_pp": 1.6,
          "slu_pp": -0.6144
        },
        "slu_pp": 0.6144,
        "source": "analysis/SAEA-SLURP-SYSTEM-THINKING-CORE-DEV2000-ADDED-READ-V1/read.json (data root); sha256 f110be353fdce378555e41544f50e51eca61717af93e5f56095af3ed25d931f5"
      },
      "design_statement": "CROSS-FLIGHT AGAINST A SEALED COLUMN, NO IN-CHAIN REPLICATE, BY DESIGN: the allowance permits one generation run id (lock arm only), the sealed successor-2 run must not be re-flown, and a second flight would consume a second attempt. Instrument rule 4 refuses 'a single cross-flight contrast against an older sealed comparator with no in-chain replicate' (stage3_effect_floor_check.py scopes cells by a 'stage3' token in the fragment stem or experiment id, which this cell, like successors 1 and 2, does not carry, so the refusal is not mechanically enforced); the exception is the owner's: ruling 301 A fixes the declared DEV twin offset with the no-in-chain-replicate limitation stated in the read, the same exception decision 250 A made for successor 2.",
      "expected_effect_basis": {
        "dev_point": {
          "intent_ci95": [
            0.996,
            4.0716
          ],
          "intent_pp": 2.5,
          "slu_ci95": [
            5.4586,
            9.6175
          ],
          "slu_pp": 7.5179
        },
        "primary": "official pooled SLU-F1 (slurp-slu-official-test), post-stratified natural mixture, Thinking system minus the SEALED successor-2 column",
        "reading": "+7.5179 pp is the DEV point of the Thinking lock arm minus the sealed Instruct NX R5 composed column (CI95 [5.4586, 9.6175]); it is the measured number of the P3.1 read (owner decision 139: a measured number, not a prior), declared at registration. claims_benefit stays false in the sense of successor 2's read-qualification: a point above the bar is REPORTED, never claimed."
      },
      "expected_effect_pp": 7.5179,
      "expected_effect_status": "the P3.1 DEV point (owner decision 139), declared at registration",
      "harm_margin_pp": 2.5,
      "harm_margin_pp_by_metric": {
        "intent_accuracy": 2.5,
        "slu_f1": 2.5
      },
      "measurement_design": "cross-flight-no-replicate",
      "note": "SUCCESSOR-3 = the SLURP lock candidate v3.0 (the locked system on the Thinking core) on the signed test sample (owner ruling 301 A). Primary: official pooled SLU-F1 (post-stratified natural mixture; equal-stratum beside it); guard: intent (scenario_action exact). Contrast: Thinking arm minus the SEALED successor-2 column. No claim of benefit. tuning_roster / read_roster (item D3): the vote pool and the centroid key are TRAIN construction artifacts, the v4 rule set behind v4g was selected on the A2 DEV pool and confirmed on TRAIN Fold A and Fold B, COMP-1b on DEV-2000-ADDED; the Thinking transfer was read on TRAIN Fold B (268-B) and DEV-2000-ADDED (P3.1) without tuning; all are disjoint from the sample by its disjointness proof (docs/checks/speech-aware-evidence-acquisition/2026-09-27-slurp-test-sample-roster/disjointness.json, CLEAN); nothing was chosen or tuned on the sample.",
      "own_null": {
        "flag": "NO OWN NULL EXISTS FOR SLURP-TEST-SAMPLE-3010-V1 for the Thinking core (no A/A pair flew on it); the DEV twin offset is declared in its place.",
        "intent_pp": 1.6,
        "kind": "DECLARED-DEV-TWIN-OFFSET-NOT-MEASURED-ON-THE-SAMPLE",
        "scaled_fallback_for_context": {
          "flag": "NO OWN NULL EXISTS FOR SLURP-TEST-SAMPLE-3010-V1 (no A/A pair has flown on it, and the allowance names no second PLAN read id that could measure one). Declared guard = the DEV-2000-ADDED own null scaled by sqrt(913 / 682) at the PROMPT level (rho = 1, conservative: every recording of a prompt moves together; design note section 4 'Sample paired h 1.33'). The recording-level scaling sqrt(1000 / 3010) is given beside it and is the OPTIMISTIC bound; the read reports both.",
          "h_intent": 1.3329,
          "h_intent_recording_scaled": 0.664,
          "h_slu": 1.4492,
          "h_slu_recording_scaled": 0.7219,
          "kind": "FALLBACK-SCALED-NOT-MEASURED",
          "n": 3010,
          "n_prompts": 682,
          "source": "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d, row 'cross-flight A/A, DEV-2000-ADDED' (the B6 pair); scaling: docs/readiness/2026-09-27-slurp-test-sample-design-v1.md section 4"
        },
        "slu_pp": 0.6144
      },
      "owner_ruling_301_a": {
        "date": "2026-10-13",
        "ruling": "Sign the successor-3 allowance now (same terms as v2: one attempt per id, aggregate-only, no smoke, no re-fly); only the lock arm flies on the sample; the comparator is the sealed successor-2 read; the declared twin offset is the DEV twin offset, with the no-in-chain-replicate limitation stated in the read.",
        "source": "docs/receipts/owner/2026-10-13-slurp-test-sample-allowance-successor-3.json"
      },
      "primary_metric": "official pooled SLU-F1 (slurp-slu-official-test), Thinking arm minus the sealed successor-2 column beyond the declared DEV twin offset; intent accuracy (scenario_action exact) the non-inferiority guard",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-TEST-SAMPLE-3010-V1",
      "roster": "TEST-SAMPLE (SLURP-TEST-SAMPLE-3010-V1, split identity 0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9), 3,010 recordings / 682 prompts",
      "rows": 3010,
      "tuning_roster": [
        "slurp-train-construction-pool-agree-kprobe-r01-excluded",
        "SLURP-EVO-FOLD-A-V2",
        "SLURP-DEV-2000-ADDED-V1"
      ]
    }
  }
}
```
