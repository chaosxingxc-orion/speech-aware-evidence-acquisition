#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Cell W4-SV's first-visit column read (owner decision 172; recipe
# docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1/analysis-recipe-v1.json):
#
#   bash scripts/flights/w4sv/w4sv_read.sh [--rescore]
#
# 1. REFUSES before any score is opened unless the READ row SAEA-SLURP-STAGE3-W4SV-FOLD-A-COLUMN-READ-V1 is ROOT
#    COUNTERSIGNED in docs/exposure-ledger.md.
# 2. Renders the three first-visit Solver columns (b-w4, t-twin, a-agree) of the sealed arm through the delivered
#    row's normaliser and projection (AT1 self-check) and scores each ONCE with slurp-slu-official-train
#    (scripts/analysis/stage3_rollout_score.py --mode supply-variants), into <run dir>/supply-variants/ -- the
#    directory scripts/analysis/slurp_paired_roster_read.py reads a column from. IDEMPOTENT: skipped when
#    supply-variants/score-summary.json already carries the expected schema; --rescore forces it anyway.
# 3. Pass t-vs-a (the twin null: left a-agree, right t-twin) and pass b-vs-a (GATING: left a-agree, right b-w4) with
#    scripts/analysis/stage3_paired_read.py --left-column/--right-column, paired row bootstrap by sample_id,
#    10,000 draws, seed 20260928, per-scenario tables and the frontier row, under
#    $SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-W4SV-FOLD-A-COLUMN-READ-V1/<pass>/. A pass directory that
#    already holds files is never overwritten.
# MODEL-FREE: zero model / tokenizer / encoder / server contacts; three official column scorings. Descriptive
# numbers only; the verdict word is the coordinator's under the package's rule (decision 139), and a column pair's
# ceiling is 'nominated' (Q6).
RESCORE=0
for arg in "$@"; do
  case "$arg" in
    --rescore) RESCORE=1 ;;
    *) echo "usage: w4sv_read.sh [--rescore]"; exit 2 ;;
  esac
done
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
source "$MAIN/scripts/flights/batch/read_lib.sh"
RUN=SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1
ATT=attempt-slurp-native-stage3-w4sv-fold-a-generation-v1
READ=SAEA-SLURP-STAGE3-W4SV-FOLD-A-COLUMN-READ-V1
ROSTER=docs/receipts/rosters/slurp-evo-fold-a-v2.json
SPLIT=61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6
SCORER=slurp-slu-official-train
RUNDIR=$SPEECHRL_DATA_DIR/runs/$RUN/$ATT
OUT=$SPEECHRL_DATA_DIR/analysis/$READ
cd "$MAIN" || exit 1
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
read_require_countersigned docs/exposure-ledger.md "$READ" || exit 3
[ -f "$RUNDIR/$RUN.run-manifest.json" ] || { echo "REFUSED: no sealed manifest under $RUNDIR"; exit 4; }
SCORE_RECEIPT="$RUNDIR/supply-variants/score-summary.json"
SCORE_SCHEMA=saea-stage3-supply-variant-first-visit-v1
if [ "$RESCORE" = 1 ] || ! read_scoring_done "$SCORE_RECEIPT" "$SCORE_SCHEMA"; then
  "$PY" -B scripts/analysis/stage3_rollout_score.py --mode supply-variants --run "$RUN" --attempt "$ATT" \
    --roster "$ROSTER" --analysis-root "$RUNDIR/supply-variants" --scorer-id "$SCORER" --stage all \
    --data-root "$SPEECHRL_DATA_DIR" || { echo "COLUMN RENDER/SCORE FAILED"; exit 5; }
else
  echo "column scoring already done under $RUNDIR/supply-variants (schema $SCORE_SCHEMA); skipping (--rescore forces)"
fi
for pass in t-vs-a b-vs-a; do
  case $pass in t-vs-a) RIGHT=t-twin; LABEL="the twin t-twin (the null)";; b-vs-a) RIGHT=b-w4; LABEL="arm b-w4 (W4 conventions, gating)";; esac
  if [ -d "$OUT/$pass" ] && [ -n "$(ls -A "$OUT/$pass")" ]; then echo "REFUSED: $OUT/$pass already holds files"; exit 6; fi
  mkdir -p "$OUT/$pass"
  "$PY" -B scripts/analysis/stage3_paired_read.py --per-scenario --frontier \
    --stage all --left-run "$RUN" --left-attempt "$ATT" --left-column a-agree --left-label "the delivering arm a-agree" \
    --right-run "$RUN" --right-attempt "$ATT" --right-column "$RIGHT" --right-label "$LABEL" \
    --scorer-id "$SCORER" --expected-split-role discovery --roster "$ROSTER" --cluster-key sample_id \
    --split-identity-hash "$SPLIT" --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
    --seed 20260928 --draws 10000 --recipe-id slurp-stage3-w4sv-fold-a-column-read-v1 \
    --title "Cell W4-SV first-visit column read ($pass)" --analysis-root "$OUT/$pass" || { echo "READ FAILED ($pass)"; exit 7; }
done
echo "W4-SV column reads written under $OUT (t-vs-a, b-vs-a)"
