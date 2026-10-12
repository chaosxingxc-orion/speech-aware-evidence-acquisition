#!/bin/bash
# GENERIC entry point for a Windows Scheduled Task that runs one registered packet-promotion roster of
# scripts/slurp_evo_fold_preprocess.py on the CPU-only featcache sidecar (-ngl 0, 0 GPU-h) beside the resident GPU
# session, with a host-memory watchdog: available memory below 6 GB stops the preprocess.
#
# The roster-parameterised sibling of scripts/flights/batch/prep_r01_task_entry.sh, written for owner decision 107 of
# 2026-09-23 (the expanded DEV side). The R01 entry is left exactly as it is: its run is sealed.
#
# Environment (all optional but PREP_ROSTER):
#   PREP_ROSTER           the roster key in PREPROCESS_ROSTERS, e.g. devel-remainder          (required)
#   PREP_REPO             the clean checkout to run from            (default: the main checkout)
#   PREP_WORKERS          encode concurrency; refused above the roster's own sidecar -np      (default 4)
#   PREP_PROMOTE_WORKERS  promotion workers                                                   (default 8)
#   PREP_SIDECAR_FRAGMENT asserted against the roster's REGISTERED fragment; it is never an override, because the
#                         fragment enters the composed config hash and therefore the protocol hash the exposure row
#                         pins. A disagreement refuses the launch.
#   PREP_OUT              the check directory for the driver report (default: derived from the roster key)
#   PREP_MEMORY_FLOOR_GB  watchdog floor in GB                                                (default 6)
#
# It authorises nothing: the roster's exposure row must already be countersigned, and the run makes exactly the
# contacts that row declares.
set -u
ROSTER=${PREP_ROSTER:?PREP_ROSTER is required (a key of PREPROCESS_ROSTERS)}
REPO=${PREP_REPO:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
saea_data_root_init || exit 70
DATA=$SAEA_DATA_ROOT
WORKERS=${PREP_WORKERS:-4}
PROMOTE_WORKERS=${PREP_PROMOTE_WORKERS:-8}
FLOOR=${PREP_MEMORY_FLOOR_GB:-6}
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
source /home/chao/.venvs/speechrl/bin/activate
cd "$REPO" || exit 1
LOG=/home/chao/prep-$ROSTER-$(date -u +%Y%m%dT%H%M%SZ).log
WATCHDOG_LOG=/home/chao/prep-$ROSTER-watchdog.log
exec > "$LOG" 2>&1
echo "task entry $(date -u +%FT%TZ) roster $ROSTER HEAD $(git rev-parse --short HEAD) dirt $(git status --short | grep -vc '^??')"
[ "$(git status --short | grep -vc '^??')" = "0" ] || { echo "dirty tree; refusing"; exit 2; }

# The roster's own registration is the single source of truth for the run id, the sidecar fragment and the slot count.
FACTS=$(python -B scripts/flights/batch/prep_generic_steps.py roster-facts --repo-root "$REPO" --roster "$ROSTER" \
          ${PREP_SIDECAR_FRAGMENT:+--expect-sidecar-fragment "$PREP_SIDECAR_FRAGMENT"} \
          --expect-workers "$WORKERS") || { echo "ROSTER FACTS REFUSED"; echo "$FACTS"; exit 6; }
echo "$FACTS"
eval "$FACTS"
OUT=${PREP_OUT:-docs/checks/speech-aware-evidence-acquisition/$(date -u +%Y-%m-%d)-slurp-$ROSTER-packets}
mkdir -p "$OUT"

python -B scripts/slurp_evo_fold_preprocess.py --roster "$ROSTER" --preflight-only --workers "$WORKERS" \
  || { echo "PREFLIGHT FAILED"; exit 3; }

# Owner decision 162 (enforced for decision 163): every serving geometry starts BEFORE any CPU sidecar, and a sidecar
# runs only beside a resident GPU session. On 2026-09-27 a resident sidecar held the host under the serving start
# guard and two geometry restarts failed with the card empty. Refuse while no GPU session is resident and running, or
# while a serving swap (serving_swap.sh) holds its pending marker.
# shellcheck source=serving_lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/serving_lib.sh"
saea_sidecar_admission "${SAEA_SERVING_SESSION:-$REPO/scripts/serving_session.sh}" || { echo "SIDECAR REFUSED"; exit 10; }

(
  while true; do
    AV=$(free -g | awk '/^Mem:/{print $7}')
    echo "watchdog $(date -u +%T) available_gb=$AV" >> "$WATCHDOG_LOG"
    if [ "$AV" -lt "$FLOOR" ]; then
      echo "WATCHDOG: available memory ${AV} GB < ${FLOOR} GB; stopping the preprocess $(date -u +%FT%TZ)" | tee -a "$WATCHDOG_LOG"
      pkill -f "slurp_evo_fold_preprocess.py --roster $ROSTER --run"
      exit 0
    fi
    sleep 10
  done
) &
WD=$!
python -B scripts/slurp_evo_fold_preprocess.py --roster "$ROSTER" --run \
  --workers "$WORKERS" --promote-workers "$PROMOTE_WORKERS" \
  --output "$OUT/preprocess-report-$ROSTER.json"
RC=$?
kill $WD 2>/dev/null
echo "preprocess exit $RC $(date -u +%FT%TZ)"
ls -la "$OUT" 2>&1 | tail -4
if [ -n "${PREP_PROMOTION_RECEIPT:-}" ]; then
  ls -la "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/$PREP_PROMOTION_RECEIPT" 2>&1 | tail -2
fi
exit $RC
