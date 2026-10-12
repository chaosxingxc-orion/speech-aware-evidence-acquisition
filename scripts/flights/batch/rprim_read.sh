#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# R-PRIM read by script (decision 58): one factor (the Reviewer verdict as a closed set of primitives, item E37, decision 84)
# against the sealed PLAN arm at the plan's own null (PLANr). Driver = the repo copy scripts/analysis/plan_cell_read.py.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
ROOT=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-REVIEW-PRIMITIVES-PAIRED-ANALYSIS-V1
mkdir -p $ROOT && cp $MAIN/scripts/analysis/plan_cell_read.py $ROOT/plan_cell_read.py && cp $MAIN/docs/readiness/2026-09-22-slurp-review-primitives-v1/registered-facts-v1.json $ROOT/registered-rprim.json && cd $ROOT || exit 1
sha256sum plan_cell_read.py | cut -c1-16
for stage in stop structural contrast lock efficiency frontier verdict; do
  echo "== stage $stage $(date -u +%T)"
  $PY plan_cell_read.py --stage $stage \
    --arm-run SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-V1 \
    --arm-attempt attempt-slurp-native-review-primitives-train-fold-a-generation-v1 \
    --arm-fit-run SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-FIT-V1 --arm-label R-PRIM \
    --comparator-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1 \
    --comparator-attempt attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1 \
    --comparator-fit-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-FIT-V1 --comparator-label PLAN \
    --lock-run SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1 \
    --lock-attempt attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-recovery-v1 \
    --own-null-left-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1 \
    --own-null-left-attempt attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1 --own-null-left-label "cell PLAN" \
    --own-null-right-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1 \
    --own-null-right-attempt attempt-slurp-native-default-plan-lock-replicate-train-fold-a-generation-v1 --own-null-right-label "cell PLANr" \
    --package-dir $MAIN/docs/readiness/2026-09-22-slurp-review-primitives-v1 \
    --h-slu 1.2485 --h-intent 0.9943 --normaliser-id saea-deliver-normalise-v3 \
    --recipe-id slurp-review-primitives-paired-analysis-v1 \
    --title "Cell R-PRIM: the Reviewer verdict as a closed set of primitives (item E37, owner decision 84), one factor on the locked default-plan base" \
    --registered $ROOT/registered-rprim.json --analysis-root $ROOT > $ROOT/stage-$stage.log 2>&1 || { echo "STAGE $stage FAILED"; tail -5 $ROOT/stage-$stage.log | cut -c1-300; exit 2; }
done
echo "R-PRIM read done $(date -u +%T)"; ls $ROOT
