#!/usr/bin/env bash
# Outer-parallel authoritative scoring. Each worker scores one COMPLETE,
# verified run manifest through the existing single-process official scorer.
# The scheduler never shards a corpus or averages shard-level aggregates.
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1
python -m speech_aware_evidence_acquisition.core.driver score-batch "$@"
