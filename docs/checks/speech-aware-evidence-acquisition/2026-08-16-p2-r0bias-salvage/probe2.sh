set -euo pipefail
D=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59
python3 - <<'PY'
import json
D='/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59'
rows=[json.loads(l) for l in open(D+'/SAEA-P2-r0bias.outputs.jsonl',encoding='utf-8') if l.strip()]
print('n outputs',len(rows))
print('keys',sorted(rows[0].keys()))
for r in rows:
    t=r.get('text') or ''
    print(r['request_id'], r['sample_id'], 'admitted=',r.get('admitted'), 'chars=',len(t), 'words=',len(t.split()), 'tail=',repr(t[-70:]))
PY
