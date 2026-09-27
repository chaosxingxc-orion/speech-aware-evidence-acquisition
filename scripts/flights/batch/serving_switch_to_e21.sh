#!/bin/bash
# Decision 91: stop the resident SLURP session cleanly (its scheduled task is stopped from Windows first), then verify the card is free.
# Prefer scripts/flights/batch/serving_swap.sh e21-np4, which does the whole swap in order (owner decision 163).
STOP_SID=serving-slurp-native-candidate-five-train-a-np4-v1
NEXT=e21-np4
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=serving_lib.sh
source "$HERE/serving_lib.sh"
MAIN=$SAEA_MAIN
DATA=$SAEA_DATA
SS=${SAEA_SERVING_SESSION:-scripts/serving_session.sh}
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
cd $MAIN || exit 1
# Owner decision 163: only a GENERATION flight blocks the switch (a model-free core.flight.cli prepare-supply/check
# in a worktree no longer does), and the host-memory start guard of the NEXT geometry is checked BEFORE the stop.
if REASONS=$(saea_flight_alive); then echo "$REASONS"; echo "a flight/driver is alive; refusing"; exit 7; fi
HM=$(bash $SS host-memory --min-host-free-gb "$SAEA_MIN_HOST_FREE_GB" --margin-gb "${SAEA_SWAP_MARGIN_GB:-0.5}" 2>&1); HM_RC=$?
if [ $HM_RC -ne 0 ]; then
  echo "$HM"; echo "the $NEXT start would refuse on host memory (exit $HM_RC); nothing is stopped. CPU sidecars: $(saea_cpu_sidecars | tr '\n' ';')"; exit 8
fi
bash $SS stop --session-id $STOP_SID 2>&1 | tail -3
sleep 5
for p in $(pgrep -f -- "[c]ore\.session\.serving start .*--session-id $STOP_SID( |$)"); do kill $p && echo "stopped wrapper $p"; done
sleep 3
pgrep -fa "[l]lama-server --host" | cut -c1-80; nvidia-smi --query-gpu=memory.used --format=csv,noheader
ls $DATA/serving/$STOP_SID/ | grep stop
