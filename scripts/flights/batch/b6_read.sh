#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
cd $MAIN || exit 1
ROOT=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B6-DEV2000-ADDED-PAIRED-ANALYSIS-V1
for stage in stop structural contrast efficiency verdict; do
  echo "== stage $stage $(date -u +%T)"
  $PY -B scripts/analysis/slurp_paired_roster_read.py --stage $stage \
    --left-run SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1 --left-attempt attempt-slurp-direct-max512-dev2000-added-generation-v1 --left-label direct \
    --right-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1 --right-attempt attempt-slurp-native-default-plan-dev2000-added-generation-v1 --right-label plan \
    --scorer-id slurp-slu-official --roster docs/receipts/rosters/slurp-dev-2000-added-v1.json --cluster-key utterance_id \
    --analysis-root $ROOT --repo-root $MAIN --data-root $SPEECHRL_DATA_DIR --seed 20260915 --draws 10000 \
    --recipe-id docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1/analysis-recipe-v1.json \
    --title "Cell B6: the locked v2.0 default plan against the bare core on the fresh DEV-2000-ADDED roster (paired, descriptive)" > $ROOT.stage-$stage.log 2>&1 || { echo "STAGE $stage FAILED"; tail -6 $ROOT.stage-$stage.log | cut -c1-300; exit 2; }
done
mv $ROOT.stage-*.log $ROOT/ 2>/dev/null
echo "B6 read done $(date -u +%T)"; ls $ROOT
