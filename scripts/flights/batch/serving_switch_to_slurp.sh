#!/bin/bash
# After the E35 seal: stop the resident E21 session cleanly (its scheduled tasks SAEA-Serving-E21 / SAEA-Monitor-E21 are stopped from
# Windows first), verify the card is free; the SLURP session is then restarted from Windows (SAEA-Serving + SAEA-Monitor).
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
cd $MAIN || exit 1
[ -e $DATA/locks/flight.lock ] && { echo "flight.lock present; refusing to switch"; exit 7; }
pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep && { echo "a flight/driver is alive; refusing"; exit 7; }
bash scripts/serving_session.sh stop --session-id serving-e21-native-window-flightruntime-np4-max1024-v1 2>&1 | tail -3
sleep 5
for p in $(pgrep -f "core.session.serving start"); do kill $p && echo "stopped wrapper $p"; done
sleep 3
pgrep -fa "llama-server --host" | grep -v pgrep | cut -c1-80; nvidia-smi --query-gpu=memory.used --format=csv,noheader
ls $DATA/serving/serving-e21-native-window-flightruntime-np4-max1024-v1/ | grep stop
