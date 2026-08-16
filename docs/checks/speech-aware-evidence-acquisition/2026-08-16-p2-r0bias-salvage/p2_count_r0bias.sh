#!/usr/bin/env bash
set -uo pipefail
t=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59/SAEA-P2-r0bias.trace.jsonl
echo "trace: $t"
echo -n "MODEL_RESPONSE lines: "; grep -c '"MODEL_RESPONSE"' "$t"
echo -n "MODEL_REQUEST lines: "; grep -c '"MODEL_REQUEST"' "$t"
python3 - "$t" <<'PY'
import json,sys
tot=0.0; n=0
for ln in open(sys.argv[1],encoding="utf-8"):
    ln=ln.strip()
    if not ln: continue
    try: d=json.loads(ln)
    except Exception: continue
    for k in ("speech_audio_seconds","audio_seconds","metered_audio_seconds"):
        if k in d and isinstance(d[k],(int,float)):
            tot+=d[k]; n+=1; break
print(f"audio-second-bearing records: {n}  sum: {tot:.2f}")
PY
# also look for a totals block in the trace-manifest
m=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59/SAEA-P2-r0bias.trace-manifest.json
python3 - "$m" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
def walk(o,p=""):
    if isinstance(o,dict):
        for k,v in o.items():
            if isinstance(v,(int,float)) and ("call" in k or "audio" in k or "second" in k or "metered" in k):
                print(f"  {p}{k} = {v}")
            elif isinstance(v,(dict,)) and len(p)<40: walk(v,p+k+".")
walk(d)
PY
echo "=== driver log tail (the run's own totals) ==="
grep -iE "metered|calls|audio.*second|COMPLETED|ABORTED" /home/chao/SAEA-P2-r0bias-20260816T002101Z.log | tail -25
