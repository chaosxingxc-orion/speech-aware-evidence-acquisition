#!/usr/bin/env bash
# One babysit cycle: sample GPU every 5 min for ~20 min, then report arm state.
# Bounded well under the harness foreground cap.
set -uo pipefail
d=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs
CYCLES="${1:-4}"
for i in $(seq 1 "$CYCLES"); do
  printf "%s  gpu: %s\n" "$(date -u +%FT%TZ)" \
    "$(nvidia-smi --query-gpu=clocks.sm,power.draw,utilization.gpu,memory.used --format=csv,noheader | head -1)"
  [ "$i" -lt "$CYCLES" ] && sleep 300
done
echo "--- arm state $(date -u +%FT%TZ) ---"
pgrep -f run_arm_sequence >/dev/null && echo "sequence: ALIVE" || echo "sequence: GONE"
echo -n "llama-server procs: "; pgrep -c llama-server 2>/dev/null || echo 0
for run in SAEA-P2-r1verify SAEA-P2-r2draft SAEA-P2-r0wrong SAEA-P2-r1wrong; do
  a=$(ls -t "$d/$run" 2>/dev/null | head -1)
  [ -z "$a" ] && { echo "$run: no attempt"; continue; }
  n=$(grep -c '"MODEL_RESPONSE"' "$d/$a" 2>/dev/null; grep -c '"MODEL_RESPONSE"' "$d/$run/$a/$run.trace.jsonl" 2>/dev/null || echo 0)
  n=$(echo "$n" | tail -1)
  outs=$(ls "$d/$run/$a"/*.replay-derivation.*.json 2>/dev/null | wc -l)
  st=$(grep -o '"status": "[A-Z]*"' "$d/$run/$a/$run.run-manifest.json" 2>/dev/null | head -1 || true)
  [ -z "$st" ] && st="(running/no manifest)"
  echo "$run: $a resp=$n samples=$outs $st"
done
echo "--- detached log tail ---"
tail -4 /home/chao/p2-rladder-detached-20260816T105824Z.log 2>/dev/null
