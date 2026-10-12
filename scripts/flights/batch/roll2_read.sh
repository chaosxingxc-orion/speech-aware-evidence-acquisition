#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The cell ROLL-2 sealed-pool read (the Stage-3 sealed-sample-pool asset on the v2.0 lock roster).
# MODEL-FREE: zero model / tokenizer / encoder / server contacts; scorer contacts only on derived
# COPIES (five: one per sample index). Registered as SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-READ-V1, a
# model-free-check row, BEFORE any number is read.
#
# It is NOT an admission read and never calls scripts/analysis/plan_cell_read.py: ROLL-2 is an
# ASSET, not a comparison. It has no comparator and no gate, so there is nothing to gate against.
# What this read produces is descriptive: the per-sample official SLU-F1 and intent, the
# within-flight sample spread on TRAIN Fold A, and the oracle best-of-5 ceiling stated as an UPPER
# BOUND no selection policy can exceed.
#
# Stages 1-3: scripts/analysis/stage3_rollout_score.py render / score / pairs on copies, exactly as
#             cell ROLL-1's own read runs (sample count auto-detected; asserted here as 5).
# Stage 4:    the spread and ceiling read of
#             docs/readiness/2026-09-26-slurp-stage3-roll-2-fold-a-v1/analysis-recipe-v1.json,
#             registered separately under its own read id before any number is looked at.
#
# No utterance text, gold label, transcript or model output is printed or persisted: the summary
# files carry ids, stratum names, sample indices, scores, flags and hashes only.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
RUN=${RUN:-SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1}
ATTEMPT=${ATTEMPT:-attempt-slurp-native-stage3-roll-2-fold-a-v1-generation}
ROSTER=${ROSTER:-docs/receipts/rosters/slurp-evo-fold-a-v2.json}
SCORER=${SCORER:-slurp-slu-official-projected-v3-train}
ROOT=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-READ-V1
READ_ID=SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-READ-V1
# Registration guard (agree_read.sh's shape): stage 2 reads TRAIN gold, so nothing runs before the READ row
# is a countersigned, non-DRAFT contract-table row. The full four-stage read (render before the guard, then
# score / pairs / spread) is scripts/flights/roll2/roll2_pool_read.sh -- prefer it.
row=$(grep -E "^\| [^|]* \| $READ_ID \|" "$MAIN/docs/exposure-ledger.md" | head -1)
{ [ -n "$row" ] && ! echo "$row" | grep -q "DRAFT" && echo "$row" | grep -q "root countersigned"; }   || { echo "REFUSED: the $READ_ID row is missing, DRAFT or not root countersigned"; exit 3; }
$PY -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)"   || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
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
echo "ROLL-2 render/score/pairs done $(date -u +%T)"; ls "$ROOT"
echo
echo "STAGE 4 (spread + ceiling) is NOT run by this script: it is the descriptive read proper and"
echo "must be registered as SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-READ-V1 in docs/exposure-ledger.md"
echo "before any of its numbers are looked at (analysis-recipe-v1.json stage 4_spread)."
