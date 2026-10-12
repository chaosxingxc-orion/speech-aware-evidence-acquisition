#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# E5-0 (owner decision 201): the pinned Whisper large-v3 transcript pass over SLURP TRAIN Fold A then Fold B, an
# INSTRUMENT (it bounds what a perfect ASR tool call could yield; it is never a delivery step). One speech-tool
# contact per utterance through the existing shared producer (core.preparation_speech_observations), zero core
# contacts. Registration: docs/readiness/2026-09-29-slurp-asr-tool-pass-v1/README.md.
#
#   e5_tool_pass.sh <fold-a|fold-b|both> [--cpu] [--check]
#
#   --check  evaluate every refusal of every selected roster and exit (no contact, no write);
#   --cpu    the CPU fallback (fp32, batch 1, 1 worker x 4 threads, CUDA hidden); allowed while serving is up.
#
# It runs scripts/analysis/e5_asr_tool_pass.py FROM THIS CHECKOUT, which must be clean and carry the countersigned
# exposure-ledger rows SAEA-SLURP-ASR-TOOL-PASS-V1 (+ -FOLD-B-V1). Every refusal lives in that driver: row absent /
# not countersigned / consumed, a generation flight alive, a llama-server on port 8080 in GPU mode, the umbrella lock
# without whisper-large-v3-openai-pt, a dirty checkout, a drifted registration, a prior unsealed attempt. A sealed
# roster is the idempotent warm path (no contact). The first failing roster stops the pass (one-shot semantics: no
# automatic retry; a recovery needs its own registration).
#
# Exit: 0 every selected roster sealed (or admissible under --check); 3 refused; 1 failed; 64 usage.
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=${SAEA_E5_REPO:-$(cd "$HERE/../../.." && pwd)}
PY=${SAEA_E5_PY:-/home/chao/.venvs/saea-whisper-gpu/bin/python}
DATA=$SAEA_DATA_ROOT
LOCK=${SAEA_E5_LOCK:-/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json}

WHICH=${1:-}
shift || true
CPU=
MODE=run
while [ $# -gt 0 ]; do
  case "$1" in
    --cpu) CPU=--cpu ;;
    --check) MODE=check ;;
    *) echo "e5_tool_pass: unknown option $1"; exit 64 ;;
  esac
  shift
done
case "$WHICH" in
  fold-a|fold-b) ROSTERS=$WHICH ;;
  both) ROSTERS="fold-a fold-b" ;;
  *) echo "usage: e5_tool_pass.sh <fold-a|fold-b|both> [--cpu] [--check]"; exit 64 ;;
esac

export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
unset GIT_DIR GIT_WORK_TREE
[ -n "$CPU" ] && export CUDA_VISIBLE_DEVICES=

for roster in $ROSTERS; do
  echo "$(date -u +%FT%TZ) e5_tool_pass: $MODE $roster ${CPU:-gpu}"
  rc=0
  "$PY" -B "$REPO/scripts/analysis/e5_asr_tool_pass.py" "$MODE" --roster "$roster" --data-root "$DATA" \
    --lock "$LOCK" $CPU || rc=$?
  echo "$(date -u +%FT%TZ) e5_tool_pass: $MODE $roster exit $rc"
  [ "$rc" = 0 ] || exit "$rc"
done
exit 0
