#!/usr/bin/env bash
# Run ONE flight stage as a CHILD process of this script (never detached:
# detached WSL jobs die on this host). Usage: run_stage.sh <stage> [attempt_id]
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"

STAGE="$1"
ATTEMPT="${2:-}"
STUDY_COMMIT="$(git -C "$REPO" rev-parse HEAD)"

if [ -n "$(git -C "$REPO" status --porcelain)" ]; then
  echo "REFUSING: study checkout is dirty; a flight must run against a clean, frozen HEAD"
  git -C "$REPO" status --porcelain
  exit 2
fi
echo "study HEAD (clean): $STUDY_COMMIT"
nvidia-smi --query-gpu=clocks.sm,clocks.max.sm,memory.used,utilization.gpu,pstate --format=csv

ARGS=(--stage "$STAGE" --study-commit "$STUDY_COMMIT")
if [ -n "$ATTEMPT" ]; then ARGS+=(--attempt-id "$ATTEMPT"); fi

set +e
python launch_pemb3m_flight.py "${ARGS[@]}" 2>&1 | tee -a "$SCRATCH/flight.log"
CODE=${PIPESTATUS[0]}
set -e
echo "STAGE_EXIT=$CODE"

echo "--- post-stage state ---"
pgrep -a llama-server || echo "no llama-server running"
ss -ltnp 2>/dev/null | grep -E ':(8080|8093|8094)\b' || echo "ports 8080/8093/8094 free"
nvidia-smi --query-gpu=clocks.sm,memory.used,utilization.gpu,pstate --format=csv,noheader
git -C "$REPO" status --porcelain || true
exit $CODE
