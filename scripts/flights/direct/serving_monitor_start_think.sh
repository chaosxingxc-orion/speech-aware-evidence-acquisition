#!/bin/bash
# Coordinator-owned monitor sampler for the resident THINK session (appends monitor.jsonl every 10 s; the flight receipts
# summarise it). Started by serving_swap.sh through the Windows Scheduled Task SAEA-Monitor-THINK, 20 s after the serving task.
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
saea_data_root_init || exit 70
DATA=$SAEA_DATA_ROOT
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
source /home/chao/.venvs/speechrl/bin/activate
cd "$MAIN" || exit 1
echo "monitor start $(date -u +%FT%TZ)"
python -B scripts/serving_monitor.py sample --session-id serving-slurp-thinking-direct-fold-b-np4-max8192-v1 --interval 10 > /home/chao/serving-monitor-think-$(date -u +%Y%m%dT%H%M%SZ).log 2>&1
echo "monitor exit $? $(date -u +%FT%TZ)"
