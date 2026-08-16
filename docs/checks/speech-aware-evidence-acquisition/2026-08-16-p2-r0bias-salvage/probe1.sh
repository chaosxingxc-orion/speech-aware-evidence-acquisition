set -euo pipefail
D=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59
echo "=== trace line count ==="
wc -l "$D/SAEA-P2-r0bias.trace.jsonl"
echo "=== channel histogram ==="
python3 -c "
import json,collections,sys
c=collections.Counter()
bad=0
n=0
last=None
for line in open('$D/SAEA-P2-r0bias.trace.jsonl',encoding='utf-8'):
    line=line.strip()
    if not line: continue
    n+=1
    try:
        r=json.loads(line)
    except Exception as e:
        bad+=1; print('BADLINE',n,e); continue
    c[r.get('channel')]+=1
    last=r
print('total',n,'bad',bad)
for k,v in c.most_common(): print(f'{v:6d}  {k}')
print('=== LAST RECORD keys ==='); print(json.dumps(last, indent=1)[:3000])
"
echo "=== outputs.jsonl ==="
wc -l "$D/SAEA-P2-r0bias.outputs.jsonl"
head -c 2500 "$D/SAEA-P2-r0bias.outputs.jsonl"
