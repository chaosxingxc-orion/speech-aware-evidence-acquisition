# NX-T R1: the per-node thinking-policy column, preregistration (DRAFT / HELD)

Registered 2026-10-14 at study commit `774c38d9138837d1e663c983b7cf765b8a4cbe31` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1` / `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-REC1-V1`; `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1`.

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

## Recovery rec1: the thinking-policy column flight (five arms in one flight) (the cell's single recovery re-registration)

The predecessor attempt was killed by a Windows Update forced restart of the host (System event log 1074: 15:29Z MoUsoCoreWorker "operating system: Service Pack (planned)", 15:33Z TrustedInstaller "operating system: upgrade (planned)"). The trace sink buffers until the seal, so the attempt left no trace and the E10 mode-A resume has nothing to replay; the column flight is re-flown WHOLE under the rec1 ids. The smoke cell sealed at 2026-10-14T12:16Z, was signed off at 12:18:33Z and is NOT re-flown.

RECOVERY 2026-10-14 (the cell's single one; owner decision 309 A, coordinator brief, Fable 5.1). The generation budget is run-cumulative across the attempts of the run id (core/model/adapter.py; every attempt state counts, an OPENED one included), so the rec1 plan carries the original plan plus the failed attempt's recorded spend (1,204 calls, 3298.26 speech-seconds, read from the attempt record into docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/predecessor-snapshot-arm-rec1-v1.json). The FIT cap is structural and unchanged (rows x program contacts x endpoints per contact). The FIT run id and the FIT attempt id both take the rec1 marker because the cell is re-flown whole and a (run_id, attempt_id) pair is a one-time key; the generation run id is unchanged. The registered GPU-hour ceiling does not change.

- Failed attempt: `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-v1` (OPENED at flight commit 37e177e3e from 2026-10-14T12:18:45Z, killed by a host restart at 15:29Z; 1,204 calls / 3298.26 speech-seconds realised per its attempt record (reserved 17,280 / 50,477); no trace was written (the run directory holds only the session-attach receipt); preserved unread.)
- Root cause: infrastructure, not the cell: a Windows Update forced restart (System event log 1074) killed the host session; no defect in the cell, the runtime or any registered knob.
- Fix: none in the cell; infrastructure: the Windows Update auto-restart policy is set (decision 310 A) and the data-disk mount task is fixed (decision 311)
- Re-flown whole under generation attempt `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1` and FIT run `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-REC1-V1` / attempt `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-fit-rec1-v1`; the generation run id `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1` is unchanged; the decision receipt is re-minted with the rec1 FIT run id.
- Run-cumulative plan budget: 17280 + 1204 = 18484 calls; 50477 + 3298.26 = 53776 speech-seconds; the FIT cap stays structural.
- Plans: `generation-plan-registered-rec1-v1.json`, `fit-plan-registered-rec1-v1.json` (the first-attempt plan files are superseded and removed from the package; the git history keeps them, and the failed attempt stays on the data root).
- Unchanged: the smoke cell `slurp-native-stage3-nxt-r1-thinking-policy-fold-b-smoke-4-v1` (sealed, signed off, not re-flown; its baseline, experiment, ids and attempt are untouched) and every registered knob, arm, policy, roster, prompt, geometry, cap and the 41.4 GPU-hour ceiling of the arm cell.
- A second failure closes the cell; the fix is proven on a four-row dry run.
