# Batch driver family (coordinator operations; promoted from the session scratchpad on 2026-09-22)

Owner decision 77: every GPU flight runs unattended under a Windows Scheduled Task that owns one WSL process, independent of
any Claude Code session. These scripts are that machinery. They lived in a session scratchpad until 2026-09-22, when a
session restart wiped it mid-campaign; from now on they live here and every scheduled task points at this directory.

| script | role |
| --- | --- |
| `saea_task.ps1` | register / start / stop / query one scheduled task (`-Name`, `-Script <wsl path>`, `-Status`, `-Stop`, `-Start`, `-RepeatMinutes N` for a recurring trigger); battery and idle conditions off, no time limit |
| `idle_watchdog.sh`, `idle_watchdog_select.py`, `idle_watchdog_recovery.py`, `ready_chains.json` | the idle watchdog (owner decision 182), including its server-death-STOP and uptime-restart recovery rules: see "Idle watchdog" below |
| `batch_driver.sh` | the unattended queue driver: `/home/chao/batch-queue.json` steps, `batch-status.jsonl` events, `batch-STOP` on first failure, `batch-done` at the end; `BATCH_SESSION` selects the resident session; `prelaunch` refuses a step unless `scripts/checks/flight_registration_check.py` passes on its arm, smoke and campaign-plan cells (owner decision 163: rows root countersigned, decision receipt present with the run ids eligible, READ run id declared and registered), and, scoped to a step whose experiment config declares `resume_from` on its cell (`resume_gate_lib.sh`'s `resume_gate_run`, a no-op for every other step), also refuses unless `resume_prelaunch_gate.sh` passes (see "Registration field: resume_replay_proof" below) |
| `resume_prelaunch_gate.sh`, `resume_gate_lib.sh` | the resume prelaunch gate (coordinator, after the COMP-1 resume attempt 3 seal abort): `resume_prelaunch_gate.sh` wraps `scripts/checks/resume_prelaunch_gate_check.py`, which reads a named cell's `resume_from`, verifies every predecessor trace hashes to its declared identity, and runs `scripts/analysis/replay_seal_consistency.py` over every predecessor under the CURRENT code, refusing (non-zero, naming the failing row count and check names) if any row fails or is sealed twice; `resume_gate_lib.sh` is the scoping library `batch_driver.sh` sources (`resume_gate_declared`, `resume_gate_run`) so the driver and `scripts/flights/comp1/batch_chain_comp1_resume.sh` (which also calls the gate directly, right before the driver) share one rule |
| `batch_inspect.py` | structural acceptance of a sealed smoke or arm (attempt FINALIZED, manifest COMPLETED at the flight commit, rows, ceilings, tool surface, one score job) |
| `gpu_ramp_test.sh` | the non-model GPU preflight (fp16 matmul burst; refuse below 30 TFLOP/s) |
| `batch_driver_task.sh`, `batch_chain_*.sh` | scheduled-task entry points: pin the batch flight worktree at a flight commit, write the queue, run the driver |
| `serving_task_entry*.sh`, `serving_monitor_start*.sh`, `serving_switch_to_e21.sh`, `e21_wait_ready.sh` | the resident serving sessions per geometry (SLURP np4; E21 cddb000c np4 max1024) and their monitors |
| `serving_switch_to_slurp.sh`, `slurp_wait_ready.sh` | the reverse geometry switch after the E35 seal (stop the E21 session, then the SLURP tasks restart from Windows) and its readiness wait |
| `serving_swap.sh <slurp-np4|a2t-np3|e21-np4|det-np1|think-np4>\|a2t-np3\|e21-np4\|det-np1> [--dry-run] [--restart]` | THE geometry swap (owner decision 163): swap lock + pending marker, precise generation-flight check, resident session mapped onto the geometry table, host-memory pre-check BEFORE the stop (`serving_session.sh host-memory`, guard 12.0 GB + 0.5 GB margin), clean stop + port 8080 verified free, the Windows tasks stopped/started through `saea_task.ps1 -Start` over WSL interop, the monitor 20 s later, the strict wait, restore of the previous geometry on any failure after the stop, one final JSON summary line (also appended to `/home/chao/serving-swap.jsonl`). `--restart` (owner decision 182, added for the idle watchdog) turns the "already resident" fast path into a real stop+start of the same geometry instead of a readiness-only no-op. `--stop-only` (no target) stops whatever is resident and leaves the card EMPTY, and `<target> --start-only` starts the target only on an empty card (a different resident geometry refuses, exit 10): the pair brackets a GPU window in which the card must hold no server (the Thinking packet encoder pass, `scripts/flights/direct/direct_fb_packets_gpu.sh`); neither mode restores, the caller owns the restore. Exit 0 swapped/no-op, 7 flight, 8 host memory, 9 swap lock, 10 resident state, 11 stop failed, 12 restored, 13 unrestored |
| `serving_wait_ready.sh <target> [--since EPOCH]` + `serving_ready_probe.py` | the strict readiness wait: fresh `session.json` of this start, no stop record, `/health` ok, `/props` slot geometry equal to the fragment, a fresh monitor sample; exit 0 only when READY (2 timeout, 3 stopped early, 4 wrong geometry). `slurp_wait_ready.sh`, `a2t_wait_ready.sh`, `e21_wait_ready.sh` are thin callers |
| `serving_lib.sh` | the geometry table (session id, fragment, task names, entry scripts, log globs per target) and the shared predicates: precise generation-flight detection (`core.flight.cli campaign\|worker`, `batch_driver.sh`, `lease_cli`, `flight.lock` -- never a model-free `prepare-supply`/`check`), CPU sidecars, the swap pending marker, and the decision-162 sidecar admission used by `prep_generic_task_entry.sh` and `prep_test_sample.sh` (refuse a CPU sidecar unless a GPU session is resident and running and no swap is pending) |
| `queue_lib.sh` | the unattended-queue pattern as functions (`ql_init`, `ql_commit`, `ql_wait_driver_start`, `ql_wait_terminal`, `ql_halt_on_stop`, `ql_swap`, `ql_chain`, `ql_wait_sidecars_gone`, `ql_seg_line`); every function returns the real exit status -- see the ten-line example in its header. The OWNED filler hold (after the 2026-09-30 hold race): `ql_hold_take <owner> [<predecessor>]`, `ql_hold_release <owner>`, `ql_hold_owner` -- only the owner removes a hold, a successor takes it over from its named predecessor, and `ql_seg_line` matches a log line's message start, never a phrase quoted in a preamble |
| `queue_successor_template.sh` | the successor-queue template with the owned hold (take the hold over from the predecessor at its DONE, release only our own, restart the filler only when our release removed it) and, in its header, the safe swap of a corrected script in for a RUNNING queue (`.next` beside it, stop only in the step-1 wait, rename never rewrite) |
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

## Registration fields: tuning_roster / read_roster (item D3)

The AGREE agreement term (docs/results/2026-09-27-verdict-reclassification.md item D3) tuned its
weight grid on TRAIN Fold A gold and then read it on TRAIN Fold A -- a circular read. Every
Stage-3 cell's `stage3_measurement` block now names two facts, whatever its `measurement_design`:

- `tuning_roster` -- the roster id or sealed-pool id (or a list of them) that any weight,
  threshold, cap, template or knowledge selection of this cell was chosen on; the literal string
  `"none"` when nothing was tuned.
- `read_roster` -- the roster the cell is read on.

`scripts/checks/flight_registration_check.py` checks the split on every cell that declares the
block (not only the same-flight supply-variant design's merge-set-A fields):

- `tuning-roster-missing` (advisory) -- the block is present but one of the two fields is absent.
- `tuning-roster-unverified` (advisory) -- both fields are present and distinct, but no roster
  receipt under `docs/receipts/rosters/` proves them disjoint (no receipt found for one of them, or
  its `disjointness_proof` says nothing about the other).
- `tuning-read-overlap` (**blocking** on a live, unflown cell) -- `tuning_roster` names the
  `read_roster` directly, or a named roster's own `disjointness_proof` proves shared recordings or
  utterances with the other roster.

A sealed / already-flown cell is never blocked by any of the three (this repository does not
rewrite sealed bytes or their registrations); the findings are still reported against it.

## Registration field: resume_replay_proof

Coordinator ruling after the COMP-1 resume attempt 3 seal abort: a four-row dry-run smoke cannot
see the seal-time consistency checks a resume-recovery's KEPT rows must still pass under the
CURRENT code -- the abort itself was exactly this (a harness change the smoke never exercised).
So a cell that declares `resume_from` must carry, in its own readiness package's
`*plan-registered*.json`, a `resume_replay_proof` block naming every one of:

- `rows_checked` -- total rows the checker replayed across every declared predecessor;
- `rows_failing` -- rows that failed a seal-time consistency check (must be `0`);
- `sealed_twice` -- rows sealed by more than one declared predecessor (must be `0`);
- `checker_sha256` -- the SHA-256 of the exact `scripts/analysis/replay_seal_consistency.py` that
  ran;
- `code_commit` -- the study commit the replay ran under.

Mint this block by running `scripts/flights/batch/resume_prelaunch_gate.sh --repo-root REPO
--data-root DATA --experiment EXP --cell CELL` (or the checker it wraps,
`scripts/checks/resume_prelaunch_gate_check.py`) before registering the cell: on success it
prints exactly this block (schema `saea-resume-replay-proof-v1`) as JSON, ready to paste into the
package's registered-plan facts beside `resume_from` and `resume_budget`.

`scripts/checks/flight_registration_check.py` checks for this block on every cell that declares
`resume_from`:

- `resume-replay-unproven` -- the block is missing, missing a field, or reports a failing or
  sealed-twice row. Advisory in tree mode (reported, never fails the whole-tree scan over
  paperwork not yet done); **BLOCKING** at launch (`--cell` / `--campaign-plan`, what
  `batch_driver.sh` runs) for a live, unflown resume cell.

This is the PAPERWORK half of the rule; `resume_prelaunch_gate.sh` is the LIVE half, run
automatically by `batch_driver.sh`'s `prelaunch` (scoped to a step whose experiment config
declares `resume_from`, via `resume_gate_lib.sh`) and directly by
`scripts/flights/comp1/batch_chain_comp1_resume.sh` right before the driver starts. Both must
pass; neither substitutes for the other -- the registration check proves the replay was already
run and recorded, the live gate re-runs it under whatever code is actually about to fly.

## Queue kind: seal-only (E10d; COMP-1 seal-only completion, 2026-09-29)

A resume cell whose `resume_from` LIST of predecessors already covers the whole roster flies nothing:
the runtime sets `is_seal_only`. Queue it as `"kind": "seal-only"` with `smoke_experiment`,
`smoke_cell` and `campaign_plan` all `null`. `batch_driver.sh` then refuses a seal-only step that
declares a smoke, a campaign plan, or a cell without `resume_from`; runs the ordinary `prelaunch`
(the serving-idle/healthy check still applies -- the resident session satisfies it and is never
touched -- then the registration gate on `--cell` and the resume replay gate over every declared
predecessor); runs `core.flight.cli seal-only --experiment EXP --cell CELL` (no session, lease or
slot; it seals the merged manifest and runs the one official finalize job); and inspects the
attempt as an arm (FINALIZED, every roster row, one score job, `study_commit` = the flight commit).
First user: `scripts/flights/comp1/batch_chain_comp1_sealonly.sh`.

## Idle watchdog (owner decision 182)

Row 182 (docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md): "Authorise an IDLE
WATCHDOG as an engineering-base item: a scheduled task that, every few minutes, when no
flight/driver/swap is alive, no STOP is live, the serving geometry is healthy or swappable, and a
registered ready-chain list names a next chain, launches that chain through the batch driver (row 77
unchanged: flights only through the driver), logging every decision?" Ruling: authorised. "The
watchdog never launches onto a STOP, never edits records, never starts a CPU sidecar, respects the
hold files, and its ready-chain list is a committed file the coordinator edits."

### `ready_chains.json` schema

A committed, ordered JSON object the coordinator edits by hand:

```json
{
  "allowed_carriers": ["slurp"],
  "chains": [
    {
      "name": "rankvis",
      "carrier": "slurp",
      "geometry": "slurp-np4|a2t-np3|e21-np4|det-np1|think-np4>",
      "chain_script": "scripts/flights/rankvis/batch_chain_rankvis.sh",
      "flight_commit_file": "/home/chao/rankvis-flight-commit.txt",
      "hold_file": null,
      "enabled": true,
      "note": "optional free text, logged when the entry is skipped or disabled",
      "ext4_copy_target": "optional: copy chain_script here before launching (the filler entry only)"
    }
  ]
}
```

- `allowed_carriers` -- the carriers the GPU may run right now (owner directive 2026-09-28: `["slurp"]`
  only, row 187). Every entry MUST declare a `carrier`; an entry without one, or whose carrier is not
  in this list, is skipped with a log line. An empty `allowed_carriers` list admits any declared
  carrier (used only by the test suite; production ships `["slurp"]`).
- `chains` is evaluated **in list order**; the watchdog launches the first entry that is `enabled`,
  whose `carrier` is allowed, whose `hold_file` (if given) is absent, and whose `flight_commit_file`
  either is `null` (no flight-commit gate at all -- the `filler` entry manages its own chunk commits
  internally through `filler_queue_decide.py`) or exists on disk, is non-empty, and does not already
  have a `batch-done` marker recorded for that exact commit (`/home/chao/batch-flight-commit.txt`
  equals the file's content AND `/home/chao/batch-done` is non-empty; a chain script archives both
  with a UTC timestamp suffix before it starts a new run -- see `batch_chain_roll3.sh` -- so a live,
  unarchived `batch-done` always names the commit that produced it).
- `geometry` is one of `slurp-np4|a2t-np3|e21-np4|det-np1|think-np4>` / `e21-np4` / `a2t-np3` (the `serving_swap.sh` targets this study
  currently flies; `det-np1` is not used by any ready-chain entry).
- `hold_file` is optional (`null` or omitted means no hold gates the entry).
- `ext4_copy_target` is optional: when set, the watchdog copies `chain_script` there before launching
  it, and launches the COPY instead of the main-checkout path. Only the `filler` entry needs this
  (`filler_queue.sh` loops for the length of an idle window; bash reads a script incrementally and the
  main checkout moves under a merge -- see the script's own header, and `queue_after_revtfrl.sh` step 5
  which does the same copy by hand).
- `note` is optional free text; it is appended to the "disabled" / skip log lines so a `git blame` on
  this file is not the only way to see why an entry is inert.

Shipped order (owner decisions 181-188): `rankvis -> wsv1 -> w4sv -> filler`, all `carrier: "slurp"`.
`e41-sub10` (the Earnings E41 sub10 re-read, `carrier: "earnings"`, `geometry: "slurp-np4|a2t-np3|e21-np4|det-np1|think-np4>"`) is kept in
the list, `"enabled": false`, annotated with the 2026-09-28 SLURP-only ruling (row 187); its flipped
cell stays ready at commit `bf6db903` for the owner to re-enable later by flipping `enabled` back to
`true` (`allowed_carriers` would then also need to include `"earnings"`). `wsv1` and `w4sv` (card
items W-SV-1 / W4-SV) name chain scripts and flight-commit files that do not exist yet; the watchdog
skips them with a log line, exactly like any other not-yet-flipped entry, until the coordinator lands
`scripts/flights/wsv1/batch_chain_wsv1.sh` / `scripts/flights/w4sv/batch_chain_w4sv.sh` and their
`/home/chao/{wsv1,w4sv}-flight-commit.txt` files.

### `idle_watchdog.sh`

Run as a Windows Scheduled Task (owner decision 77), one tick per invocation, idempotent and
single-instance (a PID lock file with a dead-pid check: an overlapping tick exits quietly instead of
queuing or racing a second one). On every tick, in order:

1. exit quietly if a flight/driver/swap/filler/queue process is already alive (`serving_lib.sh`'s
   `saea_flight_alive` / `saea_swap_pending`, plus `filler_queue.sh` and any
   `saea-queue/queue_*.sh` coordinator queue script);
2. `/home/chao/batch-STOP`: **never** launched onto, with one recovery carve-out (coordinator
   diagnosis, 2026-09-28 night: the resident llama-server died on a CUDA abort after 14.6 h, and the
   next resume attempt then STOPped on a urllib3 `RemoteDisconnected` / "Remote end closed
   connection" -- the SERVER was gone, not the experiment). A STOP is a SERVER-DEATH STOP only when
   its own text, or the log file its own `batch_driver.sh` "...; see &lt;path&gt;" message names,
   contains `RemoteDisconnected` or `Remote end closed connection` verbatim
   (`idle_watchdog_recovery.py` `classify_stop`; no other text ever qualifies) **and** the resident
   server's `/health` fails right now. Only then: the STOP is archived to a dated `.bak` next to it,
   logged once as "server-death STOP archived", and the tick falls through to the normal gates and
   selection below with a forced geometry restart (step 5b). Every other STOP exits quietly, logged
   once per STOP file content (an md5 of its bytes) so a long-lived STOP does not flood the log;
3. exit quietly if `/home/chao/saea-queue/watchdog.hold` exists (the coordinator's pause switch);
4. exit quietly if the study MASTER tree (never a worktree) is `git status --porcelain` dirty;
5. otherwise call `idle_watchdog_select.py` -- a pure, unit-tested function
   (`tests/unit/test_idle_watchdog.py`) -- for the next eligible `ready_chains.json` entry;
5b. UPTIME RESTART (coordinator, 2026-09-28 night): when the selected entry's geometry is already the
   resident one (`serving_session.sh resident` mapped onto the geometry table) and the resident
   server process has been up longer than `SAEA_WATCHDOG_MAX_UPTIME_SECONDS` (default 12 h -- the
   server that died was up 14.6 h; `ps -o etimes=` on the port-8080 pid), the geometry is
   force-restarted before launching (same mechanism as the server-death case, logged as
   "uptime restart"). Skipped when a server-death restart is already forced, or when the geometries
   differ (an ordinary swap already cycles the server in that case);
6. `--dry-run` stops here: it only logs and prints the decision (`DRY-RUN would launch '<name>' on
   <geometry> (commit <commit>, restart=0|1) via <chain_script>`) and archives, swaps or launches
   nothing;
7. otherwise: `serving_swap.sh <geometry> [--restart]` (a no-op only when already resident AND no
   restart was called for; a failure refuses the launch and changes nothing else), the optional
   `ext4_copy_target` copy, then `saea_task.ps1 -Name SAEA-Watchdog-Chain -Script <chain_script>
   -Start` -- the SAME mechanism `serving_swap.sh` uses to start a serving task -- so the chain's own
   batch driver, registration gate and flight-worktree checkout apply exactly as they do when a
   coordinator queue launches it by hand. The watchdog exits immediately once the launch call
   returns; the chain then runs for its own (possibly hours-long) duration under its own scheduled
   task, independent of this tick.

Every decision is logged to `/home/chao/watchdog.out` with UTC timestamps (`queue_lib.sh`'s `ql_say`).
It never edits a record other than the one STOP-archival case above (and only for a STOP it has
itself proven is a dead server, never a real failure), never starts a CPU sidecar, and never touches
a hold file (present or absent) -- it only reads them.

`idle_watchdog_recovery.py` carries the two pure recovery rules (`classify_stop`, `extract_log_path`,
`restart_needs_uptime`), unit-tested the same way as `idle_watchdog_select.py`.
`serving_swap.sh <geometry> --restart` is the minimal addition this needed: it turns the usual
"already resident" no-op into a real stop+start of the SAME geometry (a session record can say
"resident" for a process that already died).

### Registering and pausing it

```bash
powershell -File scripts/flights/batch/saea_task.ps1 -Name SAEA-Watchdog \
  -Script /mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch/idle_watchdog.sh \
  -RepeatMinutes 5
```

`saea_task.ps1` had no repetition before owner decision 182 (every task it registers uses a
`-Once -At (Get-Date).AddYears(1)` trigger and is started by hand or by `-Start`); `-RepeatMinutes N`
is the minimal addition this needs -- when `N > 0` the registration trigger becomes
`-Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes N)` with no
`-RepetitionDuration` (fires every N minutes, indefinitely; Windows PowerShell 5.1 refuses
`-RepetitionDuration ([TimeSpan]::MaxValue)` with HRESULT 0x80041318, "Duration:P99999999DT23H59M59S", which
the first registration on 2026-09-29 hit); `N` defaults to `0` (the old
one-shot-until-started trigger), so every existing caller is unaffected.

Pause it at any time with `touch /home/chao/saea-queue/watchdog.hold` (no task stop needed: the next
tick logs "watchdog held" and exits 0); remove the file to resume. Check it with
`powershell -File scripts/flights/batch/saea_task.ps1 -Name SAEA-Watchdog -Status`, and preview its
next decision without touching anything via
`bash scripts/flights/batch/idle_watchdog.sh --dry-run`.

## Package flips in one ext4 session (`flip_package_ext4.sh`)

`flip_package_ext4.sh` replaces the hand-written queue flip wrappers. It runs the whole package flip (flip-script convergence loop, plan-pin
refresh and commit, second convergence loop, per-cell registration gates, flight-commit report) inside ONE `flip_in_ext4.sh` worktree session
and fast-forwards master once, then checks that master HEAD equals the reported flight commit. Usage:

```
bash scripts/flights/batch/flip_package_ext4.sh --flip "<flip-script> [args]" --package <readiness dir> --cells <c1,c2,...> \
     --pins-commit-msg <file> [--log <path>] [-- KEY=VALUE ...]
```

`--mode iterate` (the DEFAULT; it stays the default until the owner flips it) runs the convergence loops described above. `--mode one-pass`
(owner decision 270 A, 2026-10-12) runs the flip script ONCE with `FLIP_MODE=one-pass`: `scripts/flights/repin_package_one_pass.py`
(`core/flight/repin_onepass.py`) computes the fixed point of every shared hash across the whole package model-free (config and protocol hashes,
the protocol document sha, the refreshed plan pins, each plan sha in its own ledger row), writes everything once, commits ONCE and then runs
`core.flight.cli check` once per cell on the committed tree. Only the prepared-artifact identity (which binds a configuration that holds its own
pin) stays iterative, as a bounded re-verify of the cells whose fragments changed. All refusals (dirty tree, 9p root, missing receipt, consumed
row, residue, check mismatch) are kept. `--verify-fixed-point` adds one iterative pass that must commit nothing. Supported by `direct_fb_flip.sh`
and `tfrl_i1_flip.sh`:

```
bash scripts/flights/batch/flip_package_ext4.sh --mode one-pass [--verify-fixed-point] --flip "scripts/flights/tfrl/tfrl_i1_flip.sh column" \
  --package docs/readiness/<tfrl-i3-fold-b-package> --cells <c1,c2> --pins-commit-msg <msg> -- TFRL_ITER=3
bash scripts/flights/batch/flip_package_ext4.sh --mode one-pass --flip scripts/flights/direct/direct_fb_flip.sh \
  --package docs/readiness/<direct-fb-package> --cells <c1,c2,...> --pins-commit-msg <msg>
```

The log (default `/home/chao/<package-basename>-flip.out`) carries the monitor milestones: `== flip pass N at <sha> <time>`, `   rc=... HEAD ... dirty=...`,
`== refresh plan pins`, `   refresh rc=`, `   pins committed <short>`, `== gate`, the `flight registration check:` lines,
`flight commit file: <sha> HEAD <sha>`, then `FLIP_CHAIN_DONE <utc>` or `FLIP DID NOT CONVERGE`. Exit codes are those of `flip_in_ext4.sh`
(3 driver alive, 4 master dirty, 6 inner failure, 64 9p root) plus 9 for a master HEAD that differs from the reported flight commit. Run it only
when no batch driver, flight CLI or flip is alive. Coordinator invocations (substitute the package, cells and message file):

```
# 1. direct-fb, all kinds
bash scripts/flights/batch/flip_package_ext4.sh --flip scripts/flights/direct/direct_fb_flip.sh \
  --package docs/readiness/<direct-fb-package> --cells <cell1,cell2,...> --pins-commit-msg <msg> --log /home/chao/direct-fb-flip.out
# 2. direct-fb, thinking only
bash scripts/flights/batch/flip_package_ext4.sh --flip scripts/flights/direct/direct_fb_flip.sh \
  --package docs/readiness/<direct-fb-package> --cells <thinking cells> --pins-commit-msg <msg> -- DIRECT_FB_KINDS="thinking"
# 3. tfrl column, iteration 3
bash scripts/flights/batch/flip_package_ext4.sh --flip "scripts/flights/tfrl/tfrl_i1_flip.sh column" \
  --package docs/readiness/<tfrl-i3-fold-b-package> --cells <i3 smoke cell,i3 cell> --pins-commit-msg <msg> -- TFRL_ITER=3
# 4. tfrl proposers, ACE only, iteration 3
bash scripts/flights/batch/flip_package_ext4.sh --flip "scripts/flights/tfrl/tfrl_i1_flip.sh proposers" \
  --package docs/readiness/<tfrl-i3-proposers-package> --cells <ace cell> --pins-commit-msg <msg> -- TFRL_ITER=3 TFRL_ONLY=ace
```
