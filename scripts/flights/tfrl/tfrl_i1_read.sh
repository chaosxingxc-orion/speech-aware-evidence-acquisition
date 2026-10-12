#!/bin/bash
# The loop driver's close step for one iteration, as a recipe-driven read wrapper (model-free; 0 GPU). DRAFT / HELD.
#
#   TFRL_ITER=1 bash scripts/flights/tfrl/tfrl_i1_read.sh [--dry-run] [--no-row-scores]
#
# --dry-run: prints the loop status and the commands `close` would run (no --execute); writes nothing.
# Otherwise: REFUSES unless the iteration's sealed run manifest exists and the READ row is ROOT COUNTERSIGNED; exports the per-row scores of the
# lock and ace columns (scripts/flights/tfrl/tfrl_row_scores.py, write-once, for the script-computed ACE counters); then runs
#   tfrl_loop_driver.py --execute close --iter N --row-scores F
# which scores the supply columns once each (stage3_rollout_score.py --mode supply-variants), runs the node-local reader and the paired
# reads (aa-vs-lock first, then each column), applies the preregistered selection rule, archives the states, updates the curve and the
# meta summary and chooses the next parent. It refuses while a batch driver, a flight or a flip loop runs, and when the protocol hash moved.
# MODEL-FREE: zero model / tokenizer / encoder / server contacts.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
LOCK=${SAEA_DATASETS_LOCK:-/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
saea_data_root_init || exit 70
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
source "$MAIN/scripts/flights/batch/read_lib.sh"
ITER=${TFRL_ITER:-1}
DRY=0
ROWS=1
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --no-row-scores) ROWS=0 ;;
    *) echo "usage: tfrl_i1_read.sh [--dry-run] [--no-row-scores]"; exit 2 ;;
  esac
  shift
done
SLUG=tfrl-loop-i$ITER-fold-b
RUN=SAEA-SLURP-STAGE3-${SLUG^^}-V1
ATT=attempt-slurp-native-stage3-$SLUG-generation-v1
READ_RUN=SAEA-SLURP-STAGE3-${SLUG^^}-COLUMN-READ-V1
RUNDIR=$SPEECHRL_DATA_DIR/runs/$RUN/$ATT
OUT=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-TFRL-LOOP-V1/i$ITER
cd "$MAIN" || exit 1
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
DRIVER="$PY -B scripts/flights/tfrl/tfrl_loop_driver.py --lock $LOCK"
if [ "$DRY" = 1 ]; then
  $DRIVER status
  $DRIVER close --iter "$ITER"
  exit 0
fi
[ -f "$RUNDIR/$RUN.run-manifest.json" ] || { echo "REFUSED: no sealed run manifest under $RUNDIR"; exit 3; }
read_require_countersigned docs/exposure-ledger.md "$READ_RUN" || exit 3
ROWARG=()
if [ "$ROWS" = 1 ]; then
  mkdir -p "$OUT"
  if [ ! -f "$OUT/row-scores.json" ]; then
    "$PY" -B scripts/flights/tfrl/tfrl_row_scores.py --run-id "$RUN" --attempt "$ATT" --out "$OUT/row-scores.json" --lock "$LOCK" \
      || echo "ROW-SCORE EXPORT FAILED (the columns are scored by the first close --execute; re-run this wrapper after it)"
  fi
  [ -f "$OUT/row-scores.json" ] && ROWARG=(--row-scores "$OUT/row-scores.json")
fi
$DRIVER --execute close --iter "$ITER" "${ROWARG[@]}" || { echo "CLOSE FAILED"; exit 5; }
echo "tfrl loop iteration $ITER closed; receipts under docs/readiness/2026-10-11-slurp-tfrl-loop-v1/iterations/i$ITER"
