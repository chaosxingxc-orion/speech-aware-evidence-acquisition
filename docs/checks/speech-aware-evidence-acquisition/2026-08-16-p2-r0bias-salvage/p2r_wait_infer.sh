#!/usr/bin/env bash
# Fire once when the CURRENT r1verify attempt starts producing model responses
# (i.e. the NTFS cold load finished and the GPU is decoding). Bounded so it can
# never outlive the harness background cap.
set -uo pipefail
d=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r1verify
DEADLINE=$(( $(date +%s) + 2700 ))   # 45 min
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  a=$(ls -t "$d" 2>/dev/null | head -1)
  # the resumed attempt is newer than the 02:57Z one that died at manifest bind
  if [ -n "$a" ] && [ "$a" \> "attempt-20260816T09" ]; then
    n=$(grep -c '"MODEL_RESPONSE"' "$d/$a/SAEA-P2-r1verify.trace.jsonl" 2>/dev/null || echo 0)
    if [ "${n:-0}" -gt 0 ]; then
      echo "INFERENCE LIVE $(date -u +%FT%TZ)"
      echo "attempt: $a  model_responses=$n"
      echo -n "gpu: "; nvidia-smi --query-gpu=clocks.sm,power.draw,utilization.gpu,memory.used --format=csv,noheader | head -1
      exit 0
    fi
  fi
  sleep 60
done
echo "TIMEOUT after 45 min without a model response $(date -u +%FT%TZ)"
a=$(ls -t "$d" 2>/dev/null | head -1); echo "newest attempt: $a"
echo -n "gpu: "; nvidia-smi --query-gpu=clocks.sm,power.draw,utilization.gpu,memory.used --format=csv,noheader | head -1
pgrep -f run_arm_sequence >/dev/null && echo "sequence: ALIVE" || echo "sequence: GONE"
tail -5 /home/chao/SAEA-P2-r1verify-20260816T105824Z.log 2>/dev/null
exit 1
