#!/usr/bin/env bash
# 2026-08-19 amendment item 4 accounting: the 35-call TXT duplicate sub-block.
# Structural keys ONLY -- 'arm', 'sample_id', 'silence_swapped', 'txt_duplicate'.
# Never touches 'response_text', 'messages', 'metrics' or 'consumption'.
# Usage: txt_dup_counts.sh <attempt-id>
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pkey2fly/env.sh
RD="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338/$1"

python - "$RD" <<'PY'
import json, sys, pathlib
from collections import Counter, defaultdict
rd = pathlib.Path(sys.argv[1])

dupflag = Counter()
keyed = defaultdict(int)
dup_ids, swap_ids = set(), set()
rowkeys = None
n = 0
with (rd / "outputs.jsonl").open(encoding="utf-8") as fh:
    for line in fh:
        if not line.strip():
            continue
        row = json.loads(line)
        n += 1
        if rowkeys is None:
            rowkeys = sorted(row.keys())
        arm, sid = row["arm"], row["sample_id"]
        td, sw = bool(row.get("txt_duplicate")), bool(row.get("silence_swapped"))
        dupflag[(arm, td)] += 1
        keyed[(arm, sid, sw, td)] += 1
        if td:
            dup_ids.add(sid)
        if sw:
            swap_ids.add(sid)
        del row  # never inspect the forbidden keys

print(f"total rows: {n}")
print(f"row top-level keys: {rowkeys}")
print()
print("=== (arm, txt_duplicate) counts ===")
for (arm, td), c in sorted(dupflag.items()):
    print(f"  {arm:12s} txt_duplicate={td}: {c}")
print()
print(f"distinct txt_duplicate sample ids: {len(dup_ids)}")
print(f"distinct silence_swap  sample ids: {len(swap_ids)}")
print()
d = {k: v for k, v in keyed.items() if v > 1}
print("=== duplicate (arm, sample_id, silence_swapped, txt_duplicate) keys ===")
print(f"  {len(d)} duplicates")
PY
