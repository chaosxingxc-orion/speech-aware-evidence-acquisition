#!/bin/bash
S=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/serving/serving-e21-native-window-flightruntime-np4-max1024-v1
for i in $(seq 1 90); do
  if [ -f "$S/session.json" ] && [ ! -f "$S/session-stop.json" ] && curl -s -m 3 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"ok"'; then echo "E21 SESSION READY"; curl -s -m 3 http://127.0.0.1:8080/slots | python3 -c "import json,sys; s=json.load(sys.stdin); print('slots', len(s))"; nvidia-smi --query-gpu=memory.used --format=csv,noheader; exit 0; fi
  if [ -f "$S/session-stop.json" ] && [ -f "$S/session.json" ] && [ "$(stat -c %Y $S/session-stop.json)" -gt "$(stat -c %Y $S/session.json)" ]; then echo "SESSION STOPPED EARLY"; tail -c 600 $S/session-stop.json; tail -5 $(ls -t /home/chao/serving-e21-task-*.log | head -1); exit 0; fi
  sleep 5
done
echo TIMEOUT; tail -8 $(ls -t /home/chao/serving-e21-task-*.log | head -1) | cut -c1-200; tail -8 $(ls -t /home/chao/serving-e21-np4-*.log 2>/dev/null | head -1) | cut -c1-200
