#!/bin/bash
# Entry point for the THINK serving session (owner decision 266-E): the np4 / c98304 / q8_0-KV geometry of the resident SLURP
# session, with the Thinking GGUF, its OWN speech-packet root, an 8192-token completion cap (amended from 2048 at the decode-cost sign-off) and --reasoning-format deepseek
# (model fragment q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max8192-v1). A parameterised sibling of
# scripts/flights/det/serving_task_entry_det.sh, run by the Windows Scheduled Task SAEA-Serving-THINK that
# scripts/flights/batch/serving_swap.sh starts (geometry target think-np4). Owns the wrapper independently of any Claude Code
# process or interactive wsl.exe session; reaps orphans scoped to port 8080, records a stale stop if needed, starts the wrapper,
# archives the stale stop record once the new session.json exists, then waits on the wrapper.
#
# PRECONDITION: the np4 session serving-slurp-native-candidate-five-train-a-np4-v1 has been stopped cleanly (serving_swap.sh does
# this) and the card is free. core.session.serving refuses to start a second resident session, so a forgotten np4 session is a
# refusal here, not a second server.
#
# Agents never run this. A flight attaches automatically: core.flight.FlightRuntime.serve finds the resident session and compares
# the identity fields session.json records (model fragment and its sha256, server_argv flag by flag, env).
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
saea_data_root_init || exit 70
DATA=$SAEA_DATA_ROOT
FRAGMENT=q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max8192-v1
SESSION=serving-slurp-thinking-direct-fold-b-np4-max8192-v1
S=$DATA/serving/$SESSION
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
source /home/chao/.venvs/speechrl/bin/activate
cd "$MAIN" || exit 1
LOG=/home/chao/serving-task-think-$(date -u +%Y%m%dT%H%M%SZ).log
exec > "$LOG" 2>&1
echo "task entry $(date -u +%FT%TZ) HEAD $(git rev-parse --short HEAD) fragment $FRAGMENT session $SESSION"
NP4=$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1
if [ -f "$NP4/session.json" ] && [ ! -f "$NP4/session-stop.json" ]; then
  echo "the np4 session is still recorded resident; stop it cleanly first (scripts/flights/batch/serving_swap.sh think-np4 does); refusing"; exit 6
fi
for p in $(pgrep -f "core.session.serving start"); do kill -9 $p && echo "killed orphan wrapper $p"; done
for p in $(pgrep -f "llama-server --host 127.0.0.1 --port 8080"); do kill -9 $p && echo "killed orphan server $p"; done
sleep 2
if [ -f "$S/session.json" ] && [ ! -f "$S/session-stop.json" ]; then
  echo "recording the stale stop of the previous THINK session"; bash scripts/serving_session.sh stop --session-id $SESSION 2>&1 | tail -2
fi
T0=$(date +%s)
bash scripts/serving_session.sh start $FRAGMENT --session-id $SESSION --runtime-root /home/chao > /home/chao/serving-slurp-think-np4-$(date -u +%Y%m%dT%H%M%SZ).log 2>&1 &
W=$!
echo "wrapper pid $W"
# Owner decision 163: wait for the new session.json as long as the wrapper lives, not a fixed 90 s.
for i in $(seq 1 450); do sleep 2; [ -f "$S/session.json" ] && [ "$(stat -c %Y "$S/session.json")" -ge "$T0" ] && break; kill -0 $W 2>/dev/null || break; done
if [ -f "$S/session.json" ] && [ "$(stat -c %Y "$S/session.json")" -ge "$T0" ] && [ -f "$S/session-stop.json" ]; then
  A=$S/archive-stopped-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p "$A"; mv "$S/session-stop.json" "$S/.session-stop.lock" "$A/" 2>/dev/null && echo "stale stop record archived to $A"
fi
echo "waiting on the wrapper $(date -u +%FT%TZ)"
wait $W
echo "wrapper exited $? $(date -u +%FT%TZ)"
