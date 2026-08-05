#!/usr/bin/env bash
# Model-free scoring entrypoint (R0): scores a recorded outputs JSONL against
# the frozen scoring stack via the shared driver. Never touches the model.
set -euo pipefail

usage() {
  cat <<'EOF'
usage: evaluate.sh <outputs.jsonl> [scorers]

model-free scoring of a recorded run outputs file (frozen saea-scoring-v1).
Default scorers: asr-wer. Requires SPEECHRL_DATA_DIR for reference layers.
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
if [[ $# -lt 1 ]]; then
  usage >&2
  exit 2
fi

export PYTHONDONTWRITEBYTECODE=1
python -m speech_aware_evidence_acquisition.core.driver score \
  --outputs "$1" --scorers "${2:-asr-wer}"
