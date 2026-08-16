#!/usr/bin/env bash
set -uo pipefail
t=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59/SAEA-P2-r0bias.trace.jsonl
python3 - "$t" <<'PY'
import json,sys,collections
kinds=collections.Counter(); stitch=0; keys=collections.Counter()
reqs=[]
for ln in open(sys.argv[1],encoding="utf-8"):
    ln=ln.strip()
    if not ln: continue
    try: d=json.loads(ln)
    except Exception: continue
    k=d.get("record_type") or d.get("type") or d.get("kind") or "?"
    kinds[k]+=1
    for kk in d: keys[kk]+=1
    if d.get("stitch") is True or d.get("payload",{}).get("stitch") is True:
        stitch+=1
    if k=="MODEL_REQUEST": reqs.append(d)
print("record kinds:",dict(kinds))
print("stitch-flagged records:",stitch)
print("top-level keys:",dict(keys))
if reqs:
    print("\nsample MODEL_REQUEST keys:",list(reqs[0].keys()))
    r=reqs[0]
    for k,v in r.items():
        if isinstance(v,(int,float)): print(f"  numeric {k} = {v}")
    md=r.get("metadata") or r.get("meta") or {}
    if isinstance(md,dict):
        print("  metadata keys:",list(md.keys())[:30])
        for k,v in md.items():
            if isinstance(v,(int,float)): print(f"    meta numeric {k} = {v}")
PY
