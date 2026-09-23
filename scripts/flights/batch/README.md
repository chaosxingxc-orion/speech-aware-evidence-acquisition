# Batch driver family (coordinator operations; promoted from the session scratchpad on 2026-09-22)

Owner decision 77: every GPU flight runs unattended under a Windows Scheduled Task that owns one WSL process, independent of
any Claude Code session. These scripts are that machinery. They lived in a session scratchpad until 2026-09-22, when a
session restart wiped it mid-campaign; from now on they live here and every scheduled task points at this directory.

| script | role |
| --- | --- |
| `saea_task.ps1` | register / start / stop / query one scheduled task (`-Name`, `-Script <wsl path>`, `-Status`, `-Stop`); battery and idle conditions off, no time limit |
| `batch_driver.sh` | the unattended queue driver: `/home/chao/batch-queue.json` steps, `batch-status.jsonl` events, `batch-STOP` on first failure, `batch-done` at the end; `BATCH_SESSION` selects the resident session |
| `batch_inspect.py` | structural acceptance of a sealed smoke or arm (attempt FINALIZED, manifest COMPLETED at the flight commit, rows, ceilings, tool surface, one score job) |
| `gpu_ramp_test.sh` | the non-model GPU preflight (fp16 matmul burst; refuse below 30 TFLOP/s) |
| `batch_driver_task.sh`, `batch_chain_*.sh` | scheduled-task entry points: pin the batch flight worktree at a flight commit, write the queue, run the driver |
| `serving_task_entry*.sh`, `serving_monitor_start*.sh`, `serving_switch_to_e21.sh`, `e21_wait_ready.sh` | the resident serving sessions per geometry (SLURP np4; E21 cddb000c np4 max1024) and their monitors |
| `serving_switch_to_slurp.sh`, `slurp_wait_ready.sh` | the reverse geometry switch after the E35 seal (stop the E21 session, then the SLURP tasks restart from Windows) and its readiness wait |
| `repin_cell_generic.sh`, `rprim_repin_smoke.sh`, `rprim_repin_arm.sh`, `rprim_flip_both.sh`, `batch_chain_rprim.sh` | the per-cell re-pin flip (environment-parameterised) with the R-PRIM callers, and the R-PRIM queue chain (smoke, then the 1,080-row arm) |
| `lease_reconcile_e35.sh` | the flight-lock quiescence receipt + move-aside after an abort (never deletes `generation.guard`) |
| `repin_loop_generic.sh`, `b1_check_summary.py` | the readiness flip loop around `scripts/flights/repin_cell.py` |
| `adv1_prepare.sh`, `adv1_prepare_steps.py` | Stage-3 S3-3 on the sealed cell ROLL-1 plus the ADV-1 registration fills: score copies, best/worst pairs, the disagreeing-row construction roster receipt, the `populations` block and the placeholder substitution (`ADV1_DRY=1` by default) |
| `adv1_to_deltas.sh`, `adv1_to_deltas_steps.py` | Stage-3 S3-5 after the ADV-1 seal: curate the append-only delta store, build its derangement twin, materialise both release registrations from their committed templates, release both stores and fill CELL-1 (`DELTAS_DRY=1` by default) |
| `roll1_fill_placeholders.py` | the placeholder substitution tool (`--fragments`, `--occurrence-policy`; the default is cell ROLL-1's two baselines under the exactly-once rule) |
| `e35_check.sh`, `e35_rehash.py`, `e35_done_wait.sh`, `b6_read.sh`, `b9arec_read.sh`, `b9arec_acquisition_read.py`, `e36b_replay.py` | the model-free registration re-hash, flight checks and stage reads used in the 2026-09-22 seal flights |

Paths inside are absolute WSL paths of this machine (the study checkout on `/mnt/d`, the data root on `/mnt/e`, the runtime
root `/home/chao`); they are operations scripts, not library code, and are excluded from the engineering-base line budget.
