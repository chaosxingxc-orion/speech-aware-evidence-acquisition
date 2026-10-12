#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The construction-source column's offline read: the loop's contrast tables over the sealed lock column (model-free; 0 GPU). DRAFT / HELD.
#
#   bash scripts/flights/tfrl/tfrl_const_read.sh [--dry-run]
#
# --dry-run: prints the command the read would run and writes nothing. Otherwise REFUSES unless the sealed run manifest exists, its per-row
# official scores are on disk (<run>.scores.json, block slurp-slu-official-train) and the READ row is ROOT COUNTERSIGNED; then runs
#   scripts/analysis/tfrl_contrast_tables.py --arm lock --split train --rows 625
# into analysis/SAEA-SLURP-TFRL-LOOP-V1/construction-source/tables (write-once). The loop driver's `open --iter t --execute` re-derives the same
# tables under its own iteration directory from the same sealed bytes (iterations 1-3 all read THIS column). MODEL-FREE: zero model, tokenizer,
# encoder and server contacts; no claim is made.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
LOCK=${SAEA_DATASETS_LOCK:-/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
source "$MAIN/scripts/flights/batch/read_lib.sh"
DRY=0
case "${1:-}" in
  --dry-run) DRY=1 ;;
  "") ;;
  *) echo "usage: tfrl_const_read.sh [--dry-run]"; exit 2 ;;
esac
SLUG=tfrl-construction-lock-r01c
RUN=SAEA-SLURP-STAGE3-${SLUG^^}-V1
ATT=attempt-slurp-native-stage3-$SLUG-generation-v1
READ_RUN=SAEA-SLURP-STAGE3-${SLUG^^}-COLUMN-READ-V1
RUNDIR=$SPEECHRL_DATA_DIR/runs/$RUN/$ATT
OUT=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-TFRL-LOOP-V1/construction-source/tables
cd "$MAIN" || exit 1
CMD=("$PY" -B scripts/analysis/tfrl_contrast_tables.py --run-id "$RUN" --attempt "$ATT" --arm lock --scorer slurp-slu-official-train --split train
     --rows 625 --data-root "$SPEECHRL_DATA_DIR" --lock "$LOCK" --out-dir "$OUT")
if [ "$DRY" = 1 ]; then
  echo "${CMD[@]}"
  exit 0
fi
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
[ -f "$RUNDIR/$RUN.run-manifest.json" ] || { echo "REFUSED: no sealed run manifest under $RUNDIR"; exit 3; }
[ -f "$RUNDIR/$RUN.scores.json" ] || { echo "REFUSED: no official per-row scores ($RUN.scores.json) under $RUNDIR"; exit 4; }
read_require_countersigned docs/exposure-ledger.md "$READ_RUN" || exit 3
[ -e "$OUT/tables-v1.json" ] && { echo "REFUSED: $OUT/tables-v1.json exists (write-once)"; exit 6; }
mkdir -p "$OUT"
"${CMD[@]}" || { echo "TABLES FAILED"; exit 5; }
echo "construction-source tables written under $OUT"
