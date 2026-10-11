#!/bin/bash
# Stop the SUPERSEDED Thinking serving session of the 266-E read (completion cap 2,048) so the amended session (cap 8,192) can start.
#
# WHY A SEPARATE TOOL. The cap lives in the model fragment's decoding_params, and the flight attaches to a resident session by fragment name AND
# sha256, so the amended Thinking geometry (target think-np4) has a NEW fragment and a NEW session id. scripts/flights/batch/serving_swap.sh maps the
# resident session onto its geometry table and refuses ("session ... is not in the geometry table; stop it by hand", exit 10) when the resident
# session is the retired one, for a full swap and for --stop-only alike. This script is that hand step, made exact: the same clean stop, wrapper
# kill, port-free wait and Windows-task stop serving_swap.sh performs for any geometry, aimed at the retired session id. It starts NOTHING.
#
# Coordinator-run only; agents never run it. Order of the cap-amendment swap (the package README, "Recovery rec1: the four-row Thinking smoke"):
#   bash scripts/flights/direct/serving_stop_think_superseded.sh --dry-run
#   bash scripts/flights/direct/serving_stop_think_superseded.sh
#   bash scripts/flights/batch/serving_swap.sh think-np4 --start-only      # the card is empty, so --start-only is the clean start
#
# Refusals: a generation flight alive (7); a different session recorded resident (10); the retired session cannot be stopped cleanly (11).
# A retired session that is not resident is a no-op (exit 0), so the script is safe to re-run.
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
# shellcheck source=../batch/serving_lib.sh
source "$REPO/scripts/flights/batch/serving_lib.sh"

RETIRED_SID=serving-slurp-thinking-direct-fold-b-np4-v1
RETIRED_TASKS="SAEA-Serving-THINK SAEA-Monitor-THINK"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1
say() { echo "$(date -u +%FT%TZ) stop-superseded-think: $*"; }

if REASONS=$(saea_flight_alive); then say "REFUSED (7): $REASONS"; exit 7; fi
SS=${SAEA_SERVING_SESSION:-$REPO/scripts/serving_session.sh}
export SPEECHRL_DATA_DIR=$SAEA_DATA PYTHONDONTWRITEBYTECODE=1
RES=$(bash "$SS" resident 2>&1)
RES_RC=$?
CUR_SID=
if [ "$RES_RC" = 0 ]; then
  CUR_SID=$(printf '%s' "$RES" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("session_id") or "")' 2>/dev/null)
  if [ "$CUR_SID" != "$RETIRED_SID" ]; then
    say "REFUSED (10): the resident session is '$CUR_SID', not the retired Thinking session $RETIRED_SID; use scripts/flights/batch/serving_swap.sh"
    exit 10
  fi
elif [ "$RES_RC" != 3 ]; then
  say "REFUSED (10): serving_session.sh resident exit $RES_RC: $RES"; exit 10
fi
if [ -z "$CUR_SID" ]; then
  say "no session is recorded resident; nothing to stop (no-op)"
  exit 0
fi
say "resident: $RETIRED_SID (completion cap 2,048, superseded by the amended think-np4 geometry)"
if [ "$DRY" = 1 ]; then
  say "DRY RUN: would stop the session (serving_session.sh stop), kill its wrapper, wait for port $SAEA_SERVING_PORT to be free, then stop the Windows tasks: $RETIRED_TASKS"
  exit 0
fi
bash "$SS" stop --session-id "$RETIRED_SID" 2>&1 | tail -3
sleep 5
for p in $(pgrep -f -- "[c]ore\.session\.serving start .*--session-id $RETIRED_SID( |$)" 2>/dev/null); do
  kill "$p" 2>/dev/null && say "killed leftover wrapper $p"
done
FREE=0
for _ in $(seq 1 30); do
  if [ -z "$(saea_port_server_pids)" ]; then FREE=1; break; fi
  sleep 2
done
if [ "$FREE" != 1 ]; then say "FAILED (11): port $SAEA_SERVING_PORT is still held: $(saea_port_server_pids)"; exit 11; fi
say "port $SAEA_SERVING_PORT is free"
PS=$(saea_powershell)
for name in $RETIRED_TASKS; do
  "$PS" -NoProfile -File "$SAEA_TASK_PS1_WIN" -Name "$name" -Stop 2>&1 | tr -d '\r' | sed 's/^/    ps: /'
done
say "stopped; the card is empty and the amended Thinking session may be started (serving_swap.sh think-np4 --start-only)"
exit 0
