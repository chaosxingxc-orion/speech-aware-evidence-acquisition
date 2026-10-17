# NX-T R2: the per-node reasoning-budget column, preregistration (DRAFT / HELD)

Registered 2026-10-15 at study commit `3b08bbd533a35d9726dd9be8019a98164fbacaff` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1` / `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-FIT-REC2-V1`; `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-NXT-R2-THINKING-BUDGET-FOLD-B-READ-V1`.

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

## Recovery rec2: the reasoning-budget column flight (3 arms in one flight) (the cell's rec2 re-registration, under an explicit owner exception to the one-recovery rule)

The rec1 column attempt was ABORTED on 2026-10-17 at about 13:42Z by a coordinator action, not by the cell: registering the serving task SAEA-Serving-THINKB7 for the next flight started a second server, the serving entry's start-up reaper killed the resident THINKB server under the open flight, the driver saw "Remote end closed connection" on a Solver contact and aborted the attempt at 172 calls / 481.5 speech-seconds with its complete rows checkpointed and its trace present. Owner ruling 328 of 2026-10-17 grants an EXPLICIT exception to the package rule of one recovery re-registration per run id and rules that a stopped attempt is RESUMED, never re-flown whole, whenever a checkpoint or trace exists: this rec2 keeps the 26 complete rows of the stopped rec1 attempt by a mode-A resume and flies the 1,054 remaining rows.

RECOVERY 2026-10-17 (rec2; owner ruling 328 of 2026-10-17, coordinator brief on the owner's message, translated from Chinese: just resume from the checkpoint). MODE A (trace replay), not mode B: the runtime, runner and row_checkpoint modules are byte-identical between the rec1 flight commit 9790c071f and this registration, but the launch-time checkpoint reader refuses the rec1 checkpoint for the rec2 attempt: row checkpoint $SPEECHRL_DATA_DIR/runs/SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1/attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-rec1-v1/SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1.rows.ckpt.jsonl was written for protocol_hash 'f30958b8ade762b6cf9ccf090d90313d164d5f309547978c30b9a129d6e109ac', not '87c8551b7674ad9c9dd89970366263a9589b9536bd9cb44a133c4ae04e7fdb9c'; a resume applies only when the code, config and split are unchanged. The protocol hash covers the whole experiment fragment, including the cell's attempt id, so a new attempt id of the same cell can never present the header's protocol hash (f30958b8ade7... against the rec2 87c8551b7674...). The trace pin has no such binding and its complete-row set equals the checkpoint's (same kept-row id hash). `resume_from` names the rec1 attempt and the sha256 of its trace, add8fb93cd4096787e5ae559c3374ec77edff4f9145499ecf986c4c458473813 (10,810,021 bytes), read from the data root into docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1/predecessor-snapshot-arm-rec2-v1.json. The attempt keeps the 26 complete rows (each is proven by the offline replay recorded as a block of the generation plan) and flies the 1,054 remaining rows: 1,054 x 6 = 6,324 program contacts and nothing else. The generation budget is run-cumulative across the attempts of the run id (core/model/adapter.py): the registered plan plus both earlier attempts' recorded spend (214 calls, 613.647 speech-seconds, read from the attempt records into docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1/predecessor-snapshot-arm-rec1-v1.json and docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1/predecessor-snapshot-arm-rec2-v1.json). The FIT cap is structural and unchanged. The FIT run id and the FIT attempt id take the rec2 marker because a (run_id, attempt_id) pair is a one-time key; the generation run id is unchanged. The registered GPU-hour ceiling (31.3 GPU-h) stands; the resume is expected to spend about 23.5 GPU-h (1,054 rows x 2.46 full-row equivalents / 1.84 rows per minute). `--allow-output-change` is never passed: the rebuilt supply, the roster (1,080 rows) and the read (n = 1,080) are the registered ones.

- Earlier attempt: `attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-v1` (OPENED); recorded spend 42 calls / 132.099 speech-seconds
- Earlier attempt: `attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-rec1-v1` (ABORTED); recorded spend 172 calls / 481.548 speech-seconds
- Immediate predecessor (the stopped attempt): `attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-rec1-v1` (ABORTED (its attempt record); 172 calls / 481.55 speech-seconds realised per its attempt record (reserved 11,922 / 34,836); 26 complete rows in its row checkpoint (sha256 fe96736b...) and its trace (sha256 add8fb93...); 4 partial row(s) in the trace were never completed; preserved unread.)
- Root cause: A coordinator error, not a harness, serving-geometry or owner action: the serving-task registration helper registers AND starts a task and the serving entry script's unscoped start-up reaper killed the resident server of the open flight; the harness behaved as designed (a lost server aborts the attempt).
- Fix: None required in code: the harness is unchanged between the rec1 flight commit 9790c071f and this registration for the modules a checkpoint resume compares. The standing rules from the incident: no serving or monitor task is registered or started while a flight is open, and serving tasks are created only by scripts/flights/batch/serving_swap.sh.
- Resumed in mode A (trace replay) from `attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-rec1-v1`: the 26 complete rows are kept and the 1,054 remaining rows are flown under generation attempt `attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-rec2-v1` and FIT run `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-FIT-REC2-V1` / attempt `attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-fit-rec2-v1`; the generation run id `SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1` is unchanged; the decision receipt is re-minted with the rec2 FIT run id.
- Run-cumulative plan budget: 11880 + 214 = 12094 calls; 34703 + 613.647 = 35317 speech-seconds; the FIT cap stays structural.
- Plans: `generation-plan-registered-rec2-v1.json`, `fit-plan-registered-rec2-v1.json` (the earlier plan files (the first attempt and every earlier rec) are superseded and removed from the package; the git history keeps them, and the earlier attempts stay on the data root).
- Owner exception: owner ruling 328 of 2026-10-17; no further recovery is covered by it.
- Unchanged: the smoke cell `slurp-native-stage3-nxt-r2-thinking-budget-fold-b-smoke-4-v1` (sealed, not re-flown) and every registered knob, arm, policy, roster (1,080 rows), prompt, geometry, cap, the program phase-native-module-v1-c6 and the 31.3 GPU-hour ceiling of the arm cell.
- Resume accounting: kept 26 rows (from `attempt-slurp-native-stage3-nxt-r2-thinking-budget-fold-b-generation-rec1-v1`, kept-row id hash d7f17639ee8afb68c2a403d3f082cdda9c787f69a9d61c9a6315b8fb7a4ca1b9); flown 1,054 rows (4 partial, 1,050 never started), 6,324 program contacts. The read reports kept / flown counts beside the arm columns. Owner ruling 328 of 2026-10-17 covers this one re-registration only.
- A third recovery is not covered by the owner exception; a second failure of rec2 closes the cell, and the fix is proven on a four-row dry run.
