#!/usr/bin/env bash
# Qwen3-ASR CPU sidecar wrapper (owner rulings 339 / 342 A).
#   scripts/flights/direct/asr_sidecar.sh start|stop|status <qwen3-asr-0.6b|qwen3-asr-1.7b> [--port N] [--lock P]
# `start` stays in the foreground (a detached WSL job dies with its shell): run it as a live background wrapper.
# Default port 8190, CPU only (-ngl 0), session record under $SPEECHRL_DATA_DIR/serving/asr-sidecar-<id>/
# (override with --session-root). The llama-server argv puts --port before --host so the core serving entry's
# unscoped reaper (pgrep -f 'llama-server --host') never matches it. Never use the serving_* scripts.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${SPEECHRL_DATA_DIR:?SPEECHRL_DATA_DIR is not set}"
export PYTHONDONTWRITEBYTECODE=1
exec "${SAEA_ASR_PY:-python3}" -B "$HERE/asr_sidecar.py" "$@"
