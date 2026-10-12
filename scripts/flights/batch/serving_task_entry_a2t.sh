#!/bin/bash
# Entry point for the Windows Scheduled Task "SAEA-Serving-A2T": owns the resident AUDIO2TOOL-geometry serving wrapper
# (q4km-mmproj-free-a2t-native-role-np3-max2048-v1: -c 98304 -np 3, three 32,768-token slots, max2048, --no-mmproj,
# LLAMA_SPEECH_FEATURE_ROOT /home/chao/feat-cache/a2t-native-system-4000-packets-04ccc72a, port 8080) for the A2T-AA chain
# and every later Audio2Tool cell. Same discipline as serving_task_entry.sh / serving_task_entry_e21.sh. It is a DIFFERENT
# session identity from the SLURP np4 session: stop that one first (serving_switch_to_a2t.sh) -- serving_session.sh start
# refuses while anything listens on the port.
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
saea_data_root_init || exit 70
DATA=$SAEA_DATA_ROOT
SID=serving-a2t-native-role-base-np3-max2048-v3
S=$DATA/serving/$SID
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
source /home/chao/.venvs/speechrl/bin/activate
cd "$MAIN" || exit 1
LOG=/home/chao/serving-a2t-task-$(date -u +%Y%m%dT%H%M%SZ).log
exec > "$LOG" 2>&1
echo "task entry $(date -u +%FT%TZ) HEAD $(git rev-parse --short HEAD)"
SL=$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1
if [ -f "$SL/session.json" ] && [ ! -f "$SL/session-stop.json" ]; then echo "the SLURP session is still resident; run serving_switch_to_a2t.sh first"; exit 7; fi
for p in $(pgrep -f "core.session.serving start"); do kill -9 $p && echo "killed orphan wrapper $p"; done
for p in $(pgrep -f "llama-server --host 127.0.0.1 --port 8080"); do kill -9 $p && echo "killed orphan server $p"; done
sleep 2
if [ -f "$S/session.json" ] && [ ! -f "$S/session-stop.json" ]; then
  echo "recording the stale stop of the previous A2T session"; bash scripts/serving_session.sh stop --session-id $SID 2>&1 | tail -2
fi
T0=$(date +%s)
bash scripts/serving_session.sh start q4km-mmproj-free-a2t-native-role-np3-max2048-v1 \
  --session-id $SID --runtime-root /home/chao > /home/chao/serving-a2t-np3-$(date -u +%Y%m%dT%H%M%SZ).log 2>&1 &
W=$!
echo "wrapper pid $W"
# Owner decision 163: wait for the new session.json as long as the wrapper lives (a load over 90 s used to leave the stale
# stop record in place, and a flight refuses to attach to a session that has one), not a fixed 90 s.
for i in $(seq 1 450); do sleep 2; [ -f "$S/session.json" ] && [ "$(stat -c %Y "$S/session.json")" -ge "$T0" ] && break; kill -0 $W 2>/dev/null || break; done
if [ -f "$S/session.json" ] && [ "$(stat -c %Y "$S/session.json")" -ge "$T0" ] && [ -f "$S/session-stop.json" ]; then
  A=$S/archive-stopped-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p "$A"; mv "$S/session-stop.json" "$S/.session-stop.lock" "$A/" 2>/dev/null && echo "stale stop record archived to $A"
fi
echo "waiting on the wrapper $(date -u +%FT%TZ)"
wait $W
echo "wrapper exited $? $(date -u +%FT%TZ)"
