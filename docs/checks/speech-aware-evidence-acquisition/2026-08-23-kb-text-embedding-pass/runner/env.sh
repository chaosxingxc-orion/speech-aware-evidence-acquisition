#!/usr/bin/env bash
# Shared environment for the SAEA-SN-TOOL-KB-TEXT-EMB-PASS shells. Sourced, never executed.
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1          # bytecode under the frozen scoring package closes the D3 gate
export REPO=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONPATH="$REPO/src"             # armor against a hijacked editable install
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LLAMA_RUNTIME_ROOT=/home/chao
export SCRATCH=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/kbtextemb

# Nothing in this pass may fetch an unregistered artifact.
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# shellcheck disable=SC1091
source ~/.venvs/speechrl/bin/activate
