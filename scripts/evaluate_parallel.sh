#!/usr/bin/env bash
# Outer-parallel authoritative scoring or finalization. Each worker handles
# one COMPLETE, verified run manifest through the existing single-process
# official scorer. Pass --finalize to score, seal, and settle each attempt.
# The scheduler never shards a corpus or averages shard-level aggregates.
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1
python -m speech_aware_evidence_acquisition.core.driver score-batch "$@"
