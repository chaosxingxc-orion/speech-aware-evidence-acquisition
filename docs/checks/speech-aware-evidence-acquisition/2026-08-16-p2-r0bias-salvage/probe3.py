import json, collections
D='/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59'
recs=[json.loads(l) for l in open(D+'/SAEA-P2-r0bias.trace.jsonl',encoding='utf-8') if l.strip()]
bych=collections.defaultdict(list)
for r in recs: bych[r['channel']].append(r)
for ch in ['OBS','ORG','SUPPLY','USE','REPLAY','MODEL_REQUEST','MODEL_RESPONSE','COST']:
    rs=bych[ch]
    keys=collections.Counter()
    for r in rs:
        p=r['payload']
        keys.update(sorted(p.keys()) if isinstance(p,dict) else ['<not-dict>'])
    print('='*70); print(ch, 'n=',len(rs))
    print(' payload keys:', dict(keys))
    print(' first record_id:', rs[0]['record_id'], '| last:', rs[-1]['record_id'])
    s=json.dumps(rs[0], indent=1, ensure_ascii=False)
    print(' FIRST:', s[:1400])
