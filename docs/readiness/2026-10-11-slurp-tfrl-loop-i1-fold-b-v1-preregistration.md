# Loop iteration 1 (supply column): preregistration (DRAFT / HELD)

Registered 2026-10-11 at study commit `0000000000000000000000000000000000000000` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-V1` / `SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-COLUMN-READ-V1`.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows prove FORM only: the phase-native-module-v1-c4 program loads, the supply arms fan out with the delivering arm last, the empty ace-playbook-i0 route renders zero bytes on the non-ace arms, every swap resolves its alternate and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-V1": {
      "aa_arm_id": "aa",
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "same-flight-supply-variant",
      "nomination_rule": "official-column",
      "note": "Loop iteration 1: arms ace, aa, lock over the delivering lock arm, paired per row inside one flight, preregistered selection rule in docs/readiness/2026-10-11-slurp-tfrl-loop-v1/tfrl-loop-protocol-v1.json. The expected effect is the typed arm's predicted effect when one flies (at least 1.5 pp, decision 192) and is 0.0 with claims_benefit false when the typed arm is empty (the iteration then measures the ACE comparator, the twin null and the offline delivery reads).",
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

## Smoke recovery (the cell's single recovery re-registration, rec1)

The predecessor attempt was refused at preflight, before any model contact: "supply action 'ace' is invalid: knowledge store ace-playbook snapshot SHA-256 mismatch". Root cause: the ACE snapshot pin was the file hash; corrected to the preparer's content hash (the re-derived column package, master commit 785b2fb9d). The smoke is re-flown whole under the rec1 attempt ids; the arm cell is untouched (its attempt never opened).

RECOVERY 2026-10-11 (the cell's single one; coordinator brief, Fable 5.1). The generation budget is run-cumulative across the attempts of the run id (core/model/adapter.py), so the rec1 plan carries the original plan plus the failed attempt's recorded spend (0 calls, 0 speech-seconds): the cumulative budget equals the original plan. The FIT cap is structural and unchanged (rows x max_contacts x endpoints per contact). The FIT attempt id also takes the rec1 suffix because the smoke is re-flown whole and a (run_id, attempt_id) pair is a one-time key.

- Failed attempt: `attempt-slurp-native-stage3-tfrl-loop-i1-fold-b-smoke-4-generation-v1` (OPENED with 0 calls and 0 audio seconds (reserved 16 calls / 41 speech-seconds); refused at preflight 2026-10-11T13:22Z at flight commit 6cbd9c707 before any model contact; preserved unread under the data root. The FIT attempt was never opened.)
- Root cause: ACE snapshot pin was the file hash; corrected to the preparer's content hash.
- Re-flown whole under generation attempt `attempt-slurp-native-stage3-tfrl-loop-i1-fold-b-smoke-4-generation-rec1-v1` and FIT attempt `attempt-slurp-native-stage3-tfrl-loop-i1-fold-b-smoke-4-fit-rec1-v1`; the arm cell is untouched (its attempt never opened); the run ids and the minted decision receipt are unchanged.
- Run-cumulative plan budget: 16 + 0 = 16 calls; 41 + 0 = 41 speech-seconds; the FIT cap stays structural.
- Plans: `smoke-generation-plan-registered-rec1-v1.json`, `smoke-fit-plan-registered-rec1-v1.json` (the first-attempt smoke plan files are superseded and removed from the package; the git history keeps them).
- A second failure closes the cell; the fix is proven on a four-row dry run.
