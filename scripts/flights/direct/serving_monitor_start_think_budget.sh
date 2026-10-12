#!/bin/bash
# Coordinator-owned monitor sampler for the resident THINK-BUDGET session (appends monitor.jsonl every 10 s; the flight receipts
# summarise it). Started by serving_swap.sh through the Windows Scheduled Task SAEA-Monitor-THINKB, 20 s after the serving task.
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
source /home/chao/.venvs/speechrl/bin/activate
cd "$MAIN" || exit 1
echo "monitor start $(date -u +%FT%TZ)"
python -B scripts/serving_monitor.py sample --session-id serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1 --interval 10 > /home/chao/serving-monitor-thinkb-$(date -u +%Y%m%dT%H%M%SZ).log 2>&1
echo "monitor exit $? $(date -u +%FT%TZ)"
