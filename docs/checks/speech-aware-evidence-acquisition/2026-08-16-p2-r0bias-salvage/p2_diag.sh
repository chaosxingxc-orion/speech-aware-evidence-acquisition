#!/usr/bin/env bash
set -uo pipefail
echo "=== detached logs ==="
ls -la /home/chao/p2-rladder-detached-*.log 2>/dev/null
for f in /home/chao/p2-rladder-detached-*.log; do
  echo "--- $f (tail 40) ---"; tail -40 "$f"
done
echo "=== launcher alive? ==="
pgrep -af run_arm_sequence || echo none
pgrep -af llama-server || echo "no llama-server"
echo "=== r0bias manifest ==="
d=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs
m="$d/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59/SAEA-P2-r0bias.run-manifest.json"
python3 -c "
import json,sys
o=json.load(open('$m'))
for k in ('status','started_at','finished_at','abort_reason','error','notes'):
    if k in o: print(k,'=',json.dumps(o[k])[:500])
print('keys:', list(o.keys()))
" 2>&1 | head -30
echo "=== r1verify attempt dir ==="
ls -la "$d/SAEA-P2-r1verify/attempt-20260816T025734Z-23a43f/" 2>/dev/null | head -20
