#!/bin/bash
# Read the P3.1 read (model-free): refuses unless the READ row is root countersigned, then runs the preregistered reader.
#   bash scripts/flights/direct/thinking_system_dev_read.sh smoke   # per-node decode cost of the sealed smoke (no countersignature: nothing is scored)
#   bash scripts/flights/direct/thinking_system_dev_read.sh         # the full read, after BOTH arms are sealed
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
source "$MAIN/scripts/flights/batch/read_lib.sh"
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
cd "$MAIN" || exit 1
STAGE=${1:-read}
if [ "$STAGE" = "read" ]; then
  read_require_countersigned docs/exposure-ledger.md SAEA-SLURP-SYSTEM-THINKING-CORE-DEV2000-ADDED-READ-V1 || exit 3
fi
$PY -B scripts/analysis/slurp_system_thinking_core_dev_read.py --stage "$STAGE" --data-root "$SPEECHRL_DATA_DIR" --repo-root "$MAIN" || exit 2
echo "P3.1 $STAGE done $(date -u +%T)"
