#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Usage: cell1_read.sh <arm|twin> -- the CELL-1 read (Stage-3 S3-6 / S3-4s; owner decisions 83, 99, 101, 106; decision 58 by script):
# the locked plan plus the per-node stage3-deltas-v1r store against the sealed PLAN arm at the plan's own null (PLAN vs PLANr);
# the twin read is the arm read with one input changed (analysis-recipe-v1.json, twin_invocation). Driver = the repo copy
# scripts/analysis/plan_cell_read.py. Model-free: zero model / tokenizer / encoder / server contacts; scorer contacts only through the
# sealed per-sample scores. Registered as SAEA-SLURP-STAGE3-DELTA-CELL-{R01,TWIN}-PAIRED-ANALYSIS-V1 (model-free-check rows).
# 2026-09-23: the arm attempt is the RECOVERY id (attempt-slurp-native-stage3-delta-cell-r01-v1-generation-recovery).
# The first arm attempt aborted after 304 contacts and sealed no outputs; the registered package files
# (generation-plan-registered-v1.json, protocol-registered-v1.json, analysis-recipe-v1.json) keep the
# original id they were registered with, exactly as the smoke's own recovery did, and the README note
# records the divergence. The run id, the comparator and the estimator are unchanged.
WHICH=$1
case $WHICH in
  arm) ARM_RUN=SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1; ARM_ATTEMPT=attempt-slurp-native-stage3-delta-cell-r01-v1-generation-recovery-relaunch-2; ARM_FIT=SAEA-SLURP-STAGE3-DELTA-CELL-R01-FIT-V1; LABEL="cell CELL-1 (the locked plan plus the per-node stage3-deltas store)"; TAG=R01;;
  twin) ARM_RUN=SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-V1; ARM_ATTEMPT=attempt-slurp-native-stage3-delta-cell-r01-v1-twin; ARM_FIT=SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-FIT-V1; LABEL="the CELL-1 derangement twin (form control)"; TAG=TWIN;;
  *) echo "usage: cell1_read.sh arm|twin"; exit 2;;
esac
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
PKG=$MAIN/docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1
ROOT=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-$TAG-PAIRED-ANALYSIS-V1
LOCK_ATTEMPT=${LOCK_ATTEMPT:-attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-recovery-v1}
mkdir -p "$ROOT" && cp "$MAIN/scripts/analysis/plan_cell_read.py" "$ROOT/plan_cell_read.py" && cp "$PKG/registered-facts-v1.json" "$ROOT/registered-cell1.json" && cd "$ROOT" || exit 1
sha256sum plan_cell_read.py | cut -c1-16
for stage in stop structural contrast lock efficiency frontier verdict; do
  echo "== stage $stage $(date -u +%T)"
  $PY plan_cell_read.py --stage $stage \
    --arm-run $ARM_RUN --arm-attempt $ARM_ATTEMPT --arm-fit-run $ARM_FIT --arm-label "$LABEL" \
    --comparator-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1 --comparator-attempt attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1 \
    --comparator-fit-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-FIT-V1 --comparator-label "the sealed PLAN arm (the locked v2.0 plan)" \
    --lock-run SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1 --lock-attempt "$LOCK_ATTEMPT" \
    --own-null-left-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1 --own-null-left-attempt attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1 --own-null-left-label "cell PLAN" \
    --own-null-right-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1 --own-null-right-attempt attempt-slurp-native-default-plan-lock-replicate-train-fold-a-generation-v1 --own-null-right-label "cell PLANr" \
    --package-dir "$PKG" \
    --h-slu 1.2485 --h-intent 0.9943 --normaliser-id saea-deliver-normalise-v3 \
    --recipe-id slurp-stage3-delta-cell-$WHICH-paired-analysis-v1 \
    --title "Cell CELL-1 ($WHICH; Stage-3 S3-6 / S3-4s): the locked plan plus the per-node stage3-deltas-v1r store against the sealed PLAN arm" \
    --registered "$ROOT/registered-cell1.json" --analysis-root "$ROOT" > "$ROOT/stage-$stage.log" 2>&1 || { echo "STAGE $stage FAILED"; tail -5 "$ROOT/stage-$stage.log" | cut -c1-300; exit 2; }
done
echo "CELL-1 $WHICH read done $(date -u +%T)"; ls "$ROOT"
