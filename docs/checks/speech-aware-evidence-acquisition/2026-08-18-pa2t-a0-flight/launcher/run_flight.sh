#!/usr/bin/env bash
# P-A2T Stage-1 A0 flight.
#   run_flight.sh                 fresh attempt
#   run_flight.sh <attempt-id>    resume that attempt (cached responses replayed)
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/a2tfly2/env.sh
cd "$REPO"
RUN_PARENT="$SPEECHRL_DATA_DIR/runs/SAEA-BASE-a2t-a0-400"
LOG="$SCRATCH/flight.log"
ARGS=(--run-dir "$RUN_PARENT")
if [ "${1:-}" != "" ]; then ARGS+=(--attempt-id "$1"); fi
echo "launcher: $SCRATCH/launch_pa2t_a0.py" | tee -a "$LOG"
echo "args: ${ARGS[*]}" | tee -a "$LOG"
echo "feat cache: $SAEA_FEAT_CACHE_DIR" | tee -a "$LOG"
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"
python -u "$SCRATCH/launch_pa2t_a0.py" "${ARGS[@]}" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
echo "exit: $rc at $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"
exit "$rc"
