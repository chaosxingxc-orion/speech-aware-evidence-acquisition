#!/usr/bin/env bash
# The registered P-EMB-3L flight. Runs the launcher from the scratchpad; the
# study working tree is never written to.
#
# Usage:
#   run_flight.sh                 fresh attempt
#   run_flight.sh <attempt-id>    resume that attempt (cached vectors replayed)
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pemb3l
source "$SDIR/env.sh"
RUN_ID=SAEA-PROBE-pemb3l-234
mkdir -p "$SAEA_FEAT_CACHE_DIR"
cd "$REPO"

RUN_PARENT="$SPEECHRL_DATA_DIR/runs/$RUN_ID"
LOG="$SCRATCH/flight.log"

ARGS=(--run-dir "$RUN_PARENT")
if [ "${1:-}" != "" ]; then
  ARGS+=(--attempt-id "$1")
fi

echo "launcher: $SCRATCH/launch_pemb3l_flight.py" | tee -a "$LOG"
echo "wrapper pid: $$" | tee -a "$LOG"
echo "args: ${ARGS[*]}" | tee -a "$LOG"
echo "feat cache: $SAEA_FEAT_CACHE_DIR" | tee -a "$LOG"
echo "media marker pin: $LLAMA_MEDIA_MARKER" | tee -a "$LOG"
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"

python -u "$SCRATCH/launch_pemb3l_flight.py" "${ARGS[@]}" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
echo "exit: $rc at $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"

echo "=== post-flight resident server check (both sessions must be gone) ===" | tee -a "$LOG"
pgrep -a llama-server | tee -a "$LOG" || echo "  (none running)" | tee -a "$LOG"
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader | tee -a "$LOG"
exit "$rc"
