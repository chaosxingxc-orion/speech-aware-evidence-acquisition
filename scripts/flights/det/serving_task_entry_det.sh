#!/bin/bash
# Entry point for the DET serving session (the single-slot, prompt-cache-off geometry of cell DET):
# a parameterised sibling of scripts/flights/batch/serving_task_entry.sh, to be run by the coordinator
# as the action of the Windows Scheduled Task that owns the resident serving wrapper (SAEA-Serving
# re-pointed at this script, or a sibling task) for as long as the DET chain lives. Owns the wrapper
# independently of any Claude Code process or interactive wsl.exe session. Reaps orphans scoped to
# port 8080, records a stale stop if needed, starts the wrapper, archives the stale stop record once the
# new session.json exists, then waits on the wrapper.
#
# PRECONDITION: the np4 session serving-slurp-native-candidate-five-train-a-np4-v1 has been stopped
# cleanly (scripts/serving_session.sh stop --session-id ... from the coordinator, its own task stopped
# first) and the card is free. core.session.serving refuses to start a second resident session and
# refuses a listening port, so a forgotten np4 session is a refusal here, not a second server.
#
# Agents never run this. A flight attaches automatically: core.flight.FlightRuntime.serve finds the
# resident session, compares the identity fields session.json records (server_argv flag by flag:
# -np 1, -c 24576, --no-cache-prompt, no --slot-prompt-similarity), and refuses with the exact
# differing field rather than spawning a second server.
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
saea_data_root_init || exit 70
DATA=$SAEA_DATA_ROOT
FRAGMENT=q4km-mmproj-free-slurp-native-bounded-perception-proof-np1-nocache-ctx24k-max512-v1
SESSION=serving-slurp-native-det-np1-nocache-v1
S=$DATA/serving/$SESSION
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
source /home/chao/.venvs/speechrl/bin/activate
cd "$MAIN" || exit 1
LOG=/home/chao/serving-task-det-$(date -u +%Y%m%dT%H%M%SZ).log
exec > "$LOG" 2>&1
echo "task entry $(date -u +%FT%TZ) HEAD $(git rev-parse --short HEAD) fragment $FRAGMENT session $SESSION"
NP4=$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1
if [ -f "$NP4/session.json" ] && [ ! -f "$NP4/session-stop.json" ]; then
  echo "the np4 session is still recorded resident; stop it cleanly first (scripts/serving_session.sh stop --session-id serving-slurp-native-candidate-five-train-a-np4-v1); refusing"; exit 6
fi
for p in $(pgrep -f "core.session.serving start"); do kill -9 $p && echo "killed orphan wrapper $p"; done
for p in $(pgrep -f "llama-server --host 127.0.0.1 --port 8080"); do kill -9 $p && echo "killed orphan server $p"; done
sleep 2
if [ -f "$S/session.json" ] && [ ! -f "$S/session-stop.json" ]; then
  echo "recording the stale stop of the previous DET session"; bash scripts/serving_session.sh stop --session-id $SESSION 2>&1 | tail -2
fi
T0=$(date +%s)
bash scripts/serving_session.sh start $FRAGMENT --session-id $SESSION --runtime-root /home/chao > /home/chao/serving-slurp-det-np1-$(date -u +%Y%m%dT%H%M%SZ).log 2>&1 &
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
