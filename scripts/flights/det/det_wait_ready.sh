#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Wait for the DET serving session to be resident and healthy, and PROVE its geometry from the live
# server before anything flies: /props must report total_slots 1 and a per-slot n_ctx of 24576, and the
# recorded session.json argv must carry --no-cache-prompt and neither --cache-prompt nor
# --slot-prompt-similarity. A sibling of scripts/flights/batch/slurp_wait_ready.sh.
S=$SAEA_DATA_ROOT/serving/serving-slurp-native-det-np1-nocache-v1
for i in $(seq 1 90); do
  if [ -f "$S/session.json" ] && [ ! -f "$S/session-stop.json" ] && curl -s -m 3 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"ok"'; then
    echo "DET SESSION READY"
    curl -s -m 3 http://127.0.0.1:8080/props | python3 -c "import json,sys; p=json.load(sys.stdin); g=p.get('default_generation_settings') or {}; print('total_slots', p.get('total_slots'), 'slot n_ctx', g.get('n_ctx'))"
    python3 - "$S/session.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
argv = d["identity"]["server_argv"]
flags = {"-np": argv[argv.index("-np") + 1], "-c": argv[argv.index("-c") + 1],
         "--no-cache-prompt": "--no-cache-prompt" in argv, "--cache-prompt": "--cache-prompt" in argv,
         "--slot-prompt-similarity": "--slot-prompt-similarity" in argv, "--no-mmproj": "--no-mmproj" in argv}
ok = flags == {"-np": "1", "-c": "24576", "--no-cache-prompt": True, "--cache-prompt": False,
               "--slot-prompt-similarity": False, "--no-mmproj": True}
print("session argv geometry", json.dumps(flags), "OK" if ok else "WRONG GEOMETRY")
sys.exit(0 if ok else 4)
PY
    rc=$?
    nvidia-smi --query-gpu=memory.used --format=csv,noheader
    exit $rc
  fi
  if [ -f "$S/session-stop.json" ] && [ -f "$S/session.json" ] && [ "$(stat -c %Y $S/session-stop.json)" -gt "$(stat -c %Y $S/session.json)" ]; then echo "SESSION STOPPED EARLY"; tail -c 600 $S/session-stop.json; tail -5 $(ls -t /home/chao/serving-task-det-*.log | head -1); exit 3; fi
  sleep 5
done
echo TIMEOUT; tail -8 $(ls -t /home/chao/serving-task-det-*.log | head -1) | cut -c1-200; exit 2
