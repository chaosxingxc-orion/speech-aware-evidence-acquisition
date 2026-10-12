#!/bin/bash
# GENERIC entry point for a Windows Scheduled Task that runs one registered SPEECH-QUERY ENCODING preparation:
# step 2b (the frozen retrieval-encoder forwards), then the two model-free steps 2c (the content -> intent-boundary
# dimension alias) and 3 (the content-dimension derivative), then the fill values.
#
# The set-parameterised sibling of scripts/flights/batch/prep_r01_encode_task_entry.sh + r01_prep23.sh, written for
# owner decision 107 of 2026-09-23. The two R01 scripts are left exactly as they are: their run is sealed.
#
# Environment:
#   PREP_SET      the key in prep_generic_steps.PREPARATION_SETS, e.g. devel-remainder        (required)
#   PREP_REPO     the clean checkout to run from   (default: the main checkout)
#   PREP_DRY      1 runs only the zero-contact verification steps and prints the two mutating command lines
#
# Never while a GPU flight is in progress (the encoder takes the card): the caller checks the batch driver first and
# this entry refuses if it sees one. It authorises nothing: the encoding row and the export row must already be
# countersigned.
set -u
SET=${PREP_SET:?PREP_SET is required (a key of prep_generic_steps.PREPARATION_SETS)}
REPO=${PREP_REPO:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
saea_data_root_init || exit 70
DATA=$SAEA_DATA_ROOT
DRY=${PREP_DRY:-0}
STEPS=scripts/flights/batch/prep_generic_steps.py
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
source /home/chao/.venvs/speechrl/bin/activate
cd "$REPO" || exit 1
LOG=/home/chao/prep-$SET-encode-$(date -u +%Y%m%dT%H%M%SZ).log
exec > "$LOG" 2>&1
echo "task entry $(date -u +%FT%TZ) set $SET HEAD $(git rev-parse HEAD) dirt $(git status --short | grep -vc '^??')"
[ "$(git status --short | grep -vc '^??')" = "0" ] || { echo "dirty tree; refusing"; exit 2; }
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a GPU flight is running; refusing"; exit 7; fi

# ---------------------------------------------------------------- step 2b: mint the runtime config, then encode
CFG=$(python -B "$STEPS" runtime-config --set "$SET" --repo-root "$REPO" --data-root "$DATA") \
  || { echo "RUNTIME CONFIG REFUSED"; echo "$CFG"; exit 3; }
echo "$CFG"
eval "$(echo "$CFG" | grep -v '^#')"
STEP_2B="python -B -m speech_aware_evidence_acquisition.core.speech_preparation_runtime --config $PREP_RUNTIME_CONFIG --config-sha256 $PREP_RUNTIME_CONFIG_SHA256 --data-root $DATA --source-root $REPO"
if [ "$DRY" = "1" ]; then
  echo "2b (dry) would run: $STEP_2B"
else
  echo "2b step 2b $(date -u +%T)"
  $STEP_2B
  RC=$?
  echo "step 2b exit $RC $(date -u +%FT%TZ)"
  [ $RC -ne 0 ] && exit $RC
fi

# ---------------------------------------------------------------- A: verify the sealed receipt + materialise the alias
if [ "$DRY" = "1" ]; then
  echo "A  (dry) would verify the sealed step-2b receipt and materialise the alias config"
  echo "B  (dry) would run core.preparation_vectors with that config"
  echo "D  (dry) would run scripts/build_slurp_query_content_derivative.py"
  exit 0
fi
MAT=$(python -B "$STEPS" materialise --set "$SET" --repo-root "$REPO" --data-root "$DATA") \
  || { echo "STEP A FAILED"; echo "$MAT"; exit 4; }
echo "$MAT"
eval "$(echo "$MAT" | grep '^PREP_STATE=')"
STATE=${PREP_STATE:?materialise printed no state path}
# shellcheck disable=SC1090
. "$STATE" || { echo "no state file $STATE"; exit 4; }

# ---------------------------------------------------------------- B: step 2c, the dimension alias (zero contacts)
echo "B  step 2c $(date -u +%T)"
python -B -m speech_aware_evidence_acquisition.core.preparation_vectors \
    --config "$ALIAS_CONFIG" --config-sha256 "$ALIAS_CONFIG_SHA256" \
    --repo-root "$REPO" --data-root "$DATA" > "$(dirname "$STATE")/step-2c.json" 2> "$(dirname "$STATE")/step-2c.err" \
  || { echo "STEP 2C FAILED"; tail -5 "$(dirname "$STATE")/step-2c.err"; exit 5; }
echo "B  step 2c sealed -> $(dirname "$STATE")/step-2c.json"

# ---------------------------------------------------------------- C: read the alias receipt
python -B "$STEPS" alias-receipt --set "$SET" --data-root "$DATA" || { echo "STEP C FAILED"; exit 6; }
# shellcheck disable=SC1090
. "$STATE"

# ---------------------------------------------------------------- D: preparation 3 (zero contacts)
echo "D  preparation 3 $(date -u +%T)"
python -B scripts/build_slurp_query_content_derivative.py \
    --source-relpath "$SEGMENTS_RELPATH" --source-sha256 "$SEGMENTS_SHA256" \
    --out-dir "$VECTOR_DIR" --out-name "$CONTENT_NAME" --ledger-row "$EXPORT_ROW" \
  || { echo "PREPARATION 3 FAILED"; exit 8; }

# ---------------------------------------------------------------- E: the fill values
python -B "$STEPS" report --set "$SET" --data-root "$DATA" || { echo "STEP E FAILED"; exit 9; }
echo "== prep_generic_encode done $(date -u +%FT%TZ)"
