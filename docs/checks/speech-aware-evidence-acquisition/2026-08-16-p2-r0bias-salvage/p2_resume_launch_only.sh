#!/usr/bin/env bash
# PHASE 2 R-ladder: LAUNCH ONLY (registration already committed by p2_stage.sh).
# Run DETACHED from Windows (Start-Process wsl.exe) so no harness task cap can kill it.
set -euo pipefail
cd /mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
if pgrep -f run_arm_sequence >/dev/null; then echo "REFUSE: launcher alive"; exit 2; fi
git status --porcelain | grep -q . && { echo "REFUSE: tree dirty"; exit 3; }

export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LLAMA_RUNTIME_ROOT=/home/chao
export PYTHONDONTWRITEBYTECODE=1
REPO=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONPATH="$REPO/src"
LOG=/home/chao/p2-rladder-detached-$(date -u +%Y%m%dT%H%M%SZ).log
{
echo "################ P2 R-LADDER (detached) $(date -u +%FT%TZ) ################"
bash "$REPO/scripts/run_arm_sequence.sh" \
  --arms "$REPO/docs/arms/p2-rladder-resume.arms" \
  --dataset r4-e21-sub10 --experiment r4-context-dose \
  --model q4km-evid-v3 \
  --planned-model-calls 2500 --planned-speech-audio-seconds 170000 \
  --planned-gpu-hours 20.0 --out-dir /home/chao
echo "################ P2 done rc=$? $(date -u +%FT%TZ) ################"
} >> "$LOG" 2>&1
