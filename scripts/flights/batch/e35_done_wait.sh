#!/bin/bash
for i in $(seq 1 1260); do
  if [ -e /home/chao/batch-STOP ]; then echo STOP; cat /home/chao/batch-STOP; grep -E 'arm-exit|arm-inspect' /home/chao/batch-status.jsonl | tail -2 | cut -c1-700; exit 0; fi
  if grep -q '"event":"driver-done"' /home/chao/batch-status.jsonl 2>/dev/null; then echo DONE; grep -E 'arm-inspect|step-done|driver-done' /home/chao/batch-status.jsonl | cut -c1-600; exit 0; fi
  sleep 10
done
echo TIMEOUT; tail -2 /home/chao/batch-status.jsonl | cut -c1-300
