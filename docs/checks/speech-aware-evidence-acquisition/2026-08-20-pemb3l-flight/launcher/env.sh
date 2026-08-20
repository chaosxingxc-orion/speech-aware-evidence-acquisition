#!/usr/bin/env bash
# Shared environment for every P-EMB-3L flight shell. Sourced, never executed.
#
# SAEA_FEAT_CACHE_DIR: this sweep re-embeds the SAME 60 SLURP devel clips the
# consumed P-SLU/P-KEY/P-TRAP and P-EMB-1 flights already warmed, so it points
# at the SAME dataset-scoped directory those used (docs/featcache-directories.md's
# <dataset>-<encoder> rule): slurp-q4km. The legacy q4km cache is never touched.
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1          # bytecode under the frozen scoring package closes the D3 gate
export REPO=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONPATH="$REPO/src"             # armor against a hijacked editable install
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LLAMA_RUNTIME_ROOT=/home/chao
export SCRATCH=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pemb3l
export SAEA_FEAT_CACHE_DIR=/home/chao/feat-cache/slurp-q4km

# E-0 binding decision, reused verbatim from the consumed P-EMB-1/2 flights:
# the mtmd media placeholder token is PINNED VIA ENV here and independently
# RE-VERIFIED against the live server's own GET /props before any contact
# (rails.embedding_client.EmbeddingClient.verify_media_marker, fail-closed on a
# missing field or a mismatched value -- it never trusts this env value alone).
export LLAMA_MEDIA_MARKER='<__media__>'

# shellcheck disable=SC1091
source ~/.venvs/speechrl/bin/activate
