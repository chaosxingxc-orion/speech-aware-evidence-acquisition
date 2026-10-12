#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=$SAEA_DATA_ROOT
LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PY=/home/chao/.venvs/speechrl/bin/python
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN:$MAIN/src SPEECHRL_DATA_DIR=$DATA
cd $MAIN || exit 1
$PY -B $SP/e35_rehash.py
$PY -B $SP/e35_rehash.py | tail -1
for c in results_ledger_check finite_completion_policy_check harness_admission_check engineering_base_check; do $PY -B scripts/checks/$c.py >/tmp/g_$c.log 2>&1; r=$?; echo "$c exit $r"; [ $r -ne 0 ] && tail -3 /tmp/g_$c.log | cut -c1-240; done
for pair in "e21-native-window-four-row-direct-vs-system-v1 e21-native-window-direct-four-row-v1" "e21-native-window-four-row-direct-vs-system-v1 e21-native-window-system-four-row-v1" "e21-native-window-sub10-direct-vs-system-v1 e21-native-window-direct-sub10-v1" "e21-native-window-sub10-direct-vs-system-v1 e21-native-window-system-sub10-v1"; do
  set -- $pair
  CK=$DATA/coordination/e21-native-window-flightruntime-e35-v1/check-$2.json
  $PY -B -m speech_aware_evidence_acquisition.core.flight.cli check --repo-root "$MAIN" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" --experiment "$1" --cell "$2" > "$CK" 2>/tmp/ck_$2.err && echo "check $2: OK $($PY -c "import json;d=json.load(open('$CK'));print({k:d.get(k) for k in ('readiness','composed','status') if k in d})" | cut -c1-200)" || { echo "check $2: FAILED"; tail -4 /tmp/ck_$2.err | cut -c1-300; }
done
