#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The sealed-pool read of ONE filler chunk: all four stages of
# docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-cKK-v1/analysis-recipe-v1.json -- cell ROLL-3's
# recipe (scripts/flights/roll3/roll3_pool_read.sh) with TRAIN gold, exactly as cell ROLL-2's read scored
# TRAIN Fold A. Registered as SAEA-SLURP-STAGE3-FILLER-FOLD-B-CKK-READ-V1, a model-free-check row the
# coordinator adds AFTER the seal and BEFORE any number is read (decision 58: reads run by script).
#
#   bash scripts/flights/filler/filler_pool_read.sh <k>
#
# MODEL-FREE: zero model / tokenizer / encoder / server contacts. Scorer contacts ONLY on derived COPIES
# (five: one per sample index, stage 2, --workers 4 at most: a campaign may be in flight). Stage 4 makes
# no contact. Never touches the serving session or port 8080/8081; opens nothing under runs/ for writing.
#
# REGISTRATION GUARD: stage 1 (render) reads no gold and runs first; stages 2-4 refuse unless the READ row
# is a contract-table row of docs/exposure-ledger.md and is not marked DRAFT. When it is missing, this
# script prints the row to register (from the recipe) and stops.
#
# Scorers: the TRAIN-gold sibling slurp-slu-official-projected-v3-train on the copies (the devel scorer
# refuses a TRAIN prediction) and slurp-slu-official-train as the sealed delivered score's scorer.
# No utterance text, gold label, transcript or model output is printed or persisted by the summary files.
K=${1:?usage: filler_pool_read.sh <chunk>}
case "$K" in *[!0-9]*) echo "chunk must be a number" >&2; exit 2;; esac
K2=$(printf %02d "$((10#$K))")
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
export SAEA_ANALYSIS_WORKERS=${SAEA_ANALYSIS_WORKERS:-4}
RD=docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-c$K2-v1
RUN=SAEA-SLURP-STAGE3-FILLER-FOLD-B-C$K2-V1
ATTEMPT=attempt-slurp-native-stage3-filler-fold-b-c$K2-generation-v1
READ_ID=SAEA-SLURP-STAGE3-FILLER-FOLD-B-C$K2-READ-V1
ROSTER=docs/receipts/rosters/slurp-stage3-filler-fold-b-c$K2-v1.json
SCORER=slurp-slu-official-projected-v3-train
SEALED_SCORER=slurp-slu-official-train
RECIPE_ID=slurp-stage3-filler-fold-b-c$K2-sealed-pool-v1
ROOT=$SPEECHRL_DATA_DIR/analysis/$READ_ID${SAEA_ANALYSIS_SUFFIX:-}
[ -f "$MAIN/$RD/analysis-recipe-v1.json" ] || { echo "REFUSED: chunk c$K2 has no registered recipe"; exit 2; }
[ -d "$SPEECHRL_DATA_DIR/runs/$RUN" ] || { echo "REFUSED: $RUN has not flown"; exit 2; }
mkdir -p "$ROOT" || exit 1
$PY -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
for name in stage3_rollout_score.py stage3_pool_spread_read.py; do
  cp "$MAIN/scripts/analysis/$name" "$ROOT/$name" || exit 1   # a RECORD of the driver bytes beside the output
  echo "$name sha256 $(sha256sum "$ROOT/$name" | cut -c1-64)"
done
cd "$ROOT" || exit 1
common=(--run "$RUN" --attempt "$ATTEMPT" --roster "$ROSTER" --samples 5 --scorer-id "$SCORER" --repo-root "$MAIN" --analysis-root "$ROOT")
echo "== stage render $(date -u +%FT%TZ)"
$PY -B stage3_rollout_score.py --stage render "${common[@]}" > "$ROOT/stage-render.log" 2>&1 \
  || { echo "STAGE render FAILED"; tail -5 "$ROOT/stage-render.log" | cut -c1-300; exit 2; }
# ---- registration guard: no gold, no score, no number until the READ row is in the ledger --------------
row=$(grep -E "^\| [^|]* \| $READ_ID \|" "$MAIN/docs/exposure-ledger.md" | head -1)
if [ -z "$row" ]; then
  echo "REFUSED before stage 2: $READ_ID is not a contract-table row of docs/exposure-ledger.md."
  echo "Register it (model-free-check, after the seal, before any number is read), countersign, commit, re-run:"
  echo "| $(date -u +%F) | $READ_ID | model-free-check | The sealed-pool read of filler chunk c$K2 ($RUN): recipe $RECIPE_ID ($RD/analysis-recipe-v1.json), ROLL-3's four stages against TRAIN gold. | no model or tool contact; five scorer runs on derived copies | slurp SLURP-STAGE3-FILLER-FOLD-B-C$K2-V1 TRAIN construction 180 | discovery | <split identity of $ROSTER> | no | 0 | 0 | 0 | No new speech exposure. | $RD/analysis-recipe-v1.json | REGISTERED AFTER THE SEAL AND BEFORE ANY NUMBER IS READ (DRAFT, root countersignature pending). |"
  exit 3
fi
if echo "$row" | grep -q "DRAFT"; then
  echo "REFUSED before stage 2: the $READ_ID row is marked DRAFT (root countersignature pending)."; exit 3
fi
echo "registration guard: $READ_ID row present and not DRAFT"
for stage in score pairs; do
  echo "== stage $stage $(date -u +%FT%TZ)"
  $PY -B stage3_rollout_score.py --stage $stage "${common[@]}" --workers "$SAEA_ANALYSIS_WORKERS" \
    > "$ROOT/stage-$stage.log" 2>&1 || { echo "STAGE $stage FAILED"; tail -5 "$ROOT/stage-$stage.log" | cut -c1-300; exit 2; }
done
echo "== stage spread $(date -u +%FT%TZ)"
cat > "$ROOT/reported-beside-context.json" <<'JSON'
{
  "note": "CONTEXT ONLY -- never a comparator, never a bar (owner decisions 28, 139). A filler chunk is 180 rows: descriptive by size (rule 5) as well as by design.",
  "offline_pool_floor": {"h_slu_pp": 0.67, "n": 625, "source": "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2c/2d"},
  "roll_aa_within_flight": {"h_within_slu_pp": 0.735, "h_within_intent_pp": 0.0, "n": 200, "byte_identical_share": 0.915, "source": "docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md"}
}
JSON
$PY -B stage3_pool_spread_read.py --run "$RUN" --attempt "$ATTEMPT" --roster "$ROSTER" \
  --scorer-id "$SCORER" --sealed-scorer-id "$SEALED_SCORER" --repo-root "$MAIN" --analysis-root "$ROOT" \
  --seed 20260915 --draws 10000 --cluster-key utterance_id --channel-key headset \
  --recipe-id "$RECIPE_ID" --read-run-id "$READ_ID" \
  --expected-seeds 1249110493,1249110494,1249110495,1249110496,1249110497 --expected-temperature 0.7 \
  --context-json "$ROOT/reported-beside-context.json" > "$ROOT/stage-spread.log" 2>&1 \
  || { echo "STAGE spread FAILED"; tail -8 "$ROOT/stage-spread.log" | cut -c1-300; exit 4; }
echo "filler c$K2 read done $(date -u +%FT%TZ)"; tail -60 "$ROOT/stage-spread.log" | cut -c1-200; ls "$ROOT"
find "$MAIN/src/speech_aware_evidence_acquisition/scoring" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
