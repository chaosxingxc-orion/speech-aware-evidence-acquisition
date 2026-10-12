#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
D=$SAEA_DATA_ROOT
tail -2 /home/chao/batch-status.jsonl | cut -c1-300; ls /home/chao/batch-STOP 2>/dev/null
for r in SAEA-E21-NATIVE-WINDOW-DIRECT-SUB10-V1 SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1; do echo "$r: $(cat $D/attempts/$r/*.json 2>/dev/null | grep -o '"calls": [0-9]*\|"state": "[A-Z]*' | tr '\n' ' ')"; done
nvidia-smi --query-gpu=utilization.gpu,power.draw --format=csv,noheader
echo "== scores structure (direct four-row)"
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json,glob
p=glob.glob("$SAEA_DATA_ROOT/runs/SAEA-E21-NATIVE-WINDOW-DIRECT-FOUR-ROW-V1/attempt-e21-native-window-direct-four-row-v1/*.scores.json")[0]
d=json.load(open(p)); print("top keys", list(d.keys()))
for k,v in d.items():
    if isinstance(v,dict): print(k, "->", {kk:(vv if not isinstance(vv,(dict,list)) else (type(vv).__name__+":"+str(list(vv.keys())[:8] if isinstance(vv,dict) else len(vv)))) for kk,vv in list(v.items())[:10]})
p2=glob.glob("$SAEA_DATA_ROOT/runs/SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-V1/attempt-e21-native-window-system-four-row-recovery-v4/*.scores.json")
if p2:
    d=json.load(open(p2[0])); print("system four-row top keys", list(d.keys()))
    for k,v in d.items():
        if isinstance(v,dict) and "aggregate" in v: print(k, "aggregate", {kk:vv for kk,vv in v["aggregate"].items() if isinstance(vv,(int,float))})
PY
