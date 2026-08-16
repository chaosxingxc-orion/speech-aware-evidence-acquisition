import json, collections, re
D='/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59'
R='SAEA-P2-r0bias'
recs=[json.loads(l) for l in open(f'{D}/{R}.trace.jsonl',encoding='utf-8')if l.strip()]
bych=collections.defaultdict(list)
for r in recs: bych[r['channel']].append(r)
rep_ids={r['record_id'].rsplit('/',1)[0] for r in bych['REPLAY']}
req_ids={r['record_id'].rsplit('/',1)[0] for r in bych['MODEL_REQUEST'] if 'replay' in r['record_id']}
print('REPLAY without model call:', sorted(rep_ids-req_ids))
print('model call without REPLAY rec:', sorted(req_ids-rep_ids))
for r in bych['REPLAY']:
    if r['record_id'].rsplit('/',1)[0] in (rep_ids-req_ids):
        print(json.dumps(r,indent=1,ensure_ascii=False)[:1200])
print()
print('=== REPLAY summary ===')
by_s=collections.defaultdict(lambda: collections.Counter())
acc=collections.Counter(); rej=collections.Counter()
for r in bych['REPLAY']:
    p=r['payload']; s=p['replay_sample_id']
    by_s[s]['n']+=1
    by_s[s]['accepted']+= 1 if p['replay_accepted'] else 0
    (acc if p['replay_accepted'] else rej)[p['replay_reject_reason']]+=1
for s in sorted(by_s): print(s, dict(by_s[s]))
print('accepted reasons', dict(acc)); print('reject reasons', dict(rej))
print()
print('=== ORG/SUPPLY per sample ===')
for ch in ('ORG','SUPPLY'):
    for r in bych[ch]: print(ch, r['record_id'], json.dumps(r['payload'],ensure_ascii=False))
