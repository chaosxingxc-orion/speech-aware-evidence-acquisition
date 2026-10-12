#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Reconcile the flight.lock left by the aborted B9a arm (precedent: coordination/slurp-b1-exemplars-k20-anchor-v2/flight-lock-reconciliation-20260917T100537Z.json).
DATA=$SAEA_DATA_ROOT
/home/chao/.venvs/speechrl/bin/python - "$DATA" <<'PY'
import json, io, os, sys, hashlib, subprocess, shutil
from datetime import datetime, timezone
DATA = sys.argv[1]
lock = f"{DATA}/locks/flight.lock"
raw = open(lock, "rb").read(); doc = json.loads(raw)
assert doc["run_id"].startswith("SAEA-E21-NATIVE-WINDOW-"), doc["run_id"]
pid = doc["pid"]
try: os.kill(pid, 0); alive = True
except ProcessLookupError: alive = False
assert not alive, "owner pid alive"
ps = subprocess.run(["bash", "-c", "ps -eo pid,cmd | grep -E 'flight.cli|rails.runner|native_episode|batch_driver|speech_preparation' | grep -vE 'grep|session.serving|serving_monitor'"], capture_output=True, text=True).stdout.strip().splitlines()
import urllib.request
slots = json.load(urllib.request.urlopen("http://127.0.0.1:8080/slots", timeout=5))
processing = sum(1 for s in slots if s.get("is_processing"))
assert processing == 0 and not ps, (processing, ps)
att = f"{DATA}/runs/{doc['run_id']}/{doc['attempt_id']}"
state = {}
for name in (os.listdir(att) if os.path.isdir(att) else []):
    if name.endswith("attempt.json") or name.endswith("-attempt.json") or name == "attempt.json":
        state = json.load(io.open(os.path.join(att, name), encoding="utf-8")); break
if not state:
    for name in (os.listdir(att) if os.path.isdir(att) else []):
        if name.endswith(".json") and "attempt" in name:
            state = json.load(io.open(os.path.join(att, name), encoding="utf-8")); break
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
pkg = f"{DATA}/coordination/e21-native-window-flightruntime-e35-v1"; os.makedirs(pkg, exist_ok=True)
preserved = f"{pkg}/flight-lock-preserved-{stamp}.json"
receipt = {
  "schema": "saea-flight-lock-reconciliation-v1",
  "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
  "reconciled_by": "root (Fable 5.1 coordinator)",
  "flight_lock": doc,
  "flight_lock_sha256": hashlib.sha256(raw).hexdigest(),
  "preserved_copy": preserved,
  "quiescence": {
    "owner_pid_alive": False,
    "server_slots": len(slots),
    "server_slots_processing": processing,
    "established_connections_to_8080": int(subprocess.run(["bash","-c","ss -tn | grep ':8080' | grep -c ESTAB"],capture_output=True,text=True).stdout.strip() or 0),
    "flight_or_lease_processes": ps,
    "attempt_state": state.get("attempt_state") or state.get("state"),
    "attempt_actual": state.get("actual"),
    "attempt_failure_reason_head": (state.get("failure_reason") or state.get("failure") or "")[:300],
  },
  "reason": "An E35 arm on the E21 geometry aborted before completing (a pre-contact or early registration refusal; see the attempt record); its GenerationLease preserved flight.lock by design. The owner process is gone, the resident E21 server reports no processing slot and no established client connection, no flight, lease or preparation process is alive, and the attempt is ABORTED. The lock is moved aside (never deleted) so the next attempt can acquire it.",
  "action": "flight.lock moved to preserved_copy; generation.guard left in place",
}
shutil.copy2(lock, preserved)
out = f"{pkg}/flight-lock-reconciliation-{stamp}.json"
io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, indent=2) + "\n")
os.replace(lock, f"{DATA}/locks/flight.lock.reconciled-{stamp}")
print("receipt", out); print("attempt_state", receipt["quiescence"]["attempt_state"], receipt["quiescence"]["attempt_actual"]); print("failure:", receipt["quiescence"]["attempt_failure_reason_head"][:160])
print("locks now:", sorted(os.listdir(f"{DATA}/locks")))
PY
