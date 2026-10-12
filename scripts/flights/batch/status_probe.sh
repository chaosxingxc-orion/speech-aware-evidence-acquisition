#!/bin/bash
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
saea_data_root_init || exit 70
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
cd $MAIN && bash scripts/serving_session.sh status --session-id serving-e21-native-window-flightruntime-np4-max1024-v1 2>&1 | /home/chao/.venvs/speechrl/bin/python -c "
import json,sys; raw=sys.stdin.read()
try: d=json.loads(raw)
except Exception as e: print('NOT JSON:', raw[:500]); raise SystemExit
m=d.get('last_monitor_sample') or {}; print('keys', list(d.keys())[:14]); print('server_ok', m.get('server_ok'), 'slots', m.get('slots'), 'session', (d.get('session') or {}).get('session_id'), 'sampled', m.get('sampled_at_iso'), 'process', d.get('process_state'))"
