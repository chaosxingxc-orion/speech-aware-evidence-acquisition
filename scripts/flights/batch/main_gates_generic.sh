#!/bin/bash
# Usage: main_gates_generic.sh <pytest targets...>  -- the seven offline gates + the named tests on the main checkout (never the derived-media check: it rewrites its receipt on the Windows checkout; never the handoff-freshness check: a documentation stamp must not hold the GPU, it gates landing a result instead).
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
PY=/home/chao/.venvs/speechrl/bin/python
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
saea_data_root_init || exit 70
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN:$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
cd $MAIN || exit 1
rc=0
for c in finite_completion_policy_check results_ledger_check harness_admission_check engineering_base_check tool_catalog_check stage3_algorithm_label_check stage3_effect_floor_check; do $PY -B scripts/checks/$c.py >/tmp/gate_$c.log 2>&1; r=$?; echo "$c exit $r"; [ $r -ne 0 ] && { rc=1; tail -3 /tmp/gate_$c.log | cut -c1-200; }; done
[ $# -gt 0 ] && $PY -B -m pytest -q -p no:cacheprovider "$@" 2>&1 | tail -2
exit $rc
