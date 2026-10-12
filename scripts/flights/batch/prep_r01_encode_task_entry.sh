#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Entry point for the Windows Scheduled Task "SAEA-Prep-R01-Encode": preparation 2 of the Stage-3 construction roster R01
# (800 frozen retrieval-encoder contacts, run SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1, attempt encode-v1),
# then the model-free runbook r01_prep23.sh (alias export + content derivative). Runs from the clean checkout whose HEAD the
# runtime config pins as study_head (fable-s3q at fb6ff7a3); re-mint the config with r01_prep2_runtime_config.py otherwise.
# Never while a GPU flight is in progress (the encoder takes the card): the caller checks the batch driver first.
REPO=${PREP_REPO:-/home/chao/saea-worktrees/fable-s3q}
DATA=$SAEA_DATA_ROOT
CFG=$DATA/coordination/slurp-stage3-construction-r01-query-encoding-v1/runtime-config-v1.json
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
source /home/chao/.venvs/speechrl/bin/activate
cd "$REPO" || exit 1
LOG=/home/chao/prep-r01-encode-$(date -u +%Y%m%dT%H%M%SZ).log
exec > "$LOG" 2>&1
echo "task entry $(date -u +%FT%TZ) HEAD $(git rev-parse HEAD) dirt $(git status --short | grep -vc '^??')"
[ "$(git status --short | grep -vc '^??')" = "0" ] || { echo "dirty tree; refusing"; exit 2; }
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a GPU flight is running; refusing"; exit 7; fi
SHA=$(sha256sum "$CFG" | cut -c1-64); echo "runtime config sha256 $SHA"
python -B -m speech_aware_evidence_acquisition.core.speech_preparation_runtime --config "$CFG" --config-sha256 "$SHA" --data-root "$DATA" --source-root "$PWD"
RC=$?; echo "step 2b exit $RC $(date -u +%FT%TZ)"
[ $RC -ne 0 ] && exit $RC
bash scripts/flights/batch/r01_prep23.sh
echo "runbook exit $? $(date -u +%FT%TZ)"
