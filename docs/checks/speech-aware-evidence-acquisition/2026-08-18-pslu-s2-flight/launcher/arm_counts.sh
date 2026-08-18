#!/usr/bin/env bash
# Structural row accounting ONLY: reads the 'arm', 'sample_id', 'silence_swapped' keys
# and the closed_set_mapping's OWN 'fallback'/'outcome' machinery flags (structural
# counters). Never touches 'response_text', 'messages', 'metrics', 'consumption',
# 'predicted_raw' or 'canonical_label'.
# Usage: arm_counts.sh <attempt-id>
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pslus2fly/env.sh
RD="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-s2-183/$1"

python - "$RD" <<'PY'
import json, sys, pathlib
from collections import Counter, defaultdict
rd = pathlib.Path(sys.argv[1])

arms = Counter()
swapped = Counter()
samples_per_arm = defaultdict(set)
fallback = Counter()
outcomes = Counter()
dupes = Counter()
n = 0
with (rd / "outputs.jsonl").open(encoding="utf-8") as fh:
    for line in fh:
        if not line.strip():
            continue
        row = json.loads(line)
        n += 1
        arm = row["arm"]
        arms[arm] += 1
        samples_per_arm[arm].add(row["sample_id"])
        dupes[(arm, row["sample_id"], bool(row.get("silence_swapped")))] += 1
        if row.get("silence_swapped"):
            swapped[arm] += 1
        m = row.get("closed_set_mapping")
        if m is not None:
            fallback[bool(m.get("fallback"))] += 1
            outcomes[str(m.get("outcome"))] += 1
        del row  # never inspect the forbidden keys

print(f"total rows: {n}")
print()
print("=== rows per arm ===")
for arm, c in sorted(arms.items()):
    print(f"  {arm:24s} rows={c:4d}  distinct samples={len(samples_per_arm[arm])}")
print()
print("=== silence-swapped rows per arm ===")
for arm, c in sorted(swapped.items()):
    print(f"  {arm:24s} {c}")
print(f"  total swapped rows: {sum(swapped.values())}")
print()
print("=== duplicate (arm, sample_id, silence_swapped) keys ===")
d = {k: v for k, v in dupes.items() if v > 1}
print(f"  {len(d)} duplicates" + (f": {sorted(d)[:5]}" if d else ""))
print()
print("=== A1r-phase1 closed-set mapping (structural machinery flags, not content) ===")
for k, c in sorted(fallback.items()):
    print(f"  fallback={k}: {c}")
print(f"  non-fallback total: {fallback.get(False, 0)} / {sum(fallback.values())}")
for k, c in sorted(outcomes.items()):
    print(f"  outcome[{k}]: {c}")
PY
