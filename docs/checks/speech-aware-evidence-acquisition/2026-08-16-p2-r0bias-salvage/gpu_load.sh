#!/usr/bin/env bash
set -uo pipefail
date -u +%FT%TZ
echo "=== GPU ==="
nvidia-smi --query-gpu=clocks.sm,clocks.max.sm,power.draw,power.limit,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu --format=csv
echo "=== GPU procs ==="
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
echo "=== llama-server ==="
pgrep -af llama-server | head -5 || echo none
echo "=== launcher ==="
pgrep -af run_arm_sequence | head -3 || echo none
echo "=== CPU load ==="
uptime
nproc
echo "=== top 8 CPU procs ==="
ps -eo pcpu,pmem,etime,comm --sort=-pcpu | head -9
echo "=== detached logs (newest) ==="
ls -t /home/chao/p2-rladder-detached-*.log 2>/dev/null | head -1 | xargs -r tail -12
echo "=== run progress ==="
d=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs
for run in SAEA-P2-r1verify SAEA-P2-r2draft SAEA-P2-r0wrong SAEA-P2-r1wrong; do
  a=$(ls -t "$d/$run" 2>/dev/null | head -1)
  [ -z "$a" ] && { echo "$run: no attempt"; continue; }
  tr="$d/$run/$a/$run.trace.jsonl"
  n=$(grep -c '"MODEL_RESPONSE"' "$tr" 2>/dev/null || echo 0)
  sz=$(stat -c %s "$tr" 2>/dev/null || echo 0)
  mt=$(stat -c %y "$tr" 2>/dev/null | cut -d. -f1 || echo -)
  echo "$run: $a resp=$n bytes=$sz last_write=$mt"
done
