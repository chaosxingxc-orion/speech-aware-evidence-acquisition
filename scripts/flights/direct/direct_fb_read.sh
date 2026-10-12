#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Read the 266-E bare-core read (model-free): refuses unless the READ row is root countersigned, then runs the preregistered reader over the three
# sealed arms (Thinking minus the mean of the two Instruct passes, the twin offset, the per-scenario table, the Thinking answer-length / parse-failure /
# reasoning-leak tables, cost, and the verdict word). The decode-cost smoke stage needs no countersignature (nothing is scored):
#   bash scripts/flights/direct/direct_fb_read.sh smoke
#   bash scripts/flights/direct/direct_fb_read.sh          # the full read
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
source "$MAIN/scripts/flights/batch/read_lib.sh"
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
cd "$MAIN" || exit 1
STAGE=${1:-read}
if [ "$STAGE" = "read" ]; then
  read_require_countersigned docs/exposure-ledger.md SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-VS-INSTRUCT-READ-V1 || exit 3
fi
$PY -B scripts/analysis/slurp_direct_fold_b_core_read.py --stage "$STAGE" --data-root "$SPEECHRL_DATA_DIR" --repo-root "$MAIN" || exit 2
echo "266-E $STAGE done $(date -u +%T)"
