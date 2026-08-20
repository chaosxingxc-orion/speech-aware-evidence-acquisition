#!/usr/bin/env bash
# Shared environment for every P-EMB-3M flight shell. Sourced, never executed.
#
# SAEA_FEAT_CACHE_DIR: M1 re-embeds the SAME 60 SLURP devel clips, but through a
# DIFFERENT audio encoder (LCO-3B's own qwen2.5o projector), so it must never
# write into the q4km-warmed slurp-q4km cache. Its own dataset-scoped directory
# per docs/featcache-directories.md's <dataset>-<encoder> rule: slurp-lco3b.
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1          # bytecode under the frozen scoring package closes the D3 gate
export REPO=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONPATH="$REPO/src"             # armor against a hijacked editable install
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LLAMA_RUNTIME_ROOT=/home/chao
export SCRATCH=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pemb3m
export SAEA_FEAT_CACHE_DIR=/home/chao/feat-cache/slurp-lco3b

# E-1 Mission B binding decision: the mtmd media placeholder token is PINNED VIA
# ENV here and independently RE-VERIFIED against the live server's own GET /props
# before any contact (rails.embedding_client.EmbeddingClient.verify_media_marker,
# fail-closed on a missing field or a mismatched value -- it never trusts this env
# value alone). Upstream randomizes the marker per boot unless pinned.
export LLAMA_MEDIA_MARKER='<__media__>'

# Nothing in this flight may fetch an unregistered artifact. The M2/M3 control
# models' own remote code has network fallbacks (GLAP's tokenizer step 3;
# CLSP's RobertaTokenizer/RobertaConfig for "roberta-base"), so the hub is
# forced offline: a genuinely absent asset then fails LOUD instead of silently
# downloading, and a genuinely absent python dependency still raises ImportError
# and is reported as DROPPED-DEPS. Nothing is ever installed.
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# shellcheck disable=SC1091
source ~/.venvs/speechrl/bin/activate
