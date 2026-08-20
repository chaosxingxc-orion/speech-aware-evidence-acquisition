#!/usr/bin/env bash
# Compile-check the launcher chain and unit-test the two repaired behaviours
# WITHOUT any model contact, server spawn, or socket.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pemb3l/env.sh
cd "$REPO"
exec > >(tee "$SCRATCH/syntax-check.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
python -m py_compile "$SCRATCH/launch_pemb3l_flight.py" "$SCRATCH/flight_identity.py" "$SCRATCH/preflight.py" "$SCRATCH/update_ledger.py"
echo "py_compile exit: $?"

echo
echo "=== zombie-safe _pid_alive: spawn a child, kill it, and prove the repair ==="
python - <<'PY'
import os
import subprocess
import sys
import time

sys.path.insert(0, os.environ["SCRATCH"])
sys.path.insert(0, os.environ["REPO"] + "/src")
from launch_pemb3l_flight import _pid_alive

child = subprocess.Popen(["/bin/sh", "-c", "sleep 300"])
pid = child.pid
print(f"child pid {pid}")
print(f"  alive while running                : {_pid_alive(pid)}  (expect True)")

os.kill(pid, 15)
time.sleep(1.0)

# THE OLD BUG, reproduced directly: signal 0 succeeds on the unreaped zombie.
signal_probe_says_alive = True
try:
    os.kill(pid, 0)
except ProcessLookupError:
    signal_probe_says_alive = False
print(f"  raw os.kill(pid, 0) after SIGTERM   : {signal_probe_says_alive}  "
      "(expect True -- this is the zombie that aborted attempt 1)")

print(f"  repaired _pid_alive after SIGTERM   : {_pid_alive(pid)}  (expect False)")
print(f"  repaired _pid_alive, second call    : {_pid_alive(pid)}  (expect False)")
try:
    child.wait(timeout=5)
except Exception:
    pass
PY
echo "zombie probe exit: $?"

echo
echo "=== arm_manifest_status against the REAL on-disk state (structural only) ==="
python - <<'PY'
import os
import sys

sys.path.insert(0, os.environ["SCRATCH"])
sys.path.insert(0, os.environ["REPO"] + "/src")
from launch_pemb3l_flight import arm_manifest_status
from speech_aware_evidence_acquisition.data.lock import data_root

root = data_root()
for arm_id in ("l1-last-bare", "l2-last-instruct", "l3-mean-instruct"):
    complete, info = arm_manifest_status(root, arm_id)
    print(f"  {arm_id}: complete={complete} entries={info.get('entry_count')} "
          f"audio={info.get('audio_entries')} text={info.get('text_entries')} "
          f"npy={info.get('npy_present')} distinct={info.get('distinct_vector_sha256')}")
print()
print("  expected: l1 and l2 complete=True (carried), l3 complete=False (still to fly)")
PY
echo "manifest status exit: $?"
echo "end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
