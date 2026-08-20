#!/usr/bin/env bash
# Abort ONE attempt durably and snapshot its evidence for the flight archive.
# A protocol amendment (a changed server recipe -> a changed config/protocol
# hash) means the attempt's own ExecutionPlan no longer describes what would
# fly, so the attempt is closed and a successor is opened. Spent contacts stay
# spent: AttemptStore.prior_actual_usage charges them against the SAME plan
# ceiling in the successor.
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"

ATTEMPT="$1"
REASON="$2"

python - "$ATTEMPT" "$REASON" <<'PY'
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, ".")
from speech_aware_evidence_acquisition.core.attempts import AttemptStore
from speech_aware_evidence_acquisition.data.lock import data_root
import flight_identity as fid

attempt_id, reason = sys.argv[1], sys.argv[2]
root = data_root()
store = AttemptStore(attempts_root=root / "attempts")
handle = store.handle(fid.run_id(), attempt_id)
calls, audio = handle.actual_totals()
gpu = handle.actual_gpu_seconds()
print(f"attempt {attempt_id}: state={handle.state()} calls={calls} audio_seconds={audio} gpu_seconds={gpu}")
if handle.state() == "OPENED":
    handle.mark_aborted(reason)
    print(f"attempt {attempt_id} ABORTED: {reason}")
else:
    print(f"attempt {attempt_id} already terminal ({handle.state()}); not re-aborting")

run_dir = root / "runs" / fid.run_id() / attempt_id
out = Path(".") / f"aborted-{attempt_id}"
out.mkdir(parents=True, exist_ok=True)
for name in ("flight-state.json", f"{fid.run_id()}.plan.json", f"{fid.run_id()}.config-values.json"):
    src = run_dir / name
    if src.is_file():
        shutil.copy2(src, out / name)
        print("snapshot:", name)
for src in run_dir.glob("*.server.log"):
    shutil.copy2(src, out / src.name)
    print("snapshot:", src.name)
shutil.copy2(root / "attempts" / fid.run_id() / f"{attempt_id}.json", out / "attempt-state.json")
print("snapshot: attempt-state.json")
PY
