#!/bin/bash
# The geometry swap BACK after the A2T-AA seal: stop the resident Audio2Tool session cleanly (its scheduled tasks
# SAEA-Serving-A2T / SAEA-Monitor-A2T are stopped from Windows FIRST), verify the card is free; the SLURP session is then
# restarted from Windows (SAEA-Serving + SAEA-Monitor) and slurp_wait_ready.sh waits for it. Mirror of serving_switch_to_slurp.sh.
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
cd $MAIN || exit 1
[ -e $DATA/locks/flight.lock ] && { echo "flight.lock present; refusing to switch"; exit 7; }
pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep && { echo "a flight/driver is alive; refusing"; exit 7; }
bash scripts/serving_session.sh stop --session-id serving-a2t-native-role-base-np3-max2048-v3 2>&1 | tail -3
sleep 5
for p in $(pgrep -f "core.session.serving start"); do kill $p && echo "stopped wrapper $p"; done
sleep 3
pgrep -fa "llama-server --host" | grep -v pgrep | cut -c1-80; nvidia-smi --query-gpu=memory.used --format=csv,noheader
ls $DATA/serving/serving-a2t-native-role-base-np3-max2048-v3/ | grep stop
