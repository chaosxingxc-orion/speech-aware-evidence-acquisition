#!/usr/bin/env bash
# Bounded IGNITION wait: exits as soon as the flight has produced MIN_ROWS
# response rows, OR the launcher has terminated / aborted, OR the deadline
# passes. Structural evidence only -- never response content.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pkey2fly/env.sh

MAX_WAIT="${1:-900}"
MIN_ROWS="${2:-5}"
LOG="$SCRATCH/flight.log"
RUN_PARENT="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338"

deadline=$(( $(date +%s) + MAX_WAIT ))
reason="TIMEOUT"
while :; do
  attempt=""
  rows=0
  if [ -d "$RUN_PARENT" ]; then
    attempt=$(ls -1t "$RUN_PARENT" 2>/dev/null | head -1)
    if [ -n "$attempt" ] && [ -f "$RUN_PARENT/$attempt/responses.jsonl" ]; then
      rows=$(wc -l < "$RUN_PARENT/$attempt/responses.jsonl")
    fi
  fi
  if [ "$rows" -ge "$MIN_ROWS" ]; then reason="AIRBORNE"; break; fi
  if grep -qE "FLIGHT ABORTED|^exit:" "$LOG" 2>/dev/null; then reason="TERMINATED"; break; fi
  if [ "$(date +%s)" -ge "$deadline" ]; then break; fi
  sleep 5
done

echo "=== ignition wait ended: $reason at $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
bash "$SCRATCH/airborne.sh" 0 "$MIN_ROWS"
