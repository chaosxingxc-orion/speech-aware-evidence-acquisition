#!/bin/bash
# Coordinator-owned monitor sampler for the resident session (appends monitor.jsonl every 10 s; the flight receipts summarise it).
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
source /home/chao/.venvs/speechrl/bin/activate
cd "$MAIN" || exit 1
echo "monitor start $(date -u +%FT%TZ)"
python -B scripts/serving_monitor.py sample --session-id serving-slurp-native-candidate-five-train-a-np4-v1 --interval 10 > /home/chao/serving-monitor-$(date -u +%Y%m%dT%H%M%SZ).log 2>&1
echo "monitor exit $? $(date -u +%FT%TZ)"
