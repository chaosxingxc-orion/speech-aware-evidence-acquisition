#!/usr/bin/env bash
# Model-free reproduction entrypoint (R0). This script never touches the model:
# a model-facing run additionally requires a validated ExecutionPlan file and a
# pre-registered exposure ledger row, driven explicitly from Python — never here.
set -euo pipefail

usage() {
  cat <<'EOF'
usage: reproduce.sh [--help]

Runs the model-free verification chain: the E0 closure + runtime receipt gate
dry-run (authorizes nothing). Requires SPEECHRL_DATA_DIR and the pinned
runtime per docs/engineering.md.

Env:
  LLAMA_RUNTIME_ROOT  Directory CONTAINING the pinned llama.cpp checkout
                       (runtime receipt paths, e.g. llama.cpp/build/bin/...,
                       are resolved relative to this directory, not to the
                       checkout itself). Default: $HOME.
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

export PYTHONDONTWRITEBYTECODE=1
python -m speech_aware_evidence_acquisition.e0.generate verify --runtime-root "${LLAMA_RUNTIME_ROOT:-$HOME}"
