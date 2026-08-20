#!/usr/bin/env bash
# The registered P-EMB flight. Runs the launcher from the scratchpad; the study
# working tree is never written to.
#
# Usage:
#   run_flight.sh <A|B>                 fresh attempt
#   run_flight.sh <A|B> <attempt-id>    resume that attempt (cached vectors replayed)
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri2/pemb
source "$SDIR/env.sh"
RUN="${1:?usage: run_flight.sh <A|B> [attempt-id]}"
case "$RUN" in
  A) export SAEA_FEAT_CACHE_DIR=/home/chao/feat-cache/slurp-q4km; RUN_ID=SAEA-PROBE-pemb1-78 ;;
  B) export SAEA_FEAT_CACHE_DIR=/home/chao/feat-cache/audio2tool-q4km; RUN_ID=SAEA-PROBE-pemb2-552 ;;
  *) echo "unknown run $RUN"; exit 2 ;;
esac
mkdir -p "$SAEA_FEAT_CACHE_DIR"
cd "$REPO"

RUN_PARENT="$SPEECHRL_DATA_DIR/runs/$RUN_ID"
LOG="$SCRATCH/flight-run$RUN.log"

ARGS=(--run "$RUN" --run-dir "$RUN_PARENT")
if [ "${2:-}" != "" ]; then
  ARGS+=(--attempt-id "$2")
fi

echo "launcher: $SCRATCH/launch_pemb_flight.py" | tee -a "$LOG"
echo "wrapper pid: $$" | tee -a "$LOG"
echo "args: ${ARGS[*]}" | tee -a "$LOG"
echo "feat cache: $SAEA_FEAT_CACHE_DIR" | tee -a "$LOG"
echo "media marker pin: $LLAMA_MEDIA_MARKER" | tee -a "$LOG"
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"

python -u "$SCRATCH/launch_pemb_flight.py" "${ARGS[@]}" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
echo "exit: $rc at $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$LOG"

echo "=== post-flight resident server check ===" | tee -a "$LOG"
pgrep -a llama-server | tee -a "$LOG" || echo "  (none running)" | tee -a "$LOG"
exit "$rc"
