#!/bin/bash
# P0 only (P1 sealed 2026-09-23 00:49 UTC; the driver's smoke-wait loop variable bug ended the two-step queue after P1).
export PRUNE_ONLY=p0
exec bash /mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch/batch_chain_prune.sh
