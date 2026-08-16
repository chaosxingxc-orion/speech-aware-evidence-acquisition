#!/usr/bin/env bash
set -uo pipefail
T=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r1verify/attempt-20260816T105836Z-b06529/SAEA-P2-r1verify.trace.jsonl
S=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r1verify/attempt-20260816T105836Z-b06529/SAEA-P2-r1verify.server.log
n0=$(grep -c 'MODEL_RESPONSE' "$T" 2>/dev/null || echo 0)
h0=$(grep -c 'feat-cache HIT' "$S" 2>/dev/null || echo 0)
e0=$(grep -ci 'encoding mtmd' "$S" 2>/dev/null || echo 0)
echo "start: responses=$n0 cache_hits=$h0 encodes=$e0  $(date -u +%T)"
sum=0; zero=0; N=20; max=0
for i in $(seq $N); do
  u=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits)
  sum=$((sum+u)); [ "$u" -eq 0 ] && zero=$((zero+1)); [ "$u" -gt "$max" ] && max=$u
  sleep 3
done
n1=$(grep -c 'MODEL_RESPONSE' "$T" 2>/dev/null || echo 0)
h1=$(grep -c 'feat-cache HIT' "$S" 2>/dev/null || echo 0)
e1=$(grep -ci 'encoding mtmd' "$S" 2>/dev/null || echo 0)
echo "end:   responses=$n1 cache_hits=$h1 encodes=$e1  $(date -u +%T)"
echo "--- over 60s: mean_gpu_util=$((sum/N))%  zero_samples=$zero/$N  peak=$max%"
echo "--- delta: responses=+$((n1-n0))  cache_hits=+$((h1-h0))  encodes=+$((e1-e0))"
nvidia-smi --query-gpu=clocks.sm,power.draw,memory.used --format=csv,noheader
echo "--- busy slots now ---"
curl -s -m 5 http://127.0.0.1:8080/slots | grep -o '"is_processing":true' | wc -l
