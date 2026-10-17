#!/bin/bash
# The strict readiness wait for one resident serving geometry (owner decision 163; defect 3 of 2026-09-27: the queue
# logged "np4 back: rc 0" while slurp_wait_ready.sh had printed SESSION STOPPED EARLY -- the old waits exited 0 on an
# early stop and on a timeout, and took the PREVIOUS session's stop record for this start's).
#
#   serving_wait_ready.sh <slurp-np4|a2t-np3|e21-np4|det-np1|think-np4|think-budget-np4|think-budget7168-np4> [--since EPOCH] [--timeout SEC] [--poll SEC]
#
# READY (exit 0) only when serving_ready_probe.py proves all of: session.json of this start (started at or after
# --since), no session-stop.json (a stale one from an earlier session must have been archived by the task entry,
# or a flight could not attach), GET /health ok, GET /props slot geometry equal to the fragment's -np and -c/-np,
# and a monitor sample with server_ok stamped after the start.
# Exit 2 timeout, 3 this start stopped (a stop record of this start, or a refusal line in a task/server log written
# since the start), 4 wrong geometry, 64 usage. Never exits 0 on anything but READY.
#
# --since defaults to the start time encoded in the newest task-entry log name of the geometry (the task entry names
# its log by its own start), so the legacy callers (slurp_wait_ready.sh, a2t_wait_ready.sh, e21_wait_ready.sh with
# no arguments) no longer take a stale stop record for a failed start.
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
# shellcheck source=serving_lib.sh
source "$HERE/serving_lib.sh"
TARGET=${1:-}
shift || true
SINCE=
TIMEOUT=600
POLL=5
while [ $# -gt 0 ]; do
  case "$1" in
    --since) SINCE=${2:-}; shift ;;
    --timeout) TIMEOUT=${2:-}; shift ;;
    --poll) POLL=${2:-}; shift ;;
    *) echo "serving_wait_ready: unknown argument $1"; exit 64 ;;
  esac
  shift
done
saea_geometry "$TARGET" || { echo "usage: serving_wait_ready.sh <$(echo $SAEA_TARGETS | tr ' ' '|')> [--since EPOCH] [--timeout SEC] [--poll SEC]"; exit 64; }
if [ -z "$SINCE" ]; then
  NEWEST=$(cd "$SAEA_RUNTIME_ROOT" 2>/dev/null && ls -1 $G_TASK_LOG_GLOB 2>/dev/null | sort | tail -1)
  STAMP=$(echo "$NEWEST" | grep -oE '[0-9]{8}T[0-9]{6}Z' | tail -1)
  if [ -n "$STAMP" ]; then
    SINCE=$(date -u -d "${STAMP:0:4}-${STAMP:4:2}-${STAMP:6:2} ${STAMP:9:2}:${STAMP:11:2}:${STAMP:13:2}" +%s 2>/dev/null || echo 0)
  else
    SINCE=0
  fi
fi
FRAG=$REPO/configs/model/$G_FRAGMENT.json
S=$G_SESSION_DIR
URL=http://$SAEA_SERVING_HOST:$SAEA_SERVING_PORT
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
DEADLINE=$(( $(date +%s) + TIMEOUT ))
echo "wait $TARGET session $G_SID since $SINCE ($(date -u -d "@${SINCE%.*}" +%FT%TZ 2>/dev/null)) timeout ${TIMEOUT}s"

tail_logs() {
  local f
  for f in $(cd "$SAEA_RUNTIME_ROOT" 2>/dev/null && ls -1t $G_TASK_LOG_GLOB $G_SERVER_LOG_GLOB 2>/dev/null | head -2); do
    echo "--- $f"; tail -5 "$SAEA_RUNTIME_ROOT/$f" | cut -c1-300
  done
}

while true; do
  curl -s -m 3 "$URL/health" > "$TMP/health" 2>/dev/null || : > "$TMP/health"
  curl -s -m 5 "$URL/props" > "$TMP/props" 2>/dev/null || : > "$TMP/props"
  tail -n 3 "$S/monitor.jsonl" > "$TMP/monitor" 2>/dev/null || : > "$TMP/monitor"
  VERDICT=$(python3 "$HERE/serving_ready_probe.py" --session-dir "$S" --session-id "$G_SID" --fragment-json "$FRAG" \
    --since "$SINCE" --health-file "$TMP/health" --props-file "$TMP/props" --monitor-tail-file "$TMP/monitor" \
    --refusal-log-glob "$SAEA_RUNTIME_ROOT/$G_TASK_LOG_GLOB" --refusal-log-glob "$SAEA_RUNTIME_ROOT/$G_SERVER_LOG_GLOB")
  RC=$?
  case $RC in
    0) echo "$G_LABEL SESSION READY"
       echo "slots $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("total_slots"))' "$TMP/props" 2>/dev/null)"
       echo "$VERDICT"
       command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=memory.used --format=csv,noheader
       exit 0 ;;
    3) echo "SESSION STOPPED EARLY"; echo "$VERDICT"; tail -c 600 "$S/session-stop.json" 2>/dev/null; echo; tail_logs; exit 3 ;;
    4) echo "WRONG GEOMETRY"; echo "$VERDICT"; exit 4 ;;
    1) ;;
    *) echo "READINESS PROBE FAILED (exit $RC)"; echo "$VERDICT"; exit 64 ;;
  esac
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then
    echo "TIMEOUT"; echo "$VERDICT"; tail_logs; exit 2
  fi
  sleep "$POLL"
done
