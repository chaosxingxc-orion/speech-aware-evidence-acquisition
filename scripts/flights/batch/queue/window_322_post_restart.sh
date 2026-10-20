#!/bin/bash
# Post-restart step of the 322 window (owner rulings 322 A / 331 A, 2026-10-18), run by window_322_orchestrator.ps1 after `wsl --shutdown`
# applied the new .wslconfig: (1) close the NX-T R2 rec2 exposure rows (chain_lib close_rows_after_seal, commits the ledger alone);
# (2) start the resident Thinking session through the swap (the only sanctioned path; no flight is open); (3) the 330 A Solver reasoning
# diagnostic (< 1 GPU-h; its failure is logged and does not block R3); (4) the NX-T R3 queue hook, which sees the R2 exit line at once and
# flips + chains R3. Log /home/chao/w322-window.out.
set -u
M=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition; LOG=/home/chao/w322-window.out
say() { echo "$(date -u +%FT%TZ) post: $*" >> "$LOG"; }
cd "$M" || exit 9
source /home/chao/.venvs/speechrl/bin/activate
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$M/src SPEECHRL_DATA_DIR=/home/chao/saea-data/speechrl-data DATA=/home/chao/saea-data/speechrl-data MAIN=$M PY=python
say "start; VM memory $(free -g | awk '/Mem:/{print $2}') GB total"
# 2026-10-20 incident: after `wsl --shutdown` the data VHDX (/mnt/saea-data-1, mounted by the Windows task SAEA-Mount-Data1 at boot only) is
# detached, so the data root is absent and both the ledger closure and the serving swap refuse. Re-run the mount task from here and wait for it.
if [ ! -d "$SPEECHRL_DATA_DIR/runs" ]; then
  say "data root absent ($SPEECHRL_DATA_DIR/runs); starting SAEA-Mount-Data1 and waiting (up to 600 s)"
  /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -NonInteractive -Command "Start-ScheduledTask -TaskName SAEA-Mount-Data1" >> "$LOG" 2>&1
  for i in $(seq 1 60); do [ -d "$SPEECHRL_DATA_DIR/runs" ] && break; sleep 10; done
  [ -d "$SPEECHRL_DATA_DIR/runs" ] || { say "data root still absent; NOT continuing"; exit 9; }
  say "data root mounted"
fi
[ "$(git status --porcelain | wc -l)" = 0 ] || { say "master dirty; NOT continuing"; exit 9; }
LOG_SAVE=$LOG; source scripts/flights/batch/chain_lib.sh; LOG=$LOG_SAVE
close_rows_after_seal SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-V1 SAEA-SLURP-STAGE3-NXT-R2-THINKING-BUDGET-FOLD-B-FIT-V1; say "close rows rc=$?"
bash scripts/flights/batch/serving_swap.sh think-budget-np4 >> "$LOG" 2>&1; src=$?
say "serving_swap think-budget-np4 rc=$src"
[ $src -eq 0 ] || { say "swap failed; diagnostic and R3 NOT launched"; exit 9; }
bash scripts/flights/diag/solver_reasoning_diag.sh >> "$LOG" 2>&1; say "diagnostic rc=$?"
[ "$(git status --porcelain | wc -l)" = 0 ] || { say "master dirty after the diagnostic; R3 NOT launched"; git status --porcelain >> "$LOG"; exit 9; }
bash scripts/flights/batch/queue/queue_nxt3_after_nxt2.sh 2026-10-18T14:36:38Z; qrc=$?
say "R3 queue hook rc=$qrc (log /home/chao/nxt3-queue.out)"
[ $qrc -eq 0 ] || exit $qrc
# owner ruling 338 (2026-10-19): SLURP lock first, carriers deferred -> arm only the NX-T R4 hook (it waits for CHAIN_NXT3_EXIT). A hook armed before the shutdown would have died with it. Start-only.
PS1W='D:\chao_workspace\exploring-l4-intelligence\studies\speech-aware-evidence-acquisition\scripts\flights\batch\saea_task.ps1'
for t in SAEA-Queue-NXT4; do
  /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -NonInteractive -File "$PS1W" -Name "$t" -Start >> "$LOG" 2>&1; say "start $t rc=$?"
done
exit 0
