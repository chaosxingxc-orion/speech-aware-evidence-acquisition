#!/usr/bin/env bash
# Block until one of the given patterns appears in flight.log, or the poll
# budget runs out. Usage: wait_for.sh <polls> <pattern>
source "$(dirname "$0")/env.sh"
F="$SCRATCH/flight.log"
POLLS="${1:-100}"
PATTERN="${2:-STAGE .* OK}"
i=0
while [ "$i" -lt "$POLLS" ]; do
  if grep -qE "$PATTERN|FAILED|Traceback|REFUS" "$F" 2>/dev/null; then break; fi
  i=$((i + 1))
  sleep 5
done
tail -40 "$F"
echo "--- waited $((i * 5))s ---"
