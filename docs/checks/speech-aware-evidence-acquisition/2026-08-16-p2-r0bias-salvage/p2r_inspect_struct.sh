#!/usr/bin/env bash
# Find (1) a timestamp field in trace records, (2) the featcache dir,
# (3) the server.log "encoding" line shape. Read-only.
set -uo pipefail
OLD=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59
echo "=== trace record shape (first MODEL_RESPONSE, keys only) ==="
python3 - "$OLD/SAEA-P2-r0bias.trace.jsonl" <<'PY'
import json,sys
for ln in open(sys.argv[1],encoding="utf-8"):
    d=json.loads(ln)
    ch=d.get("channel")
    p=d.get("payload",{})
    if isinstance(p,dict) and p.get("record_type")=="MODEL_RESPONSE" or "MODEL_RESPONSE" in ln:
        print("channel:",ch)
        print("record_id:",d.get("record_id"))
        if isinstance(p,dict):
            print("payload keys:",list(p.keys()))
            for k,v in p.items():
                if any(t in k.lower() for t in ("time","stamp","clock","at","dur","sec")):
                    print(f"  {k} = {str(v)[:120]}")
        break
PY
echo
echo "=== server.log encoding-line shape (old arm) ==="
grep -icE "encoding" "$OLD/SAEA-P2-r0bias.server.log" 2>/dev/null || echo "grep failed"
grep -iE "encod" "$OLD/SAEA-P2-r0bias.server.log" 2>/dev/null | head -5
echo
echo "=== server.log first/last timestamped lines ==="
head -3 "$OLD/SAEA-P2-r0bias.server.log"
echo "..."
tail -3 "$OLD/SAEA-P2-r0bias.server.log"
echo
echo "=== featcache dir candidates ==="
ls -la /home/chao 2>/dev/null | grep -iE "feat|cache" || echo "  none in /home/chao"
find /home/chao -maxdepth 3 -type d -iname "*featcache*" -o -maxdepth 3 -type d -iname "*feat_cache*" 2>/dev/null | head
env | grep -i cache || echo "  no cache env here"
echo "=== SPEECHRL_DATA_DIR cache dirs ==="
ls -la /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data 2>/dev/null | head -20
