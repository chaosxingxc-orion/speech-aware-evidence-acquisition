#!/usr/bin/env bash
# Bounded IGNITION check: waits (default up to 540 s) for the flight to reach
# a given marker stage, then prints STRUCTURAL evidence only (line counts,
# pids, attempt id). Never prints response content.
# Usage: airborne.sh [max_wait_seconds] [min_rows]
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pkey2fly/env.sh

MAX_WAIT="${1:-540}"
MIN_ROWS="${2:-3}"
LOG="$SCRATCH/flight.log"
RUN_PARENT="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338"

deadline=$(( $(date +%s) + MAX_WAIT ))
while :; do
  attempt=""
  if [ -d "$RUN_PARENT" ]; then
    attempt=$(ls -1t "$RUN_PARENT" 2>/dev/null | head -1)
  fi
  rows=0
  if [ -n "$attempt" ] && [ -f "$RUN_PARENT/$attempt/responses.jsonl" ]; then
    rows=$(wc -l < "$RUN_PARENT/$attempt/responses.jsonl")
  fi
  if [ "$rows" -ge "$MIN_ROWS" ]; then
    break
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "TIMEOUT waiting for $MIN_ROWS response rows (have $rows)"
    break
  fi
  sleep 5
done

echo "=== ignition status $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "newest attempt: ${attempt:-<none>}"
if [ -n "${attempt:-}" ]; then
  echo "attempt dir: $RUN_PARENT/$attempt"
  echo "responses.jsonl rows: ${rows}"
  ls -la "$RUN_PARENT/$attempt" | sed 's/^/  /'
fi
echo
echo "=== flight.log phase markers (operational lines only) ==="
grep -E "wrapper pid|attempt |session up|silence-swap registered|FrozenCoreClient constructed|FLIGHT START|FLIGHT ABORTED|FAILED after|^exit:" "$LOG" 2>/dev/null | tail -20
echo
echo "=== first + latest request health lines (index/latency/chars only) ==="
grep -E " req [0-9]{4} ok | req [0-9]{4} FAILED" "$LOG" 2>/dev/null | head -3
grep -E " req [0-9]{4} ok | req [0-9]{4} FAILED" "$LOG" 2>/dev/null | tail -2
echo
echo "=== pids ==="
pgrep -af "launch_pkey_flight.py" || echo "  launcher: not running"
pgrep -a llama-server || echo "  llama-server: not running"
