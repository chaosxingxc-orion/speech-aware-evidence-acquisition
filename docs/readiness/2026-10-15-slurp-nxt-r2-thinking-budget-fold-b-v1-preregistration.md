# NX-T R2: the per-node reasoning-budget column, preregistration (DRAFT / HELD)

Registered 2026-10-15 at study commit `3b08bbd533a35d9726dd9be8019a98164fbacaff` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1` / `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-FIT-REC1-V1`; `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-NXT-R2-THINKING-BUDGET-FOLD-B-READ-V1`.

The node words and the read rule are in `docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1/README.md`.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows prove FORM only: the phase-native-module-v1-c6 module program with 3 arms loads on the Thinking session, each arm's requests carry their own reasoning budget and reserve at the unchanged cap, the forced close fires earlier at a lower budget, the live phase fit passes and the v5 receipt seals. Scored by no one; four rows claim nothing under instrument rule 5.",
      "primary_metric": "none (structural form, per-arm per-node decode cost and the forced-close behaviour only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1": {
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "same-flight-node-column",
      "note": "A per-node cost attribution, not a benefit claim: the question is how much reasoning each node needs, so the expected effect of a cheaper budget is 0.0 pp SLU-F1 (no resolvable loss) and the deliverable is the saving (the throughput table). NO twin flies (owner decision 313 A): the null is the DECLARED same-core A/A offset |o| = 1.15 pp SLU (the larger of the two measured offsets, 268-B +1.15 and P3.1 -0.61) with the paired floor 0.7 pp; the design resolves a per-arm contrast of 1.49 pp SLU / 0.65 pp intent at n = 1,080 (decision 190 node-column floors), which are also the no-resolved-loss margins.",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "primary_metric_key": "slu",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 1080,
      "template_variants": {
        "candidate_arms": 2,
        "node": "perception",
        "twin": false
      },
      "tuning_roster": "none",
      "variant_cost": {
        "extra_audio_seconds": 12619.19,
        "extra_contacts_per_row": 4
      },
      "variant_kind": "thinking-budget"
    }
  }
}
```

## Recovery rec1: the reasoning-budget column flight (3 arms in one flight) (the cell's single recovery re-registration)

The owner rebooted the laptop at about 2026-10-17 12:52Z while the column attempt was open (opened 12:40:36Z; 42 calls / 6 checkpointed rows realised); the batch driver, the flight and the resident llama-server died with the host, the attempt record stays OPENED and the data-root state (checkpoint, session-attach receipt) is intact and preserved unread.

RECOVERY 2026-10-17T13:00:09Z (the cell's single one; coordinator decision under owner rulings 318 A / 327 A and the owner's 2026-10-17 directive to keep the GPU queue running; the smoke stays sealed and signed off; the chain segment is arm-only). The generation budget is run-cumulative across the attempts of the run id (core/model/adapter.py; every attempt state counts, an OPENED one included), so the rec1 plan carries the original plan plus the failed attempt's recorded spend (42 calls, 132.099 speech-seconds, read from the attempt record into docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1/predecessor-snapshot-arm-rec1-v1.json). The FIT cap is structural and unchanged (rows x program contacts x endpoints per contact). The FIT run id and the FIT attempt id both take the rec1 marker because the cell is re-flown whole and a (run_id, attempt_id) pair is a one-time key; the generation run id is unchanged. The registered GPU-hour ceiling does not change.

- Failed attempt: `attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-v1` (OPENED; 42 calls / 132.10 speech-seconds realised per its attempt record (reserved 11,880 / 34,703); preserved unread.)
- Root cause: Host restart (owner action), not a harness or serving defect: no error in the chain, driver or campaign logs before the cut; the stale flight.lock was parked after confirming no live process..
- Fix: None required in code. The cell is re-flown WHOLE under the rec1 ids (the registered single-recovery form of this package: a (run_id, attempt_id) pair is a one-time key); the six checkpointed rows are not resumed because the package registers the whole re-fly form and the saving would be about ten minutes.
- Re-flown whole under generation attempt `attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-rec1-v1` and FIT run `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-FIT-REC1-V1` / attempt `attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-fit-rec1-v1`; the generation run id `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1` is unchanged; the decision receipt is re-minted with the rec1 FIT run id.
- Run-cumulative plan budget: 11880 + 42 = 11922 calls; 34703 + 132.099 = 34836 speech-seconds; the FIT cap stays structural.
- Plans: `generation-plan-registered-rec1-v1.json`, `fit-plan-registered-rec1-v1.json` (the first-attempt plan files are superseded and removed from the package; the git history keeps them, and the failed attempt stays on the data root).
- Unchanged: the smoke cell (sealed, signed off, not re-flown) and every registered knob, arm, policy, roster, prompt, geometry, cap and the GPU-hour ceiling of the arm cell.
- A second failure closes the cell; the fix is proven on a four-row dry run.
