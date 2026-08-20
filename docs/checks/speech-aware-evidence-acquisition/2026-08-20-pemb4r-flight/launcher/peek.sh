#!/usr/bin/env bash
# Liveness peek at the running launcher: state, open file, cumulative read bytes.
source "$(dirname "$0")/env.sh"
PID=$(pgrep -f "launch_pemb4r_flight.py" | head -1)
if [ -z "$PID" ]; then echo "no launcher process running"; exit 0; fi
echo "pid: $PID"
grep -E "^(State|Name)" "/proc/$PID/status" || true
grep -E "^(read_bytes|rchar)" "/proc/$PID/io" || true
ls -l "/proc/$PID/fd" 2>/dev/null | grep -E "slurp|speechrl-data" | tail -5 || true
echo "--- again in 15s ---"
sleep 15
grep -E "^(read_bytes|rchar)" "/proc/$PID/io" || true
