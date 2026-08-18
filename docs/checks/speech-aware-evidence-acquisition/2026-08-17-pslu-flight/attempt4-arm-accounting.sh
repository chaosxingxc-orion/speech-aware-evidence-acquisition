#!/usr/bin/env bash
# Structural row accounting ONLY: reads the 'arm', 'sample_id', 'silence_swapped' and
# 'phase1_scenario_parsed' keys. Never touches 'response_text', 'messages' or 'metrics'.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pslufly4/env.sh
RD="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/attempt-20260818T010218Z-4c97cb"

python - "$RD" <<'PY'
import json, sys, pathlib
from collections import Counter, defaultdict
rd = pathlib.Path(sys.argv[1])

FORBIDDEN = {"response_text", "messages", "metrics", "consumption"}

arms = Counter()
swapped = Counter()
samples_per_arm = defaultdict(set)
parsed = Counter()
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
        if row.get("silence_swapped"):
            swapped[arm] += 1
        if row.get("phase1_scenario_parsed") is not None:
            parsed[bool(row["phase1_scenario_parsed"])] += 1
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
print("=== phase-1 scenario parse flag (structural, not a metric) ===")
for k, c in sorted(parsed.items()):
    print(f"  parsed={k}: {c}")

ps = json.loads((rd / "predicted-scenarios.json").read_text(encoding="utf-8"))
print()
print(f"predicted-scenarios.json: {len(ps)} sample entries (values NOT printed)")
PY
