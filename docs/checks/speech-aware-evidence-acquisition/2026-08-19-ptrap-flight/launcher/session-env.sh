#!/usr/bin/env bash
# Shared environment for the 2026-08-19 three-probe serial flight session.
# Sourced, never executed. SAEA_FEAT_CACHE_DIR is set PER PROBE by the
# probe's own wrapper (slurp-q4km for P-TRAP, audio2tool-q4km for the two
# A2T probes) -- this file deliberately does NOT set it.
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1          # bytecode under the frozen scoring package closes the D3 gate
export REPO=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONPATH="$REPO/src"             # armor against a hijacked editable install
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LLAMA_RUNTIME_ROOT=/home/chao
export TRI=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri

# shellcheck disable=SC1091
source ~/.venvs/speechrl/bin/activate
