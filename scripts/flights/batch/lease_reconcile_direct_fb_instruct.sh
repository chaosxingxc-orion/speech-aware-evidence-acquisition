#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Reconcile the flight.lock left by the 266-E Instruct arm SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-V1 (flight commit 77b2283e9),
# which ABORTED at 2026-10-11T20:07:46Z BEFORE any model contact (0 calls, 0.0 speech-seconds): the runner's knowledge-source
# guard refused the AgentLoop because every Fold B query id is in the pinned FULL-TRAIN knowledge snapshot's source roster
# (RailsRunnerError "AgentLoop query samples overlap the TRAIN knowledge source roster"). Copy of lease_reconcile_psv1.sh with
# the run id, package, evidence and authorisation changed. The lock is filed into the package, never deleted. The run and
# attempt trees are left untouched: recovery is the cell's single rec1 re-registration after the knowledge pin is corrected
# to the fold-excluded view (registry entry of 2026-10-11, coordinator Fable 5.1).
DATA=$SAEA_DATA_ROOT
/home/chao/.venvs/speechrl/bin/python - "$DATA" <<'PY'
import json, io, os, sys, hashlib, subprocess, shutil
from datetime import datetime, timezone
DATA = sys.argv[1]
RUN_ID = "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-V1"
ATT_ID = "attempt-slurp-direct-only-fold-b-instruct-generation-v1"
EXPECTED_PID = 1294953
STOP = "/home/chao/batch-STOP"
DRIVER_LOG = "/home/chao/batch-driver.out"
CAMPAIGN_LOG = "/home/chao/batch-campaign-1-direct-fb-instruct-20261011T200438Z.log"
GUARD = "AgentLoop query samples overlap the TRAIN knowledge source roster"
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
ps = subprocess.run(["bash", "-c", "ps -eo pid,cmd | grep -E 'flight.cli|rails.runner|native_episode|batch_driver|speech_preparation|lease_cli' | grep -vE 'grep|session.serving|serving_monitor|lease_reconcile'"], capture_output=True, text=True).stdout.strip()
import urllib.request
slots = json.load(urllib.request.urlopen("http://127.0.0.1:8080/slots", timeout=5))
processing = sum(1 for s in slots if s.get("is_processing"))
assert processing == 0 and not ps, (processing, ps)
stop_text = open(STOP, encoding="utf-8").read().strip() if os.path.exists(STOP) else None
att_rec_path = f"{DATA}/attempts/{RUN_ID}/{ATT_ID}.json"
state = json.load(io.open(att_rec_path, encoding="utf-8"))
assert state.get("state") == "ABORTED", state.get("state")
assert GUARD in (state.get("failure_reason") or ""), (state.get("failure_reason") or "")[:200]
assert state.get("actual") == {"audio_seconds": 0.0, "calls": 0}, state.get("actual")
driver_tail = subprocess.run(["tail", "-c", "4000", DRIVER_LOG], capture_output=True, text=True).stdout
assert "arm failed on step 1" in driver_tail and '"rc":1' in driver_tail, "driver STOP line not found"
campaign_log_bytes = os.path.getsize(CAMPAIGN_LOG) if os.path.exists(CAMPAIGN_LOG) else None
att = f"{DATA}/runs/{RUN_ID}/{ATT_ID}"
fr = os.path.join(att, "flight-receipts.json")
stages = (json.load(io.open(fr, encoding="utf-8")).get("stages") or {}) if os.path.exists(fr) else {}
receipt_stages = sorted(stages.keys())
assert "run_phases" not in stages, receipt_stages
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
pkg = f"{DATA}/coordination/slurp-direct-only-fold-b-thinking-vs-instruct-v1"; os.makedirs(pkg, exist_ok=True)
preserved = f"{pkg}/flight-lock-preserved-{stamp}.json"
receipt = {
  "schema": "saea-flight-lock-reconciliation-v1",
  "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
  "reconciled_by": "coordinator Fable 5.1 (root)",
  "authorised_by": "coordinator Fable 5.1, 2026-10-11 (registry entry: 266-E Instruct arm ABORTED before the first contact)",
  "flight_lock": doc,
  "flight_lock_sha256": hashlib.sha256(raw).hexdigest(),
  "preserved_copy": preserved,
  "dead_pid_proof": {"pid": pid, "os_kill_0": "ProcessLookupError", "ps_p_returncode": ps_pid.returncode, "ps_p_stdout": ps_pid.stdout.strip()},
  "stop_marker": {"path": STOP, "text": stop_text},
  "driver_log": DRIVER_LOG,
  "campaign_log": {"path": CAMPAIGN_LOG, "bytes": campaign_log_bytes, "note": "empty: the runner refused inside run_phases before any contact; the failure is recorded in the attempt record"},
  "abort": {
    "kind": "pre-contact knowledge-source roster guard",
    "abort_at_utc": "2026-10-11T20:07:46Z",
    "flight_commit": "77b2283e9145d684fa6ac2edd7179df7add109de",
    "error": "RailsRunnerError: " + GUARD + ": [the 1,080 Fold B ids]",
    "raised_in": "rails/runner.py run_agent_loop: overlap = set(sample_ids) & set(knowledge_snapshot.source_sample_ids)",
    "root_cause": "the four 266-E baseline fragments pin the FULL-TRAIN knowledge view size-full-content-slot-fillers-intent-slot-frame (sha 609854e4..., 50,628 source rows, every Fold B id inside); the fold-excluded twin ...-tfrl-folds-v1 (sha 9c64e8ec..., 37,407 rows, 0 Fold A/B ids) is the pin every TRAIN-fold cell uses",
    "attempt_record": att_rec_path,
    "attempt_state": state.get("state"),
    "attempt_actual": state.get("actual"),
    "attempt_reserved": state.get("reserved"),
    "flight_receipt_stages": receipt_stages,
    "not_serving_death": "resident Instruct server (session serving-slurp-native-candidate-five-train-a-np4-v1) alive and idle at reconciliation; health ok",
    "not_cli_hazard_stop": "STOP written by the driver's arm-inspect step (campaign rc 1, inspect rc 2: no run manifest because the runner refused before the first contact)",
    "recovery": "the cell's single rec1 re-registration (new generation attempt id and new FIT run + attempt id) after the knowledge pin is corrected; the smoke, Thinking and replicate attempts never opened and keep their ids; run and attempt trees preserved",
  },
  "quiescence": {
    "owner_pid_alive": False, "server_slots": len(slots), "server_slots_processing": processing,
    "established_connections_to_8080": int(subprocess.run(["bash", "-c", "ss -tn | grep ':8080' | grep -c ESTAB"], capture_output=True, text=True).stdout.strip() or 0),
    "flight_or_lease_processes": ps,
  },
  "reason": "The 266-E Instruct arm aborted before any model contact on the knowledge-source roster guard (full-TRAIN snapshot pinned on a TRAIN Fold B cell); the campaign process is dead; the lock is stale.",
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
print("slots", len(slots), "processing", processing)
print("locks now:", sorted(os.listdir(f"{DATA}/locks")))
print("STOP present:", os.path.exists(STOP))
PY
