#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Usage: prune_read.sh <prune-reviewer1|prune-review-off> -- the decision-85 pruning cell read (decision 58 by script): one factor on the
# R-PRIM base against the sealed R-PRIM arm at the plan's own null (PLAN vs PLANr). Driver = the repo copy scripts/analysis/plan_cell_read.py.
NAME=$1; case $NAME in prune-reviewer1) TAG=PRUNE-REVIEWER1; SHORT=P1;; prune-review-off) TAG=PRUNE-REVIEW-OFF; SHORT=P0;; *) echo "unknown cell"; exit 2;; esac
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
ROOT=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-$TAG-PAIRED-ANALYSIS-V1
mkdir -p $ROOT && cp $MAIN/scripts/analysis/plan_cell_read.py $ROOT/plan_cell_read.py && cp $MAIN/docs/readiness/2026-09-22-slurp-$NAME-v1/registered-facts-v1.json $ROOT/registered-$NAME.json && cd $ROOT || exit 1
sha256sum plan_cell_read.py | cut -c1-16
for stage in stop structural contrast lock efficiency frontier verdict; do
  echo "== stage $stage $(date -u +%T)"
  $PY plan_cell_read.py --stage $stage \
    --arm-run SAEA-SLURP-NATIVE-$TAG-V1 --arm-attempt attempt-slurp-native-$NAME-train-fold-a-generation-v1 \
    --arm-fit-run SAEA-SLURP-NATIVE-$TAG-FIT-V1 --arm-label $SHORT \
    --comparator-run SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-V1 --comparator-attempt attempt-slurp-native-review-primitives-train-fold-a-generation-v1 \
    --comparator-fit-run SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-FIT-V1 --comparator-label R-PRIM \
    --lock-run SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1 \
    --lock-attempt attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-recovery-v1 \
    --own-null-left-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1 --own-null-left-attempt attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1 --own-null-left-label "cell PLAN" \
    --own-null-right-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1 --own-null-right-attempt attempt-slurp-native-default-plan-lock-replicate-train-fold-a-generation-v1 --own-null-right-label "cell PLANr" \
    --package-dir $MAIN/docs/readiness/2026-09-22-slurp-$NAME-v1 \
    --h-slu 1.2485 --h-intent 0.9943 --normaliser-id saea-deliver-normalise-v3 \
    --recipe-id slurp-$NAME-paired-analysis-v1 \
    --title "Cell $SHORT (owner decision 85): pruning the review loop on the measurable-Reviewer base R-PRIM (decision 97)" \
    --registered $ROOT/registered-$NAME.json --analysis-root $ROOT > $ROOT/stage-$stage.log 2>&1 || { echo "STAGE $stage FAILED"; tail -5 $ROOT/stage-$stage.log | cut -c1-300; exit 2; }
done
echo "$SHORT read done $(date -u +%T)"; ls $ROOT
