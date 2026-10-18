#!/bin/bash
# Pre-shutdown step of the 322 window (owner rulings 322 A / 331 A, 2026-10-18): refuse (exit 9) while any flight process or the flight
# lock is present; otherwise stop the resident serving session cleanly (serving_swap.sh --stop-only) so `wsl --shutdown` kills no live server.
M=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition; LOG=/home/chao/w322-window.out
say() { echo "$(date -u +%FT%TZ) pre: $*" >> "$LOG"; }
cd "$M" || exit 9
[ "$(pgrep -fc 'core.flight.cli|batch_driver|lease_cli')" = 0 ] || { say "a flight process is alive; window NOT opened"; exit 9; }
[ -e /home/chao/saea-data/speechrl-data/locks/flight.lock ] && { say "flight.lock present; window NOT opened"; exit 9; }
bash scripts/flights/batch/serving_swap.sh --stop-only >> "$LOG" 2>&1; rc=$?
say "serving_swap --stop-only rc=$rc"; exit $rc
