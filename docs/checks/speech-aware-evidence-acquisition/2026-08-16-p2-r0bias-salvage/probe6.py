import json
D='/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59'
R='SAEA-P2-r0bias'
tm=json.load(open(f'{D}/{R}.trace-manifest.json',encoding='utf-8'))
print('type',type(tm))
if isinstance(tm,dict):
    for k,v in tm.items():
        print(' ',k, type(v).__name__, (len(v) if isinstance(v,(list,dict)) else str(v)[:120]))
    for k,v in tm.items():
        if isinstance(v,list) and v: print('  sample of',k,':',json.dumps(v[0],ensure_ascii=False)[:400]); break
print()
rd=json.load(open(f'{D}/{R}.replay-derivation.4330115.json',encoding='utf-8'))
print('replay-derivation keys:', list(rd.keys()) if isinstance(rd,dict) else type(rd))
if isinstance(rd,dict):
    for k,v in rd.items():
        print(' ',k, type(v).__name__, (len(v) if isinstance(v,(list,dict)) else str(v)[:200]))
    for k,v in rd.items():
        if isinstance(v,list) and v:
            print('  first',k,':',json.dumps(v[0],ensure_ascii=False)[:900])
