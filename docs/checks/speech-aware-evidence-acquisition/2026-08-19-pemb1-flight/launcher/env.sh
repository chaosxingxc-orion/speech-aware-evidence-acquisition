#!/usr/bin/env bash
# Shared environment for every P-EMB flight shell. Sourced, never executed.
#
# SAEA_FEAT_CACHE_DIR is deliberately NOT set here: the two runs consume two
# DIFFERENT datasets and docs/featcache-directories.md's own rule is one
# `<dataset>-<encoder>` directory per dataset campaign, so each run's own
# wrapper exports its own (slurp-q4km for Run A, audio2tool-q4km for Run B).
# That rule is also why the two runs get two SEQUENTIAL embedding-server
# sessions rather than one shared one: `server_env` is fixed at spawn time,
# so one session could only ever point at one dataset's cache directory.
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1          # bytecode under the frozen scoring package closes the D3 gate
export REPO=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONPATH="$REPO/src"             # armor against a hijacked editable install
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LLAMA_RUNTIME_ROOT=/home/chao
export SCRATCH=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri2/pemb

# E-0 binding decision (preregistration opening paragraph): the mtmd media
# placeholder token is PINNED VIA ENV here and independently RE-VERIFIED against
# the live server's own GET /props before any contact
# (rails.embedding_client.EmbeddingClient.verify_media_marker, fail-closed on a
# missing field or a mismatched value -- it never trusts this env value alone).
# The literal is the pinned build's own mtmd default: `strings libmtmd.so` in
# /home/chao/llama.cpp-featcache/build/bin carries exactly `<__media__>`, and
# the `media_marker` /props field name is present in libllama-server-impl.so
# (session log tri2/marker-probe.log).
export LLAMA_MEDIA_MARKER='<__media__>'

# shellcheck disable=SC1091
source ~/.venvs/speechrl/bin/activate
