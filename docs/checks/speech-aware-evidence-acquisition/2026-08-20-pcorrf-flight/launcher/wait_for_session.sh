#!/usr/bin/env bash
# Poll the flight log until the server session is up (or the flight ends).
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf
LOG="$SDIR/flight.log"
MARK1='session up'
MARK2='FLIGHT ABORTED'
MARK3='flight receipt'
for i in $(seq 1 40); do
  if grep -qE "$MARK1|$MARK2|$MARK3" "$LOG" 2>/dev/null; then break; fi
  sleep 30
done
tail -8 "$LOG"
echo "--- gpu ---"
nvidia-smi --query-gpu=pstate,clocks.sm,utilization.gpu,memory.used --format=csv,noheader
