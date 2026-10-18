#!/bin/bash
# Read the carrier base on the Thinking core (model-free). Three stages per carrier:
#   bash scripts/flights/carriers/carrier_think_read.sh smoke   <carrier>   # decode cost of the sealed smoke (no countersignature: nothing is scored); the machine sign-off input
#   bash scripts/flights/carriers/carrier_think_read.sh columns <carrier>   # verify the carrier's two arms are sealed and scored by the standard scorer (prints no number)
#   bash scripts/flights/carriers/carrier_think_read.sh read    <carrier>   # the full read: refuses unless the carrier's READ row is root countersigned, then runs the reader
# <carrier> is a2t, e21 or e22. The flight itself runs the standard scorer once per complete manifest (core.scoring_batch, never sharded); this driver re-scores nothing.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
source "$MAIN/scripts/flights/batch/read_lib.sh"
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
cd "$MAIN" || exit 1
STAGE=${1:-read}
CARRIER=${2:?carrier required: a2t | e21 | e22}
case "$CARRIER" in a2t|e21|e22) ;; *) echo "carrier must be a2t, e21 or e22"; exit 64 ;; esac
READ_ROW=SAEA-CARRIER-THINK-BASE-$(echo "$CARRIER" | tr a-z A-Z)-READ-V1
if [ "$STAGE" = "read" ]; then
  read_require_countersigned docs/exposure-ledger.md "$READ_ROW" || exit 3
fi
$PY -B scripts/analysis/carrier_think_read.py --stage "$STAGE" --carrier "$CARRIER" --data-root "$SPEECHRL_DATA_DIR" --repo-root "$MAIN" || exit 2
echo "CARRIER-THINK $CARRIER $STAGE done $(date -u +%T)"
