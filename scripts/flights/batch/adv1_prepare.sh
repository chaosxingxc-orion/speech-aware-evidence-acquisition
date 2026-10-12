#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Runbook for Stage-3 S3-3 and the ADV-1 registration fills
# (docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md sections S3-3 and S3-4;
# fill map docs/readiness/2026-09-22-slurp-stage3-advantage-r01-v1/fill-after-roll1-seal.json).
#
# ROOT RUNS THIS **AFTER** CELL ROLL-1 (SAEA-SLURP-STAGE3-ROLLOUT-R01-V1) HAS SEALED.
# It makes ZERO model, encoder, tokenizer, GPU and network contacts of its own: S3-3 scores COPIES
# of already-sealed Solver samples through the registered official scorer, and every later step is
# pure Python over ids, counts and digests. It does NOT flip readiness, mint a decision receipt or
# touch docs/exposure-ledger.md.
#
# What it does, in order:
#   A  S3-3 render: one outputs COPY per sample index over the R01C roster
#   B  S3-3 score:  each copy scored ONCE through --scorer-id (scorer contacts only, no model)
#   C  S3-3 pairs:  per_row.json + pairs.json (pairs_schema saea-stage3-rollout-pairs-v2),
#      best/worst per disagreeing row PLUS the S3-4s trajectory block rebuilt from the
#      sealed episode receipt and the sealed <run>.trace.jsonl -- ids, labels, counts and
#      hashes only. Set ADV1_GOLD_INTENTS to a {sample_id: scenario_action} JSON map over
#      the CONSTRUCTION roster to also answer "was the gold intent among the perception
#      candidates" (it enters pairs.json as a boolean and a count, never as a label);
#      without it that question is reported unanswered rather than guessed.
#   D  the disagreeing-row CONSTRUCTION roster receipt (pure selection of R01C, zero contacts):
#      construction-advantage-text is a construction-visible arm, so
#      contracts.gate_exposure._require_construction_role_for_visible_targets refuses the touch
#      unless ADV-1's split identity is a COMMITTED roster_role='construction' receipt's
#   E  print the ADV-1 fill values and write them as a values file; insert the populations block
#   F  apply them to the two ADV-1 fragments with scripts/flights/batch/roll1_fill_placeholders.py
#
# Environment overrides: REPO, SPEECHRL_DATA_DIR, PY, ROLL1_RUN, ROLL1_ATTEMPT, SCORE_RUN,
# ADV1_SCORER.  ADV1_DRY=1 (the default) runs A-E read-only and prints the mutating command lines;
# ADV1_DRY=0 writes the roster receipt, the populations block and the fills.
# Commit the four touched paths afterwards, then re-pin with scripts/flights/repin_cell.py.
set -u
REPO=${REPO:-/home/chao/saea-worktrees/fable-s3adv}
DATA=$SAEA_DATA_ROOT
PY=${PY:-/home/chao/.venvs/speechrl/bin/python}
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
DRY=${ADV1_DRY:-1}

ROLL1_RUN=${ROLL1_RUN:-SAEA-SLURP-STAGE3-ROLLOUT-R01-V1}
ROLL1_ATTEMPT=${ROLL1_ATTEMPT:-attempt-slurp-native-stage3-rollout-r01-generation-v1}
SCORE_RUN=${SCORE_RUN:-SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1}
ADV1_SCORER=${ADV1_SCORER:-slurp-slu-official-projected-v3-train}
# S3-4s: optional, model-free, read only inside the CLI (see the header).
ADV1_GOLD_INTENTS=${ADV1_GOLD_INTENTS:-}

