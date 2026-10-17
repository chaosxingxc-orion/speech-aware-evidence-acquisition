# NX-T R1: the per-node thinking-policy column, preregistration (DRAFT / HELD)

Registered 2026-10-17 at study commit `5acfbc38b` by script. Development numbers only.

Runs: `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1` / `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-REC2-V1`; `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1`.

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

## Recovery rec2: the thinking-policy column flight (five arms in one flight) (the cell's rec2 re-registration, under an explicit owner exception to the one-recovery rule)

The rec1 column attempt stopped on a HARNESS defect, not on the infrastructure: after 1,029 complete rows the next row's `both-off` arm sealed a no-think Solver contact that ended on finish_reason `length` at its 1,024-token cap, and the fan-out raised before the delivering arm ran on that row. The absent-arm fix is merged on master (60134738e). Owner ruling 320 B of 2026-10-16 grants an EXPLICIT exception to the package rule of one recovery re-registration per run id: this rec2 keeps the 1,029 complete rows of the stopped attempt by mode-A trace replay and flies the 51 remaining rows (the failing row included) under the fix.

RECOVERY 2026-10-16 (rec2; owner ruling 320 B of 2026-10-16, coordinator brief, Fable 5.1). MODE A (trace replay), not mode B: the absent-arm fix changes rails/runner.py and a checkpoint resume refuses a code-identity change. `resume_from` names the rec1 attempt and the sha256 of its trace, 3238cd8aedb50c8a142b15e321070ffc7cf2cd055088fdcb0aee83d8a0895835 (667,787,659 bytes), read from the data root into docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/predecessor-snapshot-arm-rec2-v1.json. The attempt keeps the 1,029 complete rows (each replayed through the seal under the current code; the offline replay proof is a block of the generation plan) and flies the 51 remaining rows: 51 x 10 = 510 program contacts and nothing else. The generation budget is run-cumulative across the attempts of the run id (core/model/adapter.py): the registered plan plus both earlier attempts' recorded spend (11,502 calls, 33399.5 speech-seconds, read from the attempt records into docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/predecessor-snapshot-arm-rec1-v1.json and docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/predecessor-snapshot-arm-rec2-v1.json). The FIT cap is structural and unchanged. The FIT run id and the FIT attempt id take the rec2 marker because a (run_id, attempt_id) pair is a one-time key; the generation run id is unchanged. The registered GPU-hour ceiling (41.4 GPU-h) stands; the resume is expected to spend about 1.5 GPU-h (51 rows x 3.25 full-row equivalents / 1.84 rows per minute). `--allow-output-change` is never passed: the rebuilt supply, the roster (1,080 rows) and the read (n = 1,080) are the registered ones.

- Earlier attempt: `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-v1` (OPENED); recorded spend 1204 calls / 3298.26 speech-seconds
- Earlier attempt: `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1` (ABORTED); recorded spend 10298 calls / 30101.2 speech-seconds
- Immediate predecessor (the stopped attempt): `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1` (ABORTED (its attempt record), flight commit 8f9d8e1ee, started 2026-10-14T17:14:43Z, stopped 2026-10-15T22:33:00Z on the finite completion above; 10,298 calls / 30101.20 speech-seconds realised per its attempt record (reserved 18,484 / 53,776); 1,029 complete rows in the trace (sha256 3238cd8a...) and in the row checkpoint; the failing row's records were never flushed; preserved unread.)
- Root cause: the no-think finite completion on a candidate arm: the `both-off` arm's no-think Solver contact (cap 1,024 tokens) ended on finish_reason `length`, FrozenCoreRoleFiniteCompletionError left the branch fan-out so the delivering arm never ran on that row, and the level-2 fold found no Solver record for the arm (RailsRunnerError: perception branch 'both-off' sealed no level-2 Solver column); the first such event in 2,058 earlier no-think Solver contacts (longest 66 tokens).
- Fix: the merged absent-arm fix (commit 60134738e): a finite completion on a NON-delivering branch is recorded as `solver_absent` with an `absent_reason` (optional receipt keys, schema unchanged) and the fan-out continues so the delivering arm runs; the renderer scores an absent column as the canonical empty answer; both column readers print `absent_rows` per arm; a finite completion on the DELIVERING arm still aborts by design
- Resumed in mode A (trace replay) from `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1`: the 1,029 complete rows are kept and the 51 remaining rows (the failing row included) are flown under generation attempt `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec2-v1` and FIT run `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-FIT-REC2-V1` / attempt `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-fit-rec2-v1`; the generation run id `SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1` is unchanged; the decision receipt is re-minted with the rec2 FIT run id.
- Run-cumulative plan budget: 17280 + 11502 = 28782 calls; 50477 + 33399.5 = 83877 speech-seconds; the FIT cap stays structural.
- Plans: `generation-plan-registered-rec2-v1.json`, `fit-plan-registered-rec2-v1.json` (the earlier plan files (the first attempt and every earlier rec) are superseded and removed from the package; the git history keeps them, and the earlier attempts stay on the data root).
- Owner exception: owner ruling 320 B of 2026-10-16; no further recovery is covered by it.
- Unchanged: the smoke cell `slurp-native-stage3-nxt-r1-thinking-policy-fold-b-smoke-4-v1` (sealed, not re-flown) and every registered knob, arm, policy, roster (1,080 rows), prompt, geometry, cap, the program phase-native-module-v1-c10 and the 41.4 GPU-hour ceiling of the arm cell.
- Resume accounting: kept 1,029 rows (replayed from `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1`, kept-row id hash 461092f79ed1c76b93124ae443affb1799bec19e92429099af51c05874f55a01); flown 51 rows (0 partial, 51 never started; the failing row is among them), 510 program contacts. An arm whose Solver contact ends on a finite completion is an ABSENT column (`solver_absent`), scored as the canonical empty answer; the read reports kept / flown / absent counts per arm beside the arm columns. Owner ruling 320 B of 2026-10-16 covers this one re-registration only.
- A third recovery is not covered by the owner exception; a second failure of rec2 closes the cell, and the fix is proven on a four-row dry run.
