#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Runbook for preparations 2c and 3 of the Stage-3 construction roster R01
# (docs/readiness/2026-09-22-slurp-stage3-construction-r01-preparations-v1.md, sections 3, 4 and 8).
#
# ROOT RUNS THIS **AFTER** STEP 2B (the 800 encoder forwards of
# SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1) HAS SEALED ITS RECEIPT.
# It makes ZERO model, encoder, tokenizer, GPU and network contacts of its own: step 2c is the
# model-free content -> intent-boundary dimension alias and step 3 is the model-free content
# derivative. Both ride under ledger rows already drafted in docs/exposure-ledger.md.
#
# What it does, in order:
#   A  verify the sealed step-2b receipt, hash queries.jsonl and receipt.json, and MATERIALISE the
#      committed alias TEMPLATE configs/preparation/slurp-stage3-construction-r01-query-alias-v1.json
#      into a runnable copy under the data root. The template carries a `how_to_fill` key and two
#      PENDING_STEP_2B_* placeholders; core.preparation_vectors accepts exactly eight keys and no
#      placeholder, so the template is never passed to it and the committed file is never edited.
#   B  step 2c: python -m ...core.preparation_vectors  (zero contacts)
#   C  read the alias receipt for the segment-vector export's sha256
#   D  preparation 3: scripts/build_slurp_query_content_derivative.py  (zero contacts)
#   E  print every output path with its sha256 and the ROLL-1 placeholder fill values
#
# Environment overrides: REPO, SPEECHRL_DATA_DIR, PY.  PREP23_DRY=1 runs A, C and E only and
# prints the two mutating command lines instead of running them.
set -u
REPO=${REPO:-/home/chao/saea-worktrees/fable-s3q}
DATA=$SAEA_DATA_ROOT
PY=${PY:-/home/chao/.venvs/speechrl/bin/python}
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
DRY=${PREP23_DRY:-0}

EXPORT_ROW=SAEA-SLURP-STAGE3-CONSTRUCTION-R01-QUERY-VECTOR-EXPORT-V1
COORD=$DATA/coordination/slurp-stage3-construction-r01-query-encoding-v1
ALIAS_TEMPLATE=configs/preparation/slurp-stage3-construction-r01-query-alias-v1.json
ALIAS_RUNNABLE=$COORD/query-alias-v1.json
VECTOR_DIR=vectors/slurp-stage3-construction-r01-v1
SEGMENTS_RELPATH=$VECTOR_DIR/query-vectors-speech-segments.jsonl
CONTENT_NAME=query-vectors-speech-content-v1.jsonl
STATE=$COORD/prep23-state.env
HELPERS=scripts/flights/batch/r01_prep23_steps.py

cd "$REPO" || { echo "no checkout at $REPO"; exit 1; }
echo "== r01_prep23 $(date -u +%FT%TZ) REPO=$REPO HEAD=$(git rev-parse --short HEAD) dry=$DRY"

# ---------------------------------------------------------------- A: verify + materialise
$PY -B "$HELPERS" materialise --repo-root "$REPO" --data-root "$DATA" \
    --template "$ALIAS_TEMPLATE" --runnable "$ALIAS_RUNNABLE" --state "$STATE" \
    || { echo "STEP A FAILED"; exit 2; }
# shellcheck disable=SC1090
. "$STATE" || { echo "no state file $STATE"; exit 2; }

# ---------------------------------------------------------------- B: step 2c, the dimension alias
STEP_2C="$PY -B -m speech_aware_evidence_acquisition.core.preparation_vectors --config $ALIAS_RUNNABLE --config-sha256 $ALIAS_CONFIG_SHA256 --repo-root $REPO --data-root $DATA"
if [ "$DRY" = "1" ]; then
  echo "B  (dry) would run: $STEP_2C"
else
  echo "B  step 2c $(date -u +%T)"
  $STEP_2C > "$COORD/step-2c.json" 2> "$COORD/step-2c.err" || {
    echo "STEP 2C FAILED"; tail -5 "$COORD/step-2c.err"; exit 3; }
  echo "B  step 2c sealed -> $COORD/step-2c.json"
fi

# ---------------------------------------------------------------- C: read the alias receipt
$PY -B "$HELPERS" alias-receipt --data-root "$DATA" --state "$STATE" \
    || { echo "STEP C FAILED"; exit 4; }
# shellcheck disable=SC1090
. "$STATE"

# ---------------------------------------------------------------- D: preparation 3
STEP_3="$PY -B scripts/build_slurp_query_content_derivative.py --source-relpath $SEGMENTS_RELPATH --source-sha256 $SEGMENTS_SHA256 --out-dir $VECTOR_DIR --out-name $CONTENT_NAME --ledger-row $EXPORT_ROW"
if [ "$DRY" = "1" ]; then
  echo "D  (dry) would run: $STEP_3"
  echo "E  (dry) rerun without PREP23_DRY=1 for the ROLL-1 fill values"
  exit 0
fi
echo "D  preparation 3 $(date -u +%T)"
$STEP_3 || { echo "PREPARATION 3 FAILED"; exit 5; }

# ---------------------------------------------------------------- E: the ROLL-1 fill values
$PY -B "$HELPERS" report --data-root "$DATA" --state "$STATE" || { echo "STEP E FAILED"; exit 6; }
echo "== r01_prep23 done $(date -u +%FT%TZ)"
