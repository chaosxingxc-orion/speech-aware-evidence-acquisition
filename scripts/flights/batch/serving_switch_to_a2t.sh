#!/bin/bash
# The geometry swap INTO Audio2Tool (owner decision 69: paid only when at least two A2T cells are ready -- the A2T-AA chain
# is three flights): stop the resident SLURP session cleanly (its scheduled tasks SAEA-Serving / SAEA-Monitor are stopped
# from Windows FIRST), then verify the card is free. The A2T session is then started from Windows (SAEA-Serving-A2T on
# serving_task_entry_a2t.sh, SAEA-Monitor-A2T on serving_monitor_start_a2t.sh) and a2t_wait_ready.sh waits for it.
# Same body and refusals as serving_switch_to_e21.sh (decision 91): never under a flight.lock or a live driver.
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
cd $MAIN || exit 1
[ -e $DATA/locks/flight.lock ] && { echo "flight.lock present; refusing to switch"; exit 7; }
pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep && { echo "a flight/driver is alive; refusing"; exit 7; }
bash scripts/serving_session.sh stop --session-id serving-slurp-native-candidate-five-train-a-np4-v1 2>&1 | tail -3
sleep 5
for p in $(pgrep -f "core.session.serving start"); do kill $p && echo "stopped wrapper $p"; done
sleep 3
pgrep -fa "llama-server --host" | grep -v pgrep | cut -c1-80; nvidia-smi --query-gpu=memory.used --format=csv,noheader
ls $DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1/ | grep stop
