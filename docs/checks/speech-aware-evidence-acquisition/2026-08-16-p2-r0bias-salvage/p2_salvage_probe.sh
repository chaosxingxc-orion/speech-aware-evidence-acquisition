#!/usr/bin/env bash
set -uo pipefail
R=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
d=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs
tr="$d/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59/SAEA-P2-r0bias.trace.jsonl"
echo "=== trace size/lines ==="
ls -la "$tr"; wc -l "$tr"
echo "=== distinct sample ids in trace ==="
python3 - <<'PY'
import json,collections
p="/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59/SAEA-P2-r0bias.trace.jsonl"
sids=[];kinds=collections.Counter();last=None
for line in open(p,encoding='utf-8'):
    line=line.strip()
    if not line: continue
    try: o=json.loads(line)
    except Exception: continue
    kinds[o.get("event") or o.get("kind") or "?"]+=1
    s=o.get("sample_id") or o.get("sample") or (o.get("meta") or {}).get("sample_id")
    if s and (not sids or sids[-1]!=s): sids.append(s)
    last=o
print("events:",dict(kinds))
print("n distinct sample transitions:",len(sids))
print("first 3:",sids[:3]); print("last 3:",sids[-3:])
print("last record keys:",list(last.keys())[:12] if last else None)
PY
echo "=== manifest failure_reason ==="
python3 -c "
import json;o=json.load(open('$d/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59/SAEA-P2-r0bias.run-manifest.json'))
print('failure_reason:',json.dumps(o.get('failure_reason'))[:600]); print('cost:',json.dumps(o.get('cost'))[:400]); print('created_at:',o.get('created_at'))"
echo "=== who dirtied the tree: mtimes + diff stat ==="
cd "$R" && ls -la --time-style=full-iso AGENTS.md CLAUDE.md && git diff --stat && git diff | head -60
