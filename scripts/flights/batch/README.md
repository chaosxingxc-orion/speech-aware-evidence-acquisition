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
| `serving_swap.sh <slurp-np4\|a2t-np3\|e21-np4\|det-np1> [--dry-run]` | THE geometry swap (owner decision 163): swap lock + pending marker, precise generation-flight check, resident session mapped onto the geometry table, host-memory pre-check BEFORE the stop (`serving_session.sh host-memory`, guard 12.0 GB + 0.5 GB margin), clean stop + port 8080 verified free, the Windows tasks stopped/started through `saea_task.ps1 -Start` over WSL interop, the monitor 20 s later, the strict wait, restore of the previous geometry on any failure after the stop, one final JSON summary line (also appended to `/home/chao/serving-swap.jsonl`). Exit 0 swapped/no-op, 7 flight, 8 host memory, 9 swap lock, 10 resident state, 11 stop failed, 12 restored, 13 unrestored |
| `serving_wait_ready.sh <target> [--since EPOCH]` + `serving_ready_probe.py` | the strict readiness wait: fresh `session.json` of this start, no stop record, `/health` ok, `/props` slot geometry equal to the fragment, a fresh monitor sample; exit 0 only when READY (2 timeout, 3 stopped early, 4 wrong geometry). `slurp_wait_ready.sh`, `a2t_wait_ready.sh`, `e21_wait_ready.sh` are thin callers |
| `serving_lib.sh` | the geometry table (session id, fragment, task names, entry scripts, log globs per target) and the shared predicates: precise generation-flight detection (`core.flight.cli campaign\|worker`, `batch_driver.sh`, `lease_cli`, `flight.lock` -- never a model-free `prepare-supply`/`check`), CPU sidecars, the swap pending marker, and the decision-162 sidecar admission used by `prep_generic_task_entry.sh` and `prep_test_sample.sh` (refuse a CPU sidecar unless a GPU session is resident and running and no swap is pending) |
| `queue_lib.sh` | the unattended-queue pattern as functions (`ql_init`, `ql_commit`, `ql_wait_driver_start`, `ql_wait_terminal`, `ql_halt_on_stop`, `ql_swap`, `ql_chain`, `ql_wait_sidecars_gone`); every function returns the real exit status -- see the ten-line example in its header |
| `repin_cell_generic.sh`, `rprim_repin_smoke.sh`, `rprim_repin_arm.sh`, `rprim_flip_both.sh`, `batch_chain_rprim.sh` | the per-cell re-pin flip (environment-parameterised) with the R-PRIM callers, and the R-PRIM queue chain (smoke, then the 1,080-row arm) |
| `lease_reconcile_e35.sh` | the flight-lock quiescence receipt + move-aside after an abort (never deletes `generation.guard`) |
| `repin_loop_generic.sh`, `b1_check_summary.py` | the readiness flip loop around `scripts/flights/repin_cell.py` |
| `adv1_prepare.sh`, `adv1_prepare_steps.py` | Stage-3 S3-3 on the sealed cell ROLL-1 plus the ADV-1 registration fills: score copies, best/worst pairs, the disagreeing-row construction roster receipt, the `populations` block and the placeholder substitution (`ADV1_DRY=1` by default) |
| `adv1_to_deltas.sh`, `adv1_to_deltas_steps.py` | Stage-3 S3-5 after the ADV-1 seal: curate the append-only delta store, build its derangement twin, materialise both release registrations from their committed templates, release both stores and fill CELL-1 (`DELTAS_DRY=1` by default) |
| `roll1_fill_placeholders.py` | the placeholder substitution tool (`--fragments`, `--occurrence-policy`; the default is cell ROLL-1's two baselines under the exactly-once rule) |
| `e35_check.sh`, `e35_rehash.py`, `e35_done_wait.sh`, `b6_read.sh`, `b9arec_read.sh`, `b9arec_acquisition_read.py`, `e36b_replay.py` | the model-free registration re-hash, flight checks and stage reads used in the 2026-09-22 seal flights |

Paths inside are absolute WSL paths of this machine (the study checkout on `/mnt/d`, the data root on `/mnt/e`, the runtime
root `/home/chao`); they are operations scripts, not library code, and are excluded from the engineering-base line budget.

## Serving lifecycle rules (owner decisions 162 and 163)

- A geometry swap is ONE command, `bash scripts/flights/batch/serving_swap.sh <target>`, run from WSL; never a WSL switch
  script plus a separate Windows task switch. Dry-run first when in doubt (`--dry-run` prints the plan and every
  precondition verdict and acts on nothing). The four `serving_switch_*.sh` scripts remain for the queues that call them
  and now carry the same precise flight check and the host-memory pre-check before their stop.
- A CPU sidecar (the 8081 packet preprocess) starts only while a GPU session is resident and running and no swap is
  pending; the preparation launchers refuse otherwise (exit 10). A swap refuses (exit 8) instead of stopping the running
  geometry when the host reading proves the next start would fail its 12 GB guard, and names the sidecar holding memory.
- A readiness wait exits 0 only on READY; a queue records every exit status (`rc=0; cmd || rc=$?`) and halts on a STOP.
