#!/bin/bash
# Owner-213 successor only. Root must qualify BOTH seals and countersign READ first.
set -euo pipefail
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
PKG=docs/readiness/2026-10-01-slurp-milestone-successor1-v1
bash "$MAIN/scripts/flights/read_paired_cell.sh" "$PKG" --passes vs-aa \
  --strata-source scorer --population-counts "$PKG/population-counts-v1.json" \
  --weighting post-stratified "$@"
