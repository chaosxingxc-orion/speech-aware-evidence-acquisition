#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Cell W-SV-1's same-flight column read (owner decision 172; recipe
# docs/readiness/2026-09-28-slurp-stage3-wsv1-fold-a-v1/analysis-recipe-v1.json).
#
#   bash scripts/flights/wsv1/wsv1_read.sh [--rescore]
#
# 0. REFUSES before anything is opened unless the READ row SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1 is ROOT
#    COUNTERSIGNED (the same gate scripts/analysis/stage3_paired_read.py --package uses) and the sealed run
#    manifest exists.
# 1. Renders the three first-visit columns (a-base, b-exk30, t-twin) through the delivered row's normaliser and
#    projection (AT1 self-check) and scores each ONCE with slurp-slu-official-train
#    (scripts/analysis/stage3_rollout_score.py --mode supply-variants) into the sealed run's supply-variants/
#    directory, where scripts/analysis/slurp_paired_roster_read.py reads a column from. IDEMPOTENT: skipped when
#    supply-variants/score-summary.json already carries the expected schema; --rescore forces it anyway (a retry
#    after a later stage fails must not re-run the official scorer over columns it already scored).
# 2. Two paired reads (row bootstrap, cluster key sample_id, 10,000 draws, seed 20260928, per-scenario tables):
#      twin-null -- left a-base, right t-twin   (the bar: |offset| + CI95 half-width per metric)
#      knob      -- left a-base, right b-exk30  (read at that bar)
#    through scripts/analysis/stage3_paired_read.py --left-column/--right-column, each under
#    $SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1/<pass>/; a pass directory that
#    already holds files is refused (a sealed read is never overwritten).
# MODEL-FREE: zero model / tokenizer / encoder / server contacts; three official column scorings. The driver
# writes DESCRIPTIVE numbers; the nomination verdict is the coordinator's under the preregistered rule.
RESCORE=0
for arg in "$@"; do
  case "$arg" in
    --rescore) RESCORE=1 ;;
    *) echo "usage: wsv1_read.sh [--rescore]"; exit 2 ;;
  esac
done
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
source "$MAIN/scripts/flights/batch/read_lib.sh"
RUN=SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1
ATT=attempt-slurp-native-stage3-wsv1-fold-a-generation-v1
READ_RUN=SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1
ROSTER=docs/receipts/rosters/slurp-evo-fold-a-v2.json
SPLIT=61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6
SCORER=slurp-slu-official-train
RUNDIR=$SPEECHRL_DATA_DIR/runs/$RUN/$ATT
OUT=$SPEECHRL_DATA_DIR/analysis/$READ_RUN
cd "$MAIN" || exit 1
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
read_require_countersigned docs/exposure-ledger.md "$READ_RUN" || exit 3
[ -f "$RUNDIR/$RUN.run-manifest.json" ] || { echo "REFUSED: no sealed run manifest under $RUNDIR"; exit 3; }
SCORE_RECEIPT="$RUNDIR/supply-variants/score-summary.json"
SCORE_SCHEMA=saea-stage3-supply-variant-first-visit-v1
if [ "$RESCORE" = 1 ] || ! read_scoring_done "$SCORE_RECEIPT" "$SCORE_SCHEMA"; then
  "$PY" -B scripts/analysis/stage3_rollout_score.py --mode supply-variants --run "$RUN" --attempt "$ATT" \
    --roster "$ROSTER" --analysis-root "$RUNDIR/supply-variants" --scorer-id "$SCORER" \
    --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" --stage all || { echo "COLUMN RENDER/SCORE FAILED"; exit 4; }
else
  echo "column scoring already done under $RUNDIR/supply-variants (schema $SCORE_SCHEMA); skipping (--rescore forces)"
fi
read_pass() {  # $1 pass name, $2 right column
  local dir="$OUT/$1"
  if [ -d "$dir" ] && [ -n "$(ls -A "$dir")" ]; then echo "REFUSED: $dir already holds files"; return 5; fi
  mkdir -p "$dir"
  "$PY" -B scripts/analysis/stage3_paired_read.py --per-scenario --stage all \
    --left-run "$RUN" --left-attempt "$ATT" --left-column a-base --left-label "the delivering column a-base" \
    --right-run "$RUN" --right-attempt "$ATT" --right-column "$2" --right-label "the column $2" \
    --scorer-id "$SCORER" --expected-split-role discovery --roster "$ROSTER" --cluster-key sample_id \
    --split-identity-hash "$SPLIT" --seed 20260928 --draws 10000 \
    --recipe-id slurp-stage3-wsv1-fold-a-column-analysis-v1 \
    --title "Cell W-SV-1 column read ($1: $2 vs a-base)" --analysis-root "$dir" \
    --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR"
}
read_pass twin-null t-twin || { echo "TWIN-NULL READ REFUSED OR FAILED"; exit 6; }
read_pass knob b-exk30 || { echo "KNOB READ REFUSED OR FAILED"; exit 6; }
echo "W-SV-1 column reads written under $OUT (twin-null, knob)"
