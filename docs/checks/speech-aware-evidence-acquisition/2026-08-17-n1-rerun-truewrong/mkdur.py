import json, os
from pathlib import Path
DATA = Path(os.environ["SPEECHRL_DATA_DIR"])
base = DATA/"runs/SAEA-P2-r1verify/attempt-20260816T105836Z-b06529"
out = {}
for f in sorted(base.glob("SAEA-P2-r1verify.replay-derivation.*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    out[d["sample_id"]] = d["decoded_duration_seconds"]
Path(os.environ["S"], "durations.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
