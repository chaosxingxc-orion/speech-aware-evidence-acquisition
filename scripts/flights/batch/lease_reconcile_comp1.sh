#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Reconcile the flight.lock left by the aborted COMP-1 arm SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1
# (abort 2026-09-28T03:28:18Z; copy of lease_reconcile_e35.sh with the run id, records package,
# STOP evidence and authorisation changed). The lock is filed into the run's records, never deleted.
DATA=$SAEA_DATA_ROOT
/home/chao/.venvs/speechrl/bin/python - "$DATA" <<'PY'
import json, io, os, sys, hashlib, subprocess, shutil
from datetime import datetime, timezone
DATA = sys.argv[1]
RUN_ID = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
EXPECTED_PID = 397454
STOP = "/home/chao/batch-STOP"
DRIVER_LOG = "/home/chao/batch-campaign-1-comp1-20260928T004655Z.log"
lock = f"{DATA}/locks/flight.lock"
raw = open(lock, "rb").read(); doc = json.loads(raw)
assert doc["run_id"] == RUN_ID, doc["run_id"]
pid = doc["pid"]
assert pid == EXPECTED_PID, pid
try: os.kill(pid, 0); alive = True
except ProcessLookupError: alive = False
assert not alive, "owner pid alive"
ps_pid = subprocess.run(["ps", "-p", str(pid), "-o", "pid="], capture_output=True, text=True)
assert ps_pid.returncode != 0 and not ps_pid.stdout.strip(), ps_pid.stdout
ps = subprocess.run(["bash", "-c", "ps -eo pid,cmd | grep -E 'flight.cli|rails.runner|native_episode|batch_driver|speech_preparation|lease_cli' | grep -vE 'grep|session.serving|serving_monitor|lease_reconcile'"], capture_output=True, text=True).stdout.strip().splitlines()
import urllib.request
slots = json.load(urllib.request.urlopen("http://127.0.0.1:8080/slots", timeout=5))
processing = sum(1 for s in slots if s.get("is_processing"))
assert processing == 0 and not ps, (processing, ps)
stop_text = open(STOP, encoding="utf-8").read().strip() if os.path.exists(STOP) else None
att = f"{DATA}/runs/{doc['run_id']}/{doc['attempt_id']}"
state = {}
for name in (os.listdir(att) if os.path.isdir(att) else []):
    if name.endswith(".json") and "attempt" in name and "receipt" not in name:
        state = json.load(io.open(os.path.join(att, name), encoding="utf-8")); break
receipt_stages = None
fr = os.path.join(att, "flight-receipts.json")
if os.path.exists(fr):
    receipt_stages = sorted((json.load(io.open(fr, encoding="utf-8")).get("stages") or {}).keys()) if isinstance(json.load(io.open(fr, encoding="utf-8")).get("stages"), dict) else None
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
pkg = f"{DATA}/coordination/slurp-stage3-comp1-fold-a-v1"; os.makedirs(pkg, exist_ok=True)
preserved = f"{pkg}/flight-lock-preserved-{stamp}.json"
receipt = {
  "schema": "saea-flight-lock-reconciliation-v1",
  "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
  "reconciled_by": "flight-operations agent (Claude Opus 5.5)",
  "authorised_by": "coordinator Fable 5.1, 2026-09-28",
  "flight_lock": doc,
  "flight_lock_sha256": hashlib.sha256(raw).hexdigest(),
  "preserved_copy": preserved,
  "dead_pid_proof": {
    "pid": pid,
    "os_kill_0": "ProcessLookupError",
    "ps_p_returncode": ps_pid.returncode,
    "ps_p_stdout": ps_pid.stdout.strip(),
  },
  "stop_marker": {"path": STOP, "text": stop_text},
  "driver_log": DRIVER_LOG,
  "quiescence": {
    "owner_pid_alive": False,
    "server_slots": len(slots),
    "server_slots_processing": processing,
    "established_connections_to_8080": int(subprocess.run(["bash","-c","ss -tn | grep ':8080' | grep -c ESTAB"],capture_output=True,text=True).stdout.strip() or 0),
    "flight_or_lease_processes": ps,
    "attempt_state": state.get("attempt_state") or state.get("state"),
    "attempt_actual": state.get("actual"),
    "attempt_failure_reason_head": (state.get("failure_reason") or state.get("failure") or "")[:300],
    "flight_receipt_stages": receipt_stages,
  },
  "reason": "The COMP-1 arm SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1 aborted at 2026-09-28T03:28:18Z (arm failed on step 1; see the STOP marker and driver log). Its GenerationLease preserved flight.lock by design. The owner pid is dead, the resident SLURP np4 server reports no processing slot, and no driver, campaign, worker, lease or preparation process is alive. The lock is filed into this run's records (never deleted) so the next queued flight can acquire it.",
  "action": "flight.lock copied to preserved_copy and moved to locks/flight.lock.reconciled-<stamp>; generation.guard left in place",
}
shutil.copy2(lock, preserved)
out = f"{pkg}/flight-lock-reconciliation-{stamp}.json"
io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, indent=2) + "\n")
os.replace(lock, f"{DATA}/locks/flight.lock.reconciled-{stamp}")
print("receipt", out); print("preserved", preserved)
print("attempt_state", receipt["quiescence"]["attempt_state"], "stages", receipt_stages)
print("slots", len(slots), "processing", processing)
print("locks now:", sorted(os.listdir(f"{DATA}/locks")))
PY
