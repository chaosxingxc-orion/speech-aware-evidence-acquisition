#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Runbook: build the Stage-3 GEPA arm's prepared inputs and its two construction-role rosters.
# Design note docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md.
#
# MODEL-FREE. Zero frozen-core, tool, embedding, encoder, tokenizer, scorer, GPU and network
# contacts: every byte read is an already-sealed or committed local file. It does NOT flip
# readiness, mint a decision receipt or touch docs/exposure-ledger.md.
#
# Steps:
#   A  preconditions: the sealed ROLL-1 score root (pairs.json + per_row.json), the released v1r
#      authored-deltas document, the committed R01C roster receipt and the construction gold
#      intents map
#   B  groups:  scripts/build_slurp_stage3_gepa_groups.py -> prepared/SAEA-SLURP-STAGE3-DELTAS-
#      GEPA-V1/gepa-groups-v1.json (ids, counts and digests only)
#   C  rosters: the 68-carrier construction-role receipt and the four-row smoke receipt, both pure
#      SELECTIONS of R01C
#   D  verify:  the committed fragments agree with the freshly built artifacts (fail-closed)
#   E  dry run: ONE contact rendered offline through the real material and the transport's own
#      text-only construction gate
#
# GEPA_DRY=1 (the default) runs A and D read-only and prints every mutating command line;
# GEPA_DRY=0 runs them. Commit the rosters and any refreshed fragments afterwards, then re-pin.
set -u
REPO=${REPO:-/home/chao/saea-worktrees/fable-gepa}
DATA=$SAEA_DATA_ROOT
LOCK=${LOCK:-/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json}
PY=${PY:-/home/chao/.venvs/speechrl/bin/python}
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
DRY=${GEPA_DRY:-1}

SCORE_RUN=${SCORE_RUN:-SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1}
SCORE=$DATA/analysis/$SCORE_RUN
PREPARED=$DATA/prepared/SAEA-SLURP-STAGE3-DELTAS-GEPA-V1
GROUPS=$PREPARED/gepa-groups-v1.json
DELTAS=${GEPA_DELTAS:-$DATA/prepared/SAEA-SLURP-STAGE3-DELTAS-V1/authored-stage3-deltas-v1r.json}
GOLD=${GEPA_GOLD_INTENTS:-$DATA/coordination/slurp-stage3-advantage-r01-v1/r01c-gold-intents.json}
ROSTER=docs/receipts/rosters/slurp-stage3-construction-r01c.json
K=${GEPA_K:-6}
RANK=${GEPA_RANK_METRIC:-group-mean}
CAP=${GEPA_CURRENT_DELTA_CAP:-12}

cd "$REPO" || { echo "no checkout at $REPO"; exit 1; }
echo "== gepa_prepare $(date -u +%FT%TZ) REPO=$REPO HEAD=$(git rev-parse --short HEAD) dry=$DRY"

run() { if [ "$DRY" = "1" ]; then echo "   (dry) would run: $*"; else "$@" || { echo "FAILED: $*"; exit 3; }; fi; }

# ------------------------------------------------------------------ A: preconditions
MISSING=0
for F in "$SCORE/pairs.json" "$SCORE/per_row.json" "$DELTAS" "$GOLD" "$REPO/$ROSTER"; do
  [ -f "$F" ] || { echo "A  MISSING $F"; MISSING=1; }
done
if [ "$MISSING" = "1" ]; then
  echo "A  pairs.json / per_row.json are S3-3's own outputs; the authored v1r document and the"
  echo "   gold-intents map are the ADV-1 line's preparations. Nothing here creates them."
  [ "$DRY" = "1" ] || exit 2
fi

# ------------------------------------------------------------------ B: the groups artifact
echo "B  groups k=$K rank=$RANK current-delta-cap=$CAP"
run "$PY" -B scripts/build_slurp_stage3_gepa_groups.py \
    --pairs "$SCORE/pairs.json" --per-row "$SCORE/per_row.json" \
    --deltas "$DELTAS" --roster "$ROSTER" --gold-intents "$GOLD" \
    --repo-root "$REPO" --data-root "$DATA" \
    --k "$K" --rank-metric "$RANK" --current-delta-cap "$CAP" \
    --out "$GROUPS"

# ------------------------------------------------------------------ C: the two rosters
echo "C  construction-role rosters (pure selections of R01C)"
run "$PY" -B scripts/flights/batch/gepa_prepare_steps.py \
    --repo-root "$REPO" --groups "$GROUPS" --write roster
run "$PY" -B scripts/flights/batch/gepa_prepare_steps.py \
    --repo-root "$REPO" --groups "$GROUPS" --write smoke-roster

# ------------------------------------------------------------------ D: fragments agree
echo "D  verify the committed fragments against the artifacts"
"$PY" -B scripts/flights/batch/gepa_prepare_steps.py \
    --repo-root "$REPO" --groups "$GROUPS" verify || {
  echo "D  the committed fragments DISAGREE with the built artifacts; re-register before flying"
  exit 4
}

# ------------------------------------------------------------------ E: the offline dry run
echo "E  one-contact offline dry run"
run "$PY" -B scripts/flights/batch/gepa_dry_run.py \
    --repo-root "$REPO" --data-root "$DATA" --lock-path "$LOCK" \
    --out "$DATA/coordination/slurp-stage3-delta-cell-gepa-r01-v1/gepa-dry-run-v1.json"

echo "== gepa_prepare done $(date -u +%FT%TZ) dry=$DRY"
