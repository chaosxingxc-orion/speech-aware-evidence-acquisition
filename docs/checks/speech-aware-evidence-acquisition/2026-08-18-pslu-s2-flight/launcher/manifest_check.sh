#!/usr/bin/env bash
# Usage: manifest_check.sh <attempt-id>
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pslus2fly/env.sh
RD="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-s2-183/$1"

python - "$RD" <<'PY'
import json, sys, pathlib
rd = pathlib.Path(sys.argv[1])

m = json.loads((rd / "SAEA-PROBE-pslu-s2-183.trace-manifest.json").read_text(encoding="utf-8"))
print("=== trace-manifest top-level keys ===")
for k, v in m.items():
    if isinstance(v, (list, dict)):
        print(f"  {k}: <{type(v).__name__} len={len(v)}>")
    else:
        print(f"  {k}: {v}")

print()
print("=== session receipt ===")
s = json.loads((rd / "SAEA-PROBE-pslu-s2-183.session-receipt.json").read_text(encoding="utf-8"))
for k, v in s.items():
    if isinstance(v, (list, dict)):
        print(f"  {k}: <{type(v).__name__} len={len(v)}>")
    else:
        print(f"  {k}: {v}")

print()
print("=== plan ===")
p = json.loads((rd / "SAEA-PROBE-pslu-s2-183.plan.json").read_text(encoding="utf-8"))
for k, v in p.items():
    print(f"  {k}: {v}")
PY
