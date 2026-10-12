#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Reconcile the flight.lock left by the P-SV-1 arm SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1 (flight commit b9af3e58), which
# flew all 1,080 rows (8,709 calls) and ABORTED at seal (2026-09-29T14:19:36Z, BundleError on the seal invariant I7v:
# "perception branch candidate_intent_ids must be a non-empty ordered list of distinct non-empty strings"; copy of
# lease_reconcile_e4.sh with the run id, records package, STOP evidence, seal-abort evidence and authorisation
# changed). The lock is filed into the run's records, never deleted. The run and attempt trees are left untouched:
# recovery is expected to be seal-only after the receipt fix (no re-fly, no re-pin of the flown attempt). P-SV-2 is
# held back (same validator) and the P-SV queue must not be restarted.
DATA=$SAEA_DATA_ROOT
/home/chao/.venvs/speechrl/bin/python - "$DATA" <<'PY'
import json, io, os, sys, hashlib, subprocess, shutil
from datetime import datetime, timezone
DATA = sys.argv[1]
RUN_ID = "SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1"
ATT_ID = "attempt-slurp-native-stage3-psv1-fold-b-generation-v1"
EXPECTED_PID = 625526
STOP = "/home/chao/batch-STOP"
DRIVER_LOG = "/home/chao/batch-campaign-1-psv1-20260929T115157Z.log"
INVARIANT = "perception branch candidate_intent_ids must be a non-empty ordered list of distinct non-empty strings"
lock = f"{DATA}/locks/flight.lock"
raw = open(lock, "rb").read(); doc = json.loads(raw)
assert doc["run_id"] == RUN_ID, doc["run_id"]
assert doc["attempt_id"] == ATT_ID, doc["attempt_id"]
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
# Attempt record (the precedent's in-run lookup finds none for this run; the record lives under attempts/).
att_rec_path = f"{DATA}/attempts/{RUN_ID}/{ATT_ID}.json"
state = json.load(io.open(att_rec_path, encoding="utf-8"))
assert state.get("state") == "ABORTED", state.get("state")
assert INVARIANT in (state.get("failure_reason") or ""), state.get("failure_reason")
# Driver log: the abort must be the seal invariant (traceback through FlightRuntime.seal), not a serving death.
log_tail = subprocess.run(["tail", "-c", "20000", DRIVER_LOG], capture_output=True, text=True).stdout
assert "flight.seal()" in log_tail and "BundleError" in log_tail and INVARIANT in log_tail and "(I7v)" in log_tail, "seal traceback not found"
att = f"{DATA}/runs/{RUN_ID}/{ATT_ID}"
fr = os.path.join(att, "flight-receipts.json")
stages = json.load(io.open(fr, encoding="utf-8")).get("stages") or {}
rp = stages.get("run_phases") or {}
receipt_stages = sorted(stages.keys())
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
pkg = f"{DATA}/coordination/slurp-stage3-psv1-fold-b-v1"; os.makedirs(pkg, exist_ok=True)
preserved = f"{pkg}/flight-lock-preserved-{stamp}.json"
receipt = {
  "schema": "saea-flight-lock-reconciliation-v1",
  "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
  "reconciled_by": "flight-operations agent (Claude Opus 5.5)",
  "authorised_by": "coordinator Fable 5.1, 2026-09-29 (ops brief 14:30Z)",
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
  "abort": {
    "kind": "seal-invariant I7v",
    "abort_at_utc": "2026-09-29T14:19:36Z",
    "flight_commit": "b9af3e58",
    "error": "BundleError: outputs row <row id> (request flight-0183): perception-branch receipt is invalid: perception branch candidate_intent_ids must be a non-empty ordered list of distinct non-empty strings (I7v)",
    "invariant": INVARIANT,
    "raised_in": "FlightRuntime.seal -> verify_bundle -> _verify_outputs_trace_binding -> _verify_perception_branch_trace_binding -> refuse (core/bundle/outputs.py)",
    "attempt_record": att_rec_path,
    "attempt_state": state.get("state"),
    "attempt_actual": state.get("actual"),
    "attempt_reserved": state.get("reserved"),
    "attempt_failure_reason": state.get("failure_reason"),
    "run_phases_contact_count": rp.get("contact_count"),
    "run_phases_contact_window": rp.get("contact_window"),
    "run_phases_wall_seconds": rp.get("wall_seconds"),
    "preflight_sample_count": (stages.get("preflight") or {}).get("sample_count"),
    "flight_receipt_stages": receipt_stages,
    "not_serving_death": "run_phases completed; resident slurp-np4 server (session serving-slurp-native-candidate-five-train-a-np4-v1) alive and idle at reconciliation",
    "not_cli_hazard_stop": "STOP written by the driver's arm-inspect step (campaign rc 1, inspect rc 2: no run manifest because the seal raised)",
    "diagnosis_branch": "debugging agent branch (read-only on this run); owner decision 197 to be proposed",
    "recovery": "seal-only after the receipt fix, no re-fly, no re-pin of the flown attempt; run and attempt trees preserved",
    "psv2_hold": "P-SV-2 is held back: it runs the same I7v validator and must not fly until the fix lands and it is re-pinned",
    "psv_queue": "queue_psv.sh HALTed (exit 4) and must not be restarted; SAEA-Queue-PSV stays Ready, not re-run",
  },
  "quiescence": {
    "owner_pid_alive": False,
    "server_slots": len(slots),
    "server_slots_processing": processing,
    "established_connections_to_8080": int(subprocess.run(["bash","-c","ss -tn | grep ':8080' | grep -c ESTAB"],capture_output=True,text=True).stdout.strip() or 0),
    "flight_or_lease_processes": ps,
  },
  "reason": "The P-SV-1 arm SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1 flew all rows (run_phases complete, 8,709 calls) and aborted at seal at 2026-09-29T14:19:36Z on the seal invariant I7v (perception-branch receipt: candidate_intent_ids must be a non-empty ordered list of distinct non-empty strings). Its GenerationLease preserved flight.lock by design. The owner pid is dead, the resident SLURP np4 server reports no processing slot, and no driver, campaign, worker, lease or preparation process is alive. The lock is filed into this run's records (never deleted) so the next queued flight (COMP-1 seal-only + G5) can acquire it; P-SV-2 stays held.",
  "action": "flight.lock copied to preserved_copy and moved to locks/flight.lock.reconciled-<stamp>; generation.guard left in place; batch-STOP text recorded here, then the marker is moved to batch-STOP.<stamp>.bak",
}
shutil.copy2(lock, preserved)
out = f"{pkg}/flight-lock-reconciliation-{stamp}.json"
io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(receipt, indent=2) + "\n")
os.replace(lock, f"{DATA}/locks/flight.lock.reconciled-{stamp}")
if stop_text is not None:
    os.replace(STOP, f"{STOP}.{stamp}.bak")
print("receipt", out); print("preserved", preserved)
print("attempt_state", state.get("state"), "actual", state.get("actual"), "stages", receipt_stages)
print("contacts", rp.get("contact_count"), "window", rp.get("contact_window"))
print("slots", len(slots), "processing", processing)
print("locks now:", sorted(os.listdir(f"{DATA}/locks")))
print("STOP present:", os.path.exists(STOP))
PY
