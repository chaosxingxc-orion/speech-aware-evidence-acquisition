#!/bin/bash
# Read L338 (model-free). Three stages:
#   bash scripts/flights/nx/l338_read.sh smoke     # per-arm Solver decode cost of the sealed smoke (no countersignature: nothing is scored)
#   bash scripts/flights/nx/l338_read.sh columns   # the OFFICIAL per-arm column scoring of the sealed column flight (one complete scoring per arm; prints no number)
#   bash scripts/flights/nx/l338_read.sh           # the full read: refuses unless the READ row is root countersigned, then runs the preregistered reader
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
source "$MAIN/scripts/flights/batch/read_lib.sh"
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
cd "$MAIN" || exit 1
STAGE=${1:-read}
# The arm cell's run and attempt come from the family (the latest recovery's attempt id after a recovery), never from a literal here.
eval "$($PY -B -c "import sys; sys.path.insert(0, 'scripts/flights/nx'); import l338_family as f; print('RUN=%s ATTEMPT=%s' % (f.CELLS['arm']['run'], f.CELLS['arm']['attempt']))")" || exit 66
ANALYSIS=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-L338-LEVER-COLUMN-FOLD-B-READ-V1
if [ "$STAGE" = "columns" ]; then
  # A sampling group (roles.perception.sampling_variants, a level-2 Perception-branch group) is scored in perception-branches mode: each branch's first-visit Solver
  # column (the committed answer for the solver_samples branch, with its sample 0 as the extra stream column l1-support-sample0), rendered through the delivered row's
  # normaliser and scored ONCE, complete, with the registered official scorer (arm-<arm>-slurp-slu-official-train-scores.json under $ANALYSIS/columns). Never sharded.
  mkdir -p "$ANALYSIS/columns"
  $PY -B scripts/analysis/stage3_rollout_score.py --mode perception-branches --stage all --run "$RUN" --attempt "$ATTEMPT" \
    --roster docs/receipts/rosters/slurp-evo-fold-b-v2.json --analysis-root "$ANALYSIS/columns" --scorer-id slurp-slu-official-train \
    --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" || exit 2
  echo "L338 columns done $(date -u +%T)"
  exit 0
fi
if [ "$STAGE" = "read" ]; then
  read_require_countersigned docs/exposure-ledger.md SAEA-SLURP-L338-LEVER-COLUMN-FOLD-B-READ-V1 || exit 3
fi
$PY -B scripts/analysis/slurp_l338_column_read.py --stage "$STAGE" --data-root "$SPEECHRL_DATA_DIR" --repo-root "$MAIN" || exit 2
echo "L338 $STAGE done $(date -u +%T)"
