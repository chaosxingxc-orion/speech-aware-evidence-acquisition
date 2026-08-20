#!/usr/bin/env bash
# Run a SEQUENCE of flight stages as CHILD processes of this script (never
# detached). Usage: run_chain.sh <attempt_id|NEW> stage [stage ...]
# With NEW, the first stage must be 'preflight' and the minted attempt id is
# echoed and reused for the rest of the chain.
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"

ATTEMPT="$1"; shift
STUDY_COMMIT="$(git -C "$REPO" rev-parse HEAD)"
if [ -n "$(git -C "$REPO" status --porcelain)" ]; then
  echo "REFUSING: study checkout is dirty"; git -C "$REPO" status --porcelain; exit 2
fi
echo "study HEAD (clean): $STUDY_COMMIT"
nvidia-smi --query-gpu=clocks.sm,clocks.max.sm,memory.used,utilization.gpu,pstate --format=csv

for STAGE in "$@"; do
  echo "=================== STAGE $STAGE ==================="
  ARGS=(--stage "$STAGE" --study-commit "$STUDY_COMMIT")
  if [ "$ATTEMPT" != "NEW" ]; then ARGS+=(--attempt-id "$ATTEMPT"); fi
  set +e
  python launch_pemb3m_flight.py "${ARGS[@]}" 2>&1 | tee -a "$SCRATCH/flight.log" | grep -vE "Loading weights:|it/s\]$"
  CODE=${PIPESTATUS[0]}
  set -e
  if [ "$CODE" != "0" ]; then echo "STAGE $STAGE FAILED (exit $CODE)"; break; fi
  if [ "$ATTEMPT" == "NEW" ]; then
    ATTEMPT="$(grep -oE 'ATTEMPT_ID=[A-Za-z0-9._-]+' "$SCRATCH/flight.log" | tail -1 | cut -d= -f2)"
    echo "MINTED ATTEMPT_ID=$ATTEMPT"
  fi
  nvidia-smi --query-gpu=clocks.sm,memory.used,utilization.gpu,pstate --format=csv,noheader
done

echo "=================== POST-CHAIN ==================="
echo "ATTEMPT=$ATTEMPT"
pgrep -a llama-server || echo "no llama-server running"
ss -ltnp 2>/dev/null | grep -E ':(8080|8093|8094)\b' || echo "ports 8080/8093/8094 free"
git -C "$REPO" status --porcelain || echo "study tree clean"
exit $CODE
