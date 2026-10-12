#!/bin/bash
# Orphan reaper scoped to port 8080 (2026-09-22): the unscoped pattern killed the CPU-only preprocess sidecar on 8081 mid-run.
# Entry point for the Windows Scheduled Task "SAEA-Serving": owns the resident serving wrapper for as long as it lives,
# independent of any Claude Code process or interactive wsl.exe session. Reaps orphans, records a stale stop if needed,
# starts the wrapper, archives the stale stop record once the new session.json exists, then waits on the wrapper.
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
saea_data_root_init || exit 70
DATA=$SAEA_DATA_ROOT
S=$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
source /home/chao/.venvs/speechrl/bin/activate
cd "$MAIN" || exit 1
LOG=/home/chao/serving-task-$(date -u +%Y%m%dT%H%M%SZ).log
exec > "$LOG" 2>&1
echo "task entry $(date -u +%FT%TZ) HEAD $(git rev-parse --short HEAD)"
for p in $(pgrep -f "core.session.serving start"); do kill -9 $p && echo "killed orphan wrapper $p"; done
for p in $(pgrep -f "llama-server --host 127.0.0.1 --port 8080"); do kill -9 $p && echo "killed orphan server $p"; done
sleep 2
if [ -f "$S/session.json" ] && [ ! -f "$S/session-stop.json" ]; then
  echo "recording the stale stop of the previous session"; bash scripts/serving_session.sh stop --session-id serving-slurp-native-candidate-five-train-a-np4-v1 2>&1 | tail -2
fi
T0=$(date +%s)
bash scripts/serving_session.sh start q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1 \
  --session-id serving-slurp-native-candidate-five-train-a-np4-v1 --runtime-root /home/chao > /home/chao/serving-slurp-native-np4-$(date -u +%Y%m%dT%H%M%SZ).log 2>&1 &
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
