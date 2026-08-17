#!/usr/bin/env bash
# Shared environment for every P-SLU flight shell. Sourced, never executed.
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1          # bytecode under the frozen scoring package closes the D3 gate
export REPO=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONPATH="$REPO/src"             # armor against a hijacked editable install
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export SAEA_FEAT_CACHE_DIR=/home/chao/feat-cache/slurp-q4km
export LLAMA_RUNTIME_ROOT=/home/chao
export SCRATCH=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pslufly

# shellcheck disable=SC1091
source ~/.venvs/speechrl/bin/activate

mkdir -p "$SAEA_FEAT_CACHE_DIR"
