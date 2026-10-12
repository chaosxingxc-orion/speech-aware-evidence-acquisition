#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Entry point for the Windows Scheduled Task "SAEA-Prep-R01" (owner decisions 93/94, 2026-09-22): the registered R01
# packet promotion (run SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS) on the CPU-only featcache sidecar (-ngl 0, 0 GPU-h),
# beside the resident GPU session, with a host-memory watchdog: available memory below 6 GB stops the preprocess.
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=$SAEA_DATA_ROOT
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN:$MAIN/src
source /home/chao/.venvs/speechrl/bin/activate
cd "$MAIN" || exit 1
LOG=/home/chao/prep-r01-$(date -u +%Y%m%dT%H%M%SZ).log
exec > "$LOG" 2>&1
echo "task entry $(date -u +%FT%TZ) HEAD $(git rev-parse --short HEAD) dirt $(git status --short | grep -vc '^??')"
[ "$(git status --short | grep -vc '^??')" = "0" ] || { echo "dirty tree; refusing"; exit 2; }
OUT=docs/checks/speech-aware-evidence-acquisition/2026-09-22-slurp-stage3-construction-r01-packets
mkdir -p "$OUT"
python -B scripts/slurp_evo_fold_preprocess.py --roster ${PREP_ROSTER:-stage3-construction-r01-recovery} --preflight-only || { echo "PREFLIGHT FAILED"; exit 3; }
(
  while true; do
    AV=$(free -g | awk '/^Mem:/{print $7}')
    echo "watchdog $(date -u +%T) available_gb=$AV" >> /home/chao/prep-r01-watchdog.log
    if [ "$AV" -lt 6 ]; then
      echo "WATCHDOG: available memory ${AV} GB < 6 GB; stopping the preprocess $(date -u +%FT%TZ)" | tee -a /home/chao/prep-r01-watchdog.log
      pkill -f "slurp_evo_fold_preprocess.py --roster ${PREP_ROSTER:-stage3-construction-r01-recovery} --run"
      exit 0
    fi
    sleep 10
  done
) &
WD=$!
python -B scripts/slurp_evo_fold_preprocess.py --roster ${PREP_ROSTER:-stage3-construction-r01-recovery} --run --workers 4 --promote-workers 8 --output "$OUT/preprocess-report-${PREP_ROSTER:-stage3-construction-r01-recovery}.json"
RC=$?
kill $WD 2>/dev/null
echo "preprocess exit $RC $(date -u +%FT%TZ)"
ls -la "$OUT" /home/chao/feat-cache/slurp-q4km-packets-04ccc72a/STAGE3-CONSTRUCTION-R01-promotion.json 2>&1 | tail -4
exit $RC
