#!/bin/bash
# Select the registered sole recovery; reuse the independent shared VAR-2 chain.
set -euo pipefail
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
exec bash "$MAIN/scripts/flights/batch/batch_chain_var2.sh" recovery
