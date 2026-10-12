#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The cell ROLL-3 sealed-pool read, all four stages of
# docs/readiness/2026-09-26-slurp-stage3-roll-3-dev2000-added-v1/analysis-recipe-v1.json
# (recipe slurp-stage3-roll-3-dev2000-added-sealed-pool-v1), registered as
# SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1 (a model-free-check row; decision 58: reads run by script).
#
# MODEL-FREE: zero model / tokenizer / encoder / server contacts. Scorer contacts ONLY on derived COPIES
# (five: one per sample index, stage 2, --workers 4 at most: a campaign may be in flight). Stage 4 makes
# no contact at all. Never touches the serving session or port 8080; opens nothing under runs/ for writing.
#
# REGISTRATION GUARD (analysis-recipe-v1.json stage 4_spread; the read is "REGISTERED SEPARATELY ... before
# any number is read"): this script refuses to score or read anything unless the READ row is present in
# docs/exposure-ledger.md as a contract-table row and that row is not marked DRAFT. Stage 1 (render) reads
# no gold and is allowed before registration, so it runs first; the guard sits between stage 1 and stage 2.
#
# Stages 1-3: scripts/analysis/stage3_rollout_score.py render / score / pairs on copies, exactly as cells
#             ROLL-1 and ROLL-AA were read, with the DEVEL-gold sibling scorer slurp-slu-official-projected-v3
#             (this roster is devel, not TRAIN; the -train scorer refuses a devel prediction).
# Stage 4:    scripts/analysis/stage3_pool_spread_read.py -- the within-flight spread (all ten sample-index
#             pairs, CI95 by whole-utterance bootstrap, 10,000 draws, seed 20260915; byte-identical /
#             intent-flip / entity-set-flip shares; the headset / far-field table), the oracle best-of-5
#             ceiling (an UPPER BOUND) beside the sealed delivered score, and the row accounting.
# Both drivers are COPIED beside the output and the copies are what run (det_read.sh's discipline).
#
# No utterance text, gold label, transcript or model output is printed or persisted by the summary files.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
export SAEA_ANALYSIS_WORKERS=${SAEA_ANALYSIS_WORKERS:-4}
RUN=${RUN:-SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1}
ATTEMPT=${ATTEMPT:-attempt-slurp-native-stage3-roll-3-dev2000-added-v1-generation}
READ_ID=${READ_ID:-SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1}
ROSTER=${ROSTER:-docs/receipts/rosters/slurp-dev-2000-added-v1.json}
SCORER=${SCORER:-slurp-slu-official-projected-v3}
SEALED_SCORER=${SEALED_SCORER:-slurp-slu-official}
RECIPE_ID=slurp-stage3-roll-3-dev2000-added-sealed-pool-v1
ROOT=$SPEECHRL_DATA_DIR/analysis/$READ_ID${SAEA_ANALYSIS_SUFFIX:-}
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
  echo "REFUSED before stage 2: $READ_ID is not a contract-table row of docs/exposure-ledger.md (recipe stage 4_spread: registered separately BEFORE any number is read). Render is on disk; nothing else ran."; exit 3
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
  "note": "CONTEXT ONLY -- never a comparator, never a bar (owner decisions 28, 139).",
  "fold_a_offline_pool_floor": {"h_slu_pp": 0.67, "n": 625, "source": "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2c/2d (F1 aggregation read over the sealed ROLL-1 pool)"},
  "fold_a_offline_pool_floor_scaled": {"h_slu_pp": 0.51, "n": 1080, "source": "docs/readiness/2026-09-26-slurp-stage3-roll-2-fold-a-v1-preregistration.md (about 0.51 pp at n = 1,080)"},
  "dev_2000_added_cross_flight_own_null": {"h_slu_pp": 1.2525, "h_intent_pp": 1.1520, "n": 1000, "offset_measured_pp": -0.25, "source": "PLAN vs PLANr on DEV-2000-ADDED (instrument note section 2d, B6 pair)"},
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
echo "ROLL-3 read done $(date -u +%FT%TZ)"; tail -60 "$ROOT/stage-spread.log" | cut -c1-200; ls "$ROOT"
find "$MAIN/src/speech_aware_evidence_acquisition/scoring" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
