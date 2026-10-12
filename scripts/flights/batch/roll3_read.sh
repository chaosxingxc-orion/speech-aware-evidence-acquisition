#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The cell ROLL-3 sealed-pool read (the Stage-3 sealed-sample-pool asset on the evaluation roster DEV-2000-ADDED).
# MODEL-FREE: zero model / tokenizer / encoder / server contacts; scorer contacts only on derived
# COPIES (five: one per sample index). Registered as SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1, a
# model-free-check row, BEFORE any number is read.
#
# It is NOT an admission read and never calls scripts/analysis/plan_cell_read.py: ROLL-3 is an
# ASSET, not a comparison. It has no comparator and no gate, so there is nothing to gate against.
# What this read produces is descriptive: the per-sample official SLU-F1 and intent, the
# within-flight sample spread on DEV-2000-ADDED, and the oracle best-of-5 ceiling stated as an UPPER
# BOUND no selection policy can exceed.
#
# Stages 1-3: scripts/analysis/stage3_rollout_score.py render / score / pairs on copies, exactly as
#             cells ROLL-1 and ROLL-2 are read (sample count auto-detected; asserted here as 5). The scorer is the
#             DEVEL-gold sibling slurp-slu-official-projected-v3: this roster is devel, not TRAIN.
# Stage 4:    the spread and ceiling read of
#             docs/readiness/2026-09-26-slurp-stage3-roll-3-dev2000-added-v1/analysis-recipe-v1.json,
#             registered separately under its own read id before any number is looked at.
#
# No utterance text, gold label, transcript or model output is printed or persisted: the summary
# files carry ids, stratum names, sample indices, scores, flags and hashes only.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
RUN=${RUN:-SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1}
ATTEMPT=${ATTEMPT:-attempt-slurp-native-stage3-roll-3-dev2000-added-v1-generation}
ROSTER=${ROSTER:-docs/receipts/rosters/slurp-dev-2000-added-v1.json}
SCORER=${SCORER:-slurp-slu-official-projected-v3}
ROOT=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1
mkdir -p "$ROOT" && cp "$MAIN/scripts/analysis/stage3_rollout_score.py" "$ROOT/stage3_rollout_score.py" || exit 1
cd "$ROOT" || exit 1
echo "driver sha256 $(sha256sum stage3_rollout_score.py | cut -c1-16)"
for stage in render score pairs; do
  echo "== stage $stage $(date -u +%T)"
  $PY -B stage3_rollout_score.py --stage $stage \
    --run "$RUN" --attempt "$ATTEMPT" --roster "$ROSTER" --samples 5 \
    --scorer-id "$SCORER" --repo-root "$MAIN" --analysis-root "$ROOT" \
    > "$ROOT/stage-$stage.log" 2>&1 || { echo "STAGE $stage FAILED"; tail -5 "$ROOT/stage-$stage.log" | cut -c1-300; exit 2; }
done
echo "ROLL-3 render/score/pairs done $(date -u +%T)"; ls "$ROOT"
echo
echo "STAGE 4 (spread + ceiling) is NOT run by this script: it is the descriptive read proper and"
echo "must be registered as SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1 in docs/exposure-ledger.md"
echo "before any of its numbers are looked at (analysis-recipe-v1.json stage 4_spread)."
