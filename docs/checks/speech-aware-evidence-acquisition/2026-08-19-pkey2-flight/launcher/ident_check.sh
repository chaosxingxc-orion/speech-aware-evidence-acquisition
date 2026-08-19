#!/usr/bin/env bash
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pkey2fly/env.sh

ATT=attempt-20260819T111032Z-3109e8
RD="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338/$ATT"

echo "=== plan.json (run identity as actually bound) ==="
cat "$RD/SAEA-PROBE-pkey2-338.plan.json"

echo
echo "=== attempt store: pkey namespaces ==="
ls -1 "$SPEECHRL_DATA_DIR/attempts/" | grep -i pkey
echo "-- pkey2-338 attempt files --"
ls -1 "$SPEECHRL_DATA_DIR/attempts/SAEA-PROBE-pkey2-338/"
echo "-- pkey-303 attempt files (predecessor, must be untouched) --"
ls -1 "$SPEECHRL_DATA_DIR/attempts/SAEA-PROBE-pkey-303/"

echo
echo "=== predecessor run dir (must still hold ONLY attempt-1) ==="
ls -1 "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey-303/"

echo
echo "=== progress (structural) ==="
echo "responses.jsonl rows: $(wc -l < "$RD/responses.jsonl")"
echo "trace.jsonl rows:     $(wc -l < "$RD/SAEA-PROBE-pkey2-338.trace.jsonl")"

echo
echo "=== GPU samples (5 x 3s) ==="
for i in 1 2 3 4 5; do
  nvidia-smi --query-gpu=pstate,clocks.sm,utilization.gpu,power.draw,temperature.gpu,clocks_throttle_reasons.active --format=csv,noheader
  sleep 3
done

echo
echo "=== recent request latencies (index/latency/chars only) ==="
grep -E " req [0-9]{4} ok " "$SCRATCH/flight.log" | tail -5
