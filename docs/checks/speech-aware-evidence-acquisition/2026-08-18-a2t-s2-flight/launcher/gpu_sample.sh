#!/usr/bin/env bash
# Append one labelled GPU health sample to the campaign health log.
#   gpu_sample.sh <label>
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2fly2/env.sh
LABEL="${1:-sample}"
{
  echo "== $LABEL $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  nvidia-smi --query-gpu=clocks.sm,clocks.max.sm,temperature.gpu,power.draw,utilization.gpu,memory.used,pstate --format=csv,noheader
} | tee -a "$SCRATCH/gpu-health.log"