ROSTER=docs/receipts/rosters/slurp-stage3-construction-r01c.json
ROSTER_OUT=docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json
ANALYSIS_RELDIR=analysis/$SCORE_RUN
ANALYSIS_ROOT=$DATA/$ANALYSIS_RELDIR
PAIRS=$ANALYSIS_ROOT/pairs.json
PAIRS_RELPATH=$ANALYSIS_RELDIR/pairs.json
EXPERIMENT=configs/experiment/slurp-native-stage3-advantage-r01-v1.json
BASELINE=configs/baseline/slurp-native-stage3-advantage-baseline-v1.json
HELPERS=scripts/flights/batch/adv1_prepare_steps.py
VALUES=$DATA/coordination/slurp-stage3-advantage-r01-v1/adv1-fill-values.json
SCORE_CLI=scripts/analysis/stage3_rollout_score.py

cd "$REPO" || { echo "no checkout at $REPO"; exit 1; }
echo "== adv1_prepare $(date -u +%FT%TZ) REPO=$REPO HEAD=$(git rev-parse --short HEAD) dry=$DRY"
echo "   rollout $ROLL1_RUN / $ROLL1_ATTEMPT  scorer $ADV1_SCORER  analysis $ANALYSIS_ROOT"

WRITE=""
[ "$DRY" = "0" ] && WRITE="--write"
GOLD=""
[ -n "$ADV1_GOLD_INTENTS" ] && GOLD="--gold-intents $ADV1_GOLD_INTENTS"

# ---------------------------------------------------------------- A/B/C: S3-3 on the seal
for STAGE in render score pairs; do
  CMD="$PY -B $SCORE_CLI --run $ROLL1_RUN --attempt $ROLL1_ATTEMPT --roster $ROSTER --analysis-root $ANALYSIS_ROOT --scorer-id $ADV1_SCORER --repo-root $REPO --data-root $DATA --stage $STAGE $GOLD"
  if [ "$DRY" = "1" ] && [ ! -f "$PAIRS" ]; then
    echo "$STAGE  (dry) would run: $CMD"
    continue
  fi
  echo "$STAGE  $(date -u +%T)"
  $CMD || { echo "S3-3 STAGE $STAGE FAILED"; exit 2; }
done

if [ ! -f "$PAIRS" ]; then
  echo "no $PAIRS yet: rerun with ADV1_DRY=0 once cell ROLL-1 has sealed"
  exit 0
fi

# ---------------------------------------------------------------- D: the disagreeing-row roster
$PY -B "$HELPERS" --repo-root "$REPO" $WRITE roster \
    --pairs "$PAIRS" --pairs-relpath "$PAIRS_RELPATH" --roster-out "$ROSTER_OUT" \
    || { echo "STEP D FAILED"; exit 3; }

# ---------------------------------------------------------------- E: the fill values
$PY -B "$HELPERS" --repo-root "$REPO" $WRITE report \
    --pairs "$PAIRS" --pairs-relpath "$PAIRS_RELPATH" --values-out "$VALUES" \
    --experiment "$EXPERIMENT" \
    || { echo "STEP E FAILED"; exit 4; }

# ---------------------------------------------------------------- F: apply the fills
BY="S3-3 on the sealed cell ROLL-1 ($ROLL1_RUN / $ROLL1_ATTEMPT), scorer $ADV1_SCORER, analysis root $ANALYSIS_RELDIR; disagreeing-row construction roster $ROSTER_OUT written model-free by scripts/flights/batch/adv1_prepare_steps.py"
FILL="$PY -B scripts/flights/batch/roll1_fill_placeholders.py --fragments $EXPERIMENT $BASELINE --values $VALUES --by"
if [ "$DRY" = "1" ]; then
  echo "F  (dry) would run: $FILL \"$BY\" --occurrence-policy at-least-one"
  echo "== adv1_prepare dry done $(date -u +%FT%TZ)"
  exit 0
fi
$FILL "$BY" --occurrence-policy at-least-one --date "$(date -u +%F)" \
    || { echo "STEP F FAILED"; exit 5; }

echo "F  commit: git add $EXPERIMENT $BASELINE $ROSTER_OUT && git commit -F <message file>"
echo "== adv1_prepare done $(date -u +%FT%TZ)"
