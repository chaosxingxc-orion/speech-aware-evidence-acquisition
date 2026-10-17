#!/bin/bash
# Queue hook (owner rulings 327 A / 328, 2026-10-17): when the NX-T R2b chain exits rc 0, flip the NX-T R2 arm cell to its rec2 (resume)
# registration in ext4 and start SAEA-Chain-NXT2 (already pointed at `arm-only`). Usage: queue_nxt2rec2_after_nxt2b.sh <start-stamp-UTC>
# (only a CHAIN_NXT2B_EXIT line LATER than the stamp counts). Poll 60 s, at most 36 h. Logs to /home/chao/nxt2rec2-queue.out. Refuses
# (exit 9) on an R2b exit other than 0, a dirty master, a live flight, or a flip that does not converge; never touches the data root.
set -u
STAMP=${1:?start stamp (UTC ISO ...Z) required}
M=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
LOG=/home/chao/nxt2rec2-queue.out; CHAIN_OUT=/home/chao/nxt2b-chain.out
PS1_WIN='D:\chao_workspace\exploring-l4-intelligence\studies\speech-aware-evidence-acquisition\scripts\flights\batch\saea_task.ps1'
say() { echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }
exit_rc() { awk -v s="$STAMP" '$1 == "CHAIN_NXT2B_EXIT" && $3 > s { sub("rc=", "", $2); print $2; exit }' "$CHAIN_OUT" 2>/dev/null; }
say "armed: waiting for CHAIN_NXT2B_EXIT after $STAMP (poll 60 s, max 36 h)"
waited=0
while :; do
  rc=$(exit_rc)
  [ -n "$rc" ] && break
  [ $waited -ge 129600 ] && { say "TIMEOUT: no CHAIN_NXT2B_EXIT after $STAMP; R2 rec2 NOT launched"; exit 9; }
  sleep 60; waited=$((waited + 60))
done
[ "$rc" = 0 ] || { say "R2b exited rc=$rc; R2 rec2 NOT launched (coordinator decides)"; exit 9; }
say "R2b exit rc=0 seen; waiting 120 s for the seal-side processes to drain"; sleep 120
cd "$M" || exit 9
source /home/chao/.venvs/speechrl/bin/activate; export PYTHONDONTWRITEBYTECODE=1 SPEECHRL_DATA_DIR=/home/chao/saea-data/speechrl-data
[ "$(git status --porcelain | wc -l)" = 0 ] || { say "master dirty; NOT launched"; exit 9; }
[ "$(pgrep -fc 'core.flight.cli|batch_driver|lease_cli')" = 0 ] || { say "a flight process is alive; NOT launched"; exit 9; }
[ -e /home/chao/saea-data/speechrl-data/locks/flight.lock ] && { say "flight.lock present; NOT launched"; exit 9; }
say "flip: NX-T R2 arm cell to rec2 (NXT2_KINDS=arm)"
bash scripts/flights/batch/flip_package_ext4.sh --flip scripts/flights/nx/nxt_r2_flip.sh --package docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1 \
  --cells slurp-native-stage3-nxt-r2-thinking-budget-fold-b-v1 --pins-commit-msg /home/chao/nxt2-pins-commit.txt --log /home/chao/nxt2-rec2-flip.out -- NXT2_KINDS=arm >> "$LOG" 2>&1; frc=$?
if [ $frc -ne 0 ] || ! grep -q "FLIP_CHAIN_DONE" /home/chao/nxt2-rec2-flip.out || grep -q "FAIL\|refus" /home/chao/nxt2-rec2-flip.out || [ "$(git rev-parse HEAD)" != "$(cat /home/chao/nxt2-flight-commit.txt)" ]; then
  say "flip not converged (rc=$frc); see /home/chao/nxt2-rec2-flip.out; NOT launched"; exit 9; fi
say "flip converged at $(git rev-parse HEAD); starting SAEA-Chain-NXT2 (arm-only)"
grep -q "batch_chain_nxt_r2.sh arm-only" /home/chao/saea-queue/chain_nxt2.sh || { say "chain wrapper is not arm-only; NOT launched"; exit 9; }
powershell.exe -NoProfile -NonInteractive -Command "& '$PS1_WIN' -Name SAEA-Chain-NXT2 -Start" >> "$LOG" 2>&1 || { say "task start failed"; exit 9; }
say "SAEA-Chain-NXT2 started; done"; exit 0
