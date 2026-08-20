#!/usr/bin/env bash
# Shared environment for every P-EMB-4R flight shell. Sourced, never executed.
#
# NO GLOBAL SAEA_FEAT_CACHE_DIR. This flight serves TWO DIFFERENT audio encoders
# (LCO-3B's own qwen2.5o projector and LCO-7B's), so a single process-wide
# feature-cache directory would be wrong for one of them: cache entries are
# mmproj-encoder-specific (docs/featcache-directories.md). The launcher pins one
# directory PER MODEL (<dataset>-<encoder>: slurp-lco3b / slurp-lco7b) and passes
# it explicitly as LLAMA_MTMD_FEAT_CACHE_DIR in that session's own server_env;
# core.session.start_session force-injects nothing, so nothing else can leak in.
# The launcher REFUSES to start if SAEA_FEAT_CACHE_DIR is set in the environment,
# so an operator-shell accident can never silently repoint a session.
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1          # bytecode under the frozen scoring package closes the D3 gate
export REPO=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONPATH="$REPO/src"             # armor against a hijacked editable install
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LLAMA_RUNTIME_ROOT=/home/chao
export SCRATCH=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pemb4r
unset SAEA_FEAT_CACHE_DIR || true

# E-1 Mission B binding decision: the mtmd media placeholder token is PINNED VIA
# ENV here and independently RE-VERIFIED against the live server's own GET /props
# before any contact (rails.embedding_client.EmbeddingClient.verify_media_marker,
# fail-closed). Upstream randomizes the marker per boot unless pinned.
export LLAMA_MEDIA_MARKER='<__media__>'

# Nothing in this flight may fetch an unregistered artifact. GLAP's own remote
# code has network fallbacks, so the hub is forced offline: a genuinely absent
# asset then fails LOUD instead of silently downloading, and a genuinely absent
# python dependency still raises ImportError and is reported as DROPPED-DEPS.
# Nothing is ever installed.
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# shellcheck disable=SC1091
source ~/.venvs/speechrl/bin/activate
