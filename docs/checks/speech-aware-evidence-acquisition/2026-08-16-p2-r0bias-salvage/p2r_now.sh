#!/usr/bin/env bash
# P2 RESUME poll: four arms only.
set -uo pipefail
date -u +%FT%TZ
echo -n "llama-server procs: "; pgrep -c llama-server 2>/dev/null || echo 0
echo -n "sequence alive: "; pgrep -f run_arm_sequence >/dev/null && echo YES || echo NO
d=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs
for run in SAEA-P2-r1verify SAEA-P2-r2draft SAEA-P2-r0wrong SAEA-P2-r1wrong; do
  a=$(ls -t "$d/$run" 2>/dev/null | head -1)
  if [ -z "$a" ]; then echo "$run: no attempt"; continue; fi
  tr="$d/$run/$a/$run.trace.jsonl"
  n=$(grep -c '"MODEL_RESPONSE"' "$tr" 2>/dev/null || echo 0)
  outs=$(ls "$d/$run/$a"/*.replay-derivation.*.json 2>/dev/null | wc -l)
  m="$d/$run/$a/$run.run-manifest.json"
  st=$(grep -o '"status": "[A-Z]*"' "$m" 2>/dev/null | head -1 || true)
  [ -z "$st" ] && st="(no manifest yet)"
  echo "$run: $a resp=$n samples_done=$outs $st"
done
echo "--- detached log tail ---"
L=$(ls -t /home/chao/p2-rladder-detached-*.log 2>/dev/null | head -1)
echo "log: $L"
tail -6 "$L" 2>/dev/null
echo "--- gpu ---"
nvidia-smi --query-gpu=clocks.sm,power.draw,utilization.gpu,memory.used --format=csv,noheader | head -1
