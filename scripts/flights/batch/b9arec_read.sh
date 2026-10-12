#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# B9a-rec read by script (decision 58): one factor (the Acquisition node, kind (a)) against the sealed PLAN arm at the plan's own null (PLANr).
PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
SRC=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-DEFAULT-PLAN-LOCK-REPLICATE-PAIRED-ANALYSIS-V1
ROOT=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-PLAN-ACQUISITION-B9A-RECOVERY-PAIRED-ANALYSIS-V1
mkdir -p $ROOT && cp $SRC/plan_cell_read.py $ROOT/plan_cell_read.py && cd $ROOT || exit 1
sha256sum plan_cell_read.py | cut -c1-16
for stage in stop structural contrast lock efficiency frontier verdict; do
  echo "== stage $stage $(date -u +%T)"
  $PY plan_cell_read.py --stage $stage \
    --arm-run SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-RECOVERY-V1 \
    --arm-attempt attempt-slurp-native-plan-acquisition-b9a-recovery-train-fold-a-generation-v1 \
    --arm-fit-run SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-RECOVERY-FIT-V1 --arm-label B9a-rec \
    --comparator-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1 \
    --comparator-attempt attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1 \
    --comparator-fit-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-FIT-V1 --comparator-label PLAN \
    --lock-run SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1 \
    --lock-attempt attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-recovery-v1 \
    --own-null-left-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1 \
    --own-null-left-attempt attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1 --own-null-left-label "cell PLAN" \
    --own-null-right-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1 \
    --own-null-right-attempt attempt-slurp-native-default-plan-lock-replicate-train-fold-a-generation-v1 --own-null-right-label "cell PLANr" \
    --package-dir /mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/docs/readiness/2026-09-22-slurp-plan-acquisition-b9a-recovery-v1 \
    --h-slu 1.2485 --h-intent 0.9943 --normaliser-id saea-deliver-normalise-v3 \
    --recipe-id slurp-plan-acquisition-b9a-recovery-paired-analysis-v1 \
    --title "Cell B9a-rec: the Acquisition node, kind (a) knowledge-requery, one factor on the locked default-plan base (the one recovery after item E36)" \
    --registered $ROOT/registered-b9arec.json --analysis-root $ROOT > $ROOT/stage-$stage.log 2>&1 || { echo "STAGE $stage FAILED"; tail -5 $ROOT/stage-$stage.log | cut -c1-300; exit 2; }
done
echo "B9a-rec read done $(date -u +%T)"; ls $ROOT
