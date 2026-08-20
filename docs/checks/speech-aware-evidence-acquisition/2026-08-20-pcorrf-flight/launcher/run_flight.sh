#!/usr/bin/env bash
# The registered P-CORR-F flight (SAEA-PROBE-pcorrf-240). Runs the launcher from
# the scratchpad; the study working tree is never written to. The llama-server
# is spawned as a CHILD of this wrapper's own python process and dies with it.
#
# Usage:
#   run_flight.sh                              fresh attempt
#   run_flight.sh <attempt-id>                 resume that attempt (responses replayed)
#   run_flight.sh <attempt-id> <carry-from-id> resume + carry COMPLETE arms from another attempt
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf
source "$SDIR/env.sh"
cd "$REPO"

RUN_PARENT="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pcorrf-240"
LOG="$SCRATCH/flight.log"

ARGS=(--run-dir "$RUN_PARENT" --binding-dir "$SCRATCH")
if [ "${1:-}" != "" ]; then
  ARGS+=(--attempt-id "$1")
fi
if [ "${2:-}" != "" ]; then
  ARGS+=(--carry-from "$2")
fi

echo "launcher: $SCRATCH/launch_pcorrf_flight.py" | tee -a "$LOG"
echo "wrapper pid: $$" | tee -a "$LOG"
echo "args: ${ARGS[*]}" | tee -a "$LOG"
echo "feat cache: $SAEA_FEAT_CACHE_DIR" | tee -a "$LOG"
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"

python -u "$SCRATCH/launch_pcorrf_flight.py" "${ARGS[@]}" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
echo "exit: $rc at $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"

echo "=== post-flight orphan check ===" | tee -a "$LOG"
pgrep -a llama-server | tee -a "$LOG" || echo "  (none running)" | tee -a "$LOG"
exit "$rc"
