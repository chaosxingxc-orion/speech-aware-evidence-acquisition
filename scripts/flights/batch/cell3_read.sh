#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Usage: cell3_read.sh <arm|twin|own-null> -- the CELL-3 read (Stage-3 S3-6 iteration 3, the
# coverage-gated application policy on the fresh DEV-2000-ADDED roster; owner decisions 83, 99,
# 101, 106 and 110 pending; decision 58: reads are executed by script).
#
# ORDER MATTERS AND IS PART OF THE REGISTRATION: run `own-null` FIRST. CELL-3's margins h_SLU and
# h_intent are the half-widths PLAN-DEV2000 vs PLANr-DEV2000 produces on THIS roster; the TRAIN Fold
# A numbers 1.2485 / 0.9943 are context only and are NOT this cell's bar (a different roster, a
# different gold split, a different scorer sibling, a different clustering). The arm's contrast is
# not read until the own-null margin table has sealed, and the margins are never adjusted
# afterwards. See the preregistration, section 4a.
#
# DRIVER: scripts/analysis/slurp_paired_roster_read.py -- the reusable stage driver cell B6 proved
# on this exact roster, with this scorer (slurp-slu-official, devel gold) and this clustering
# (utterance_id, owner decision 79 D2) as its own defaults. scripts/analysis/plan_cell_read.py, the
# driver every TRAIN Fold A delta cell used, CANNOT read this cell as committed: its SCORER,
# V3_SCORER and SYM_SCORER are module constants bound to the TRAIN gold siblings with no override
# flag, its lock stage compares against a TRAIN-only B5e comparator, and its per-scenario stages
# need a roster-metadata file carrying a per-sample speaker and scenario that DEV-2000-ADDED does
# not publish. Adapting it is a separate engineering change; see the preregistration, section 9b.
#
# The driver always writes status DESCRIPTIVE and computes no verdict. The ADMITTED / NEUTRAL /
# HARMFUL rule of protocol-registered-v1.json is applied BY THE COORDINATOR in the verdict document,
# against the margins step `own-null` produced, showing the arithmetic.
#
# Model-free: zero model / tokenizer / encoder / server contacts; scorer contacts only through the
# sealed per-sample scores. Registered as SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-OWN-NULL-V1
# and SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE{,-TWIN}-PAIRED-ANALYSIS-V1 (model-free-check rows).
WHICH=$1
COMP_RUN=SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1
COMP_ATTEMPT=attempt-slurp-native-default-plan-dev2000-added-generation-v1
case $WHICH in
  own-null)
    RIGHT_RUN=SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1
    RIGHT_ATTEMPT=attempt-slurp-native-default-plan-dev2000-added-replicate-generation-v1
    RIGHT_LABEL="PLANr-DEV2000 (the request-identical replicate)"
    LEFT_LABEL="PLAN-DEV2000 (the sealed comparator)"
    ROOT_ID=SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-OWN-NULL-V1
    RECIPE=slurp-dev2000-added-own-null-v1
    TITLE="DEV-2000-ADDED own null: the locked plan against its request-identical replicate (the margin table CELL-3 is read at)"
    CONSUME=0;;
  arm)
    RIGHT_RUN=SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1
    RIGHT_ATTEMPT=attempt-slurp-native-stage3-delta-cell-r03-gate-v1-generation
    RIGHT_LABEL="cell CELL-3 (the locked plan plus the coverage-gated stage3-deltas-v2 store)"
    LEFT_LABEL="the sealed DEV-2000-ADDED PLAN arm"
    ROOT_ID=SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-PAIRED-ANALYSIS-V1
    RECIPE=slurp-stage3-delta-cell-r03-gate-arm-paired-analysis-v1
    TITLE="Cell CELL-3 (arm; Stage-3 S3-6 iteration 3): the coverage-gated stage3-deltas-v2 store against the sealed DEV-2000-ADDED PLAN arm"
    CONSUME=1;;
  twin)
    RIGHT_RUN=SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-TWIN-V1
    RIGHT_ATTEMPT=attempt-slurp-native-stage3-delta-cell-r03-gate-v1-twin
    RIGHT_LABEL="the CELL-3 derangement twin (form control)"
    LEFT_LABEL="the sealed DEV-2000-ADDED PLAN arm"
    ROOT_ID=SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-TWIN-PAIRED-ANALYSIS-V1
    RECIPE=slurp-stage3-delta-cell-r03-gate-twin-paired-analysis-v1
    TITLE="Cell CELL-3 (derangement twin; Stage-3 S3-6 iteration 3): the same gate, the deranged store, against the sealed DEV-2000-ADDED PLAN arm"
    CONSUME=1;;
  *) echo "usage: cell3_read.sh arm|twin|own-null"; exit 2;;
esac
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
PKG=$MAIN/docs/readiness/2026-09-24-slurp-stage3-delta-cell-r03-gate-v1
ROOT=$SPEECHRL_DATA_DIR/analysis/$ROOT_ID
mkdir -p "$ROOT" \
  && cp "$MAIN/scripts/analysis/slurp_paired_roster_read.py" "$ROOT/slurp_paired_roster_read.py" \
  && cp "$PKG/registered-facts-v1.json" "$ROOT/registered-cell3.json" \
  && cd "$ROOT" || exit 1
sha256sum slurp_paired_roster_read.py | cut -c1-16
$PY slurp_paired_roster_read.py --stage all \
  --left-run $COMP_RUN --left-attempt $COMP_ATTEMPT --left-label "$LEFT_LABEL" \
  --right-run $RIGHT_RUN --right-attempt $RIGHT_ATTEMPT --right-label "$RIGHT_LABEL" \
  --scorer-id slurp-slu-official \
  --roster docs/receipts/rosters/slurp-dev-2000-added-v1.json \
  --cluster-key utterance_id \
  --split-identity-hash ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67 \
  --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
  --seed 20260915 --draws 10000 \
  --recipe-id $RECIPE --title "$TITLE" \
  --analysis-root "$ROOT" > "$ROOT/stage-all.log" 2>&1 \
  || { echo "PAIRED READ FAILED"; tail -5 "$ROOT/stage-all.log" | cut -c1-300; exit 2; }
echo "paired read done $(date -u +%T)"
if [ "$CONSUME" = "1" ]; then
  echo "== per-node delta consumption and the GATE table $(date -u +%T)"
  # --scorer MUST be passed: the module default is the TRAIN gold sibling.
  $PY "$MAIN/scripts/analysis/stage3_delta_consumption_read.py" \
    --run $RIGHT_RUN --attempt $RIGHT_ATTEMPT \
    --comparator-run $COMP_RUN --comparator-attempt $COMP_ATTEMPT \
    --store-id stage3-deltas --scorer slurp-slu-official \
    --recipe-id slurp-stage3-delta-cell-r03-gate-consumption-v1 \
    --analysis-root "$ROOT" > "$ROOT/stage-consumption.log" 2>&1 \
    || { echo "CONSUMPTION READ FAILED"; tail -5 "$ROOT/stage-consumption.log" | cut -c1-300; exit 3; }
  echo "consumption read done $(date -u +%T)"
fi
echo "CELL-3 $WHICH read done $(date -u +%T)"; ls "$ROOT"
