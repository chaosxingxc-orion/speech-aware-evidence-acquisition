#!/usr/bin/env bash
# The registered P-A2T abstention-asymmetry flight (SAEA-PROBE-a2t-abst-44).
#   run_flight.sh                              fresh attempt
#   run_flight.sh <attempt-id> [prior-wall-s]  resume that attempt (cached responses replayed)
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri/abst
source "$SDIR/env.sh"
cd "$REPO"

RUN_PARENT="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-abst-44"
LOG="$SCRATCH/flight.log"

ARGS=(--run-dir "$RUN_PARENT")
if [ "${1:-}" != "" ]; then ARGS+=(--attempt-id "$1"); fi
if [ "${2:-}" != "" ]; then ARGS+=(--prior-wall-seconds "$2"); fi

echo "launcher: $SCRATCH/launch_a2t_abst.py" | tee -a "$LOG"
echo "wrapper pid: $$" | tee -a "$LOG"
echo "args: ${ARGS[*]}" | tee -a "$LOG"
echo "feat cache: $SAEA_FEAT_CACHE_DIR" | tee -a "$LOG"
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"

python -u "$SCRATCH/launch_a2t_abst.py" "${ARGS[@]}" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
echo "exit: $rc at $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"

echo "=== post-flight orphan check ===" | tee -a "$LOG"
pgrep -a llama-server | tee -a "$LOG" || echo "  (none running)" | tee -a "$LOG"
exit "$rc"
