#!/usr/bin/env bash
# Periodic GPU sample appended to gpu-health.log for the flight receipt.
#   gpu_sample.sh <label>
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2cfly/env.sh
LABEL="${1:-sample}"
printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$LABEL" "$(bash "$SCRATCH/gpu_health.sh")" \
  | tee -a "$SCRATCH/gpu-health.log"
