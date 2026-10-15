#!/bin/bash
# Read NX-T R1 (model-free). Three stages:
#   bash scripts/flights/nx/nxt_r1_read.sh smoke     # per-arm per-node decode cost of the sealed smoke (no countersignature: nothing is scored)
#   bash scripts/flights/nx/nxt_r1_read.sh columns   # the OFFICIAL per-arm column scoring of the sealed column flight (one complete scoring per arm; prints no number)
#   bash scripts/flights/nx/nxt_r1_read.sh           # the full read: refuses unless the READ row is root countersigned, then runs the preregistered reader
#   bash scripts/flights/nx/nxt_r1_read.sh sealonly-columns   # the SAME column scoring over the SEAL-ONLY completion's attempt, roster = the complete rows (package -sealonly-v1)
#   bash scripts/flights/nx/nxt_r1_read.sh sealonly-read      # the full read over the seal-only attempt at n = the complete-row count (refuses unless the READ row is countersigned)
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
source "$MAIN/scripts/flights/batch/read_lib.sh"
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
cd "$MAIN" || exit 1
STAGE=${1:-read}
# The arm cell's run and attempt come from the family (the rec1 attempt id after a recovery), never from a literal here.
eval "$($PY -B -c "import sys; sys.path.insert(0, 'scripts/flights/nx'); import nxt_r1_family as f; print('RUN=%s ATTEMPT=%s' % (f.CELLS['arm']['run'], f.CELLS['arm']['attempt']))")" || exit 66
ANALYSIS=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1
ROSTER=docs/receipts/rosters/slurp-evo-fold-b-v2.json
SEALONLY_FLAG=
case "$STAGE" in
  sealonly-columns|sealonly-read)
    # The seal-only completion of the stopped column (package -sealonly-v1): its attempt, its roster (the complete rows) and its own analysis directory come from the family.
    eval "$($PY -B -c "import sys; sys.path.insert(0, 'scripts/flights/nx'); import nxt_r1_family as f; s = f.sealonly_spec(); print('ATTEMPT=%s ROSTER=%s' % (s['attempt'], s['complete_rows']))")" || exit 66
    ANALYSIS=$ANALYSIS/sealonly
    SEALONLY_FLAG=--sealonly
    STAGE=${STAGE#sealonly-}
    ;;
esac
if [ "$STAGE" = "columns" ]; then
  mkdir -p "$ANALYSIS/columns"
  $PY -B scripts/analysis/stage3_rollout_score.py --mode perception-branches --stage all --run "$RUN" --attempt "$ATTEMPT" \
    --roster "$ROSTER" --analysis-root "$ANALYSIS/columns" --scorer-id slurp-slu-official-train \
    --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" || exit 2
  echo "NXT-R1 columns done $(date -u +%T)"
  exit 0
fi
if [ "$STAGE" = "read" ]; then
  read_require_countersigned docs/exposure-ledger.md SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1 || exit 3
fi
$PY -B scripts/analysis/slurp_nxt_thinking_policy_column_read.py --stage "$STAGE" --data-root "$SPEECHRL_DATA_DIR" --repo-root "$MAIN" $SEALONLY_FLAG || exit 2
echo "NXT-R1 $STAGE done $(date -u +%T)"
