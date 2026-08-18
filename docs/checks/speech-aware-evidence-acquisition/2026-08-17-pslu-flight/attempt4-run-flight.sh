#!/usr/bin/env bash
# Attempt 3 of the registered P-SLU flight. Runs the ARCHIVED launcher unmodified
# from the scratchpad; the study working tree is never written to.
#
# Usage:
#   run_flight.sh                 fresh attempt
#   run_flight.sh <attempt-id>    resume that attempt (cached responses replayed)
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pslufly4/env.sh

cd "$REPO"

RUN_PARENT="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60"
LOG="$SCRATCH/attempt4-flight.log"

ARGS=(--run-dir "$RUN_PARENT")
if [ "${1:-}" != "" ]; then
  ARGS+=(--attempt-id "$1")
fi

echo "launcher: $SCRATCH/launch_pslu_flight.py" | tee -a "$LOG"
echo "args: ${ARGS[*]}" | tee -a "$LOG"
echo "feat cache: $SAEA_FEAT_CACHE_DIR" | tee -a "$LOG"
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"

python -u "$SCRATCH/launch_pslu_flight.py" "${ARGS[@]}" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
echo "exit: $rc at $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"
exit "$rc"
