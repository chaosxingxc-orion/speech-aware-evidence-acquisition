#!/usr/bin/env bash
# Poll the flight log until the launcher writes its receipt (or aborts).
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf
LOG="$SDIR/flight.log"
MARK1='flight receipt:'
MARK2='FLIGHT ABORTED'
MARK3='^exit: '
for i in $(seq 1 60); do
  if grep -qE "$MARK1|$MARK2|$MARK3" "$LOG" 2>/dev/null; then break; fi
  sleep 20
done
echo "=== last 30 lines ==="
tail -30 "$LOG"
echo "--- gpu ---"
nvidia-smi --query-gpu=pstate,clocks.sm,utilization.gpu,memory.used --format=csv,noheader
echo "--- llama-server ---"
pgrep -a llama-server || echo "  (none running)"
