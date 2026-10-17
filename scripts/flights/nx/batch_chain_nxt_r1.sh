#!/bin/bash
# Decisions 77 / NX-T R1: fly the per-node thinking-policy column (TRAIN Fold B) through the batch driver, one SEGMENT per resident session.
# A driver run attaches to ONE session (BATCH_SESSION), so the read is one Thinking segment:
#
#   smoke   the four-row column smoke (an `engineering` driver step: it runs the registered smoke through the worker and the structural inspector and never
#           starts a campaign or a scoring job). Session: the THINK-BUDGET session.
#   arm     the five-arm column flight (one `cell` step, ONE session). REFUSES to start until the coordinator's sign-off marker exists (SIGNOFF_MARKER: a one-line
#           file after the coordinator read the smoke's per-arm per-node table with `bash scripts/flights/nx/nxt_r1_read.sh smoke` -- above all whether a
#           no-think arm still emits reasoning bytes or a think marker); it WAITS for the marker (NXT1_SIGNOFF_WAIT_SECONDS, default 43200) and aborts on a batch-STOP.
#   all     smoke, then the wait for the marker, then the column flight: the registered arc in ONE invocation (the default). REFUSES (exit 9) when the smoke attempt
#           already exists on the data root: a (run_id, attempt_id) pair is a one-time key and the sealed smoke is never re-flown.
#   arm-only  the RECOVERY entry (rec1, nxt_r1_family.RECOVERIES): the column flight alone under the rec1 attempt ids. REQUIRES the smoke to be sealed (its run manifest
#           reads COMPLETED, exit 9 otherwise) and the sign-off marker to exist already (exit 5 otherwise; it never waits). It SWAPS to the arm's chosen serving
#           geometry first when that session is not resident (`serving_swap.sh <target>`, the target from nxt_r1_family.ACTIVE_GEOMETRY: owner decision 315 A,
#           think-budget-np4 by default; np6 / np8 untested until their fragments land). Hold the idle watchdog (/home/chao/saea-queue/watchdog.hold) first.
#           `all` refuses (exit 9) when the arm's geometry is not the smoke's.
#           RECOVERY rec2 (owner ruling 320 B): when the arm cell declares resume_from (a mode-A resume of the stopped rec1 attempt) arm-only first verifies that the
#           predecessor trace on the data root still hashes to the declared sha256 and that the rec2 attempt does not exist yet (exit 6 otherwise); the driver then runs the
#           resume prelaunch replay gate itself (resume_gate_run) before the campaign opens. The step flies only the rows the predecessor did not complete.
#
# Registered order: swap to think-budget-np4 -> smoke -> sign-off -> the column flight -> swap back to slurp-np4. Both segments fly from ONE flight commit
# (/home/chao/nxt1-flight-commit.txt, written by the flip).
#
# PRECONDITIONS (the coordinator's; this script refuses on the first four): no flight, lease or driver process alive and the flight lock clear (serial GPU,
# ruling 303 A: the P3.1 chain has finished); the THINK-BUDGET session is the RESIDENT one (a mismatch exits 6 and starts nothing); the other geometry's session
# is not recorded resident; the cells are flipped (nxt_r1_flip.sh). WHILE the Thinking session is resident the idle watchdog MUST be held
# (/home/chao/saea-queue/watchdog.hold).
#   bash scripts/flights/nx/batch_chain_nxt_r1.sh [smoke|arm|all|arm-only]
SEGMENT=${1:-all}
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
DATA=$SAEA_DATA_ROOT
SHORT=nxt1
LOG=/home/chao/batch-chain-$SHORT.out
SIGNOFF_MARKER=/home/chao/nxt1-decode-signoff.marker
INSTRUCT_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
# The Thinking serving geometry (owner decision 315 A): the arm's session and swap target come from the family (nxt_r1_family.ACTIVE_GEOMETRY: the committed
# geometry-selection-v1.json, the np4 x 24k control when absent); the smoke is sealed on, and always uses, the control. Never a literal here.
eval "$(PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src /home/chao/.venvs/speechrl/bin/python -B -c \
  "import sys; sys.path.insert(0, '$MAIN/scripts/flights/nx'); import nxt_r1_family as f; print('THINK_SESSION=%s ARM_SWAP_TARGET=%s SMOKE_SESSION=%s SMOKE_SWAP_TARGET=%s' % (f.THINK_SESSION, f.THINK_SWAP_TARGET, f.CONTROL_SESSION, f.CONTROL_SWAP_TARGET))")" \
  || { echo "cannot read the serving geometry from the family"; exit 66; }
COMMIT=$(cat /home/chao/$SHORT-flight-commit.txt) || exit 1
OTHER=$INSTRUCT_SESSION
case "$SEGMENT" in
  smoke) export BATCH_SESSION=$SMOKE_SESSION; SWAP_TARGET=$SMOKE_SWAP_TARGET ;;
  arm|arm-only) export BATCH_SESSION=$THINK_SESSION; SWAP_TARGET=$ARM_SWAP_TARGET ;;
  all) [ "$THINK_SESSION" = "$SMOKE_SESSION" ] || { echo "segment all refused: the arm geometry ($ARM_SWAP_TARGET) differs from the smoke's ($SMOKE_SWAP_TARGET); fly the segments separately" >> $LOG; echo "refusing: all needs one geometry"; exit 9; }
       export BATCH_SESSION=$THINK_SESSION; SWAP_TARGET=$ARM_SWAP_TARGET ;;
  *) echo "usage: batch_chain_nxt_r1.sh [smoke|arm|all|arm-only]"; exit 64 ;;
esac

smoke_state() {  # prints sealed | opened | none for the registered smoke, read from the data root with the family's own ids
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src NXT1_MAIN=$MAIN NXT1_DATA=$DATA /home/chao/.venvs/speechrl/bin/python -B - <<'PY'
import json
import os
import sys

sys.path.insert(0, os.environ["NXT1_MAIN"] + "/scripts/flights/nx")
import nxt_r1_family as fam  # noqa: E402

s, data = fam.CELLS["smoke"], os.environ["NXT1_DATA"]
manifest = os.path.join(data, "runs", s["run"], s["attempt"], s["run"] + ".run-manifest.json")
attempt = os.path.join(data, "attempts", s["run"], s["attempt"] + ".json")
try:
    sealed = json.load(open(manifest, encoding="utf-8")).get("status") == "COMPLETED"
except (OSError, ValueError):
    sealed = False
print("sealed" if sealed else ("opened" if os.path.exists(attempt) else "none"))
PY
}
SMOKE_STATE=$(smoke_state)
case "$SEGMENT" in
  all) [ "$SMOKE_STATE" = none ] || { echo "segment all refused: the smoke attempt already exists on the data root (state $SMOKE_STATE); the sealed smoke is never re-flown; use arm-only" >> $LOG; echo "refusing: smoke state $SMOKE_STATE; use arm-only"; exit 9; } ;;
  arm-only)
    [ "$SMOKE_STATE" = sealed ] || { echo "segment arm-only refused: the smoke is not sealed (state $SMOKE_STATE)" >> $LOG; echo "refusing: smoke state $SMOKE_STATE"; exit 9; }
    [ -s "$SIGNOFF_MARKER" ] || { echo "segment arm-only refused: no sign-off marker $SIGNOFF_MARKER" >> $LOG; echo "refusing: no sign-off marker"; exit 5; } ;;
esac
if [ "$SEGMENT" = arm-only ]; then
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src NXT1_MAIN=$MAIN NXT1_DATA=$DATA /home/chao/.venvs/speechrl/bin/python -B - >> $LOG 2>&1 <<'PY' || { echo "arm-only refused: the resume precondition failed; abort" >> $LOG; echo "refusing: resume precondition"; exit 6; }
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ["NXT1_MAIN"] + "/scripts/flights/nx")
import nxt_r1_family as fam  # noqa: E402

data, spec = Path(os.environ["NXT1_DATA"]), fam.CELLS["arm"]
cell = json.loads((Path(os.environ["NXT1_MAIN"]) / "configs/experiment" / (spec["cell"] + ".json")).read_text(encoding="utf-8"))["cells"][0]
resume = cell.get("resume_from")
if resume is None:
    print("the arm cell declares no resume_from: an ordinary re-flown arm; nothing to check")
    raise SystemExit(0)
assert set(resume) == {"attempt_id", "trace_sha256"}, "resume_from is not the registered mode-A declaration"
assert resume == fam.RECOVERIES["arm"]["resume_from"], "resume_from is not the family's registered rec2 declaration"
trace = data / "runs" / spec["run"] / resume["attempt_id"] / (spec["run"] + ".trace.jsonl")
digest = hashlib.sha256()
with trace.open("rb") as handle:
    for block in iter(lambda: handle.read(1 << 20), b""):
        digest.update(block)
assert digest.hexdigest() == resume["trace_sha256"], "the predecessor trace moved"
# "Not yet opened" is the attempt RECORD (attempts/<run>/<attempt>.json: the one-time key the runtime itself refuses on), never the
# run directory alone: preflight-class steps run at flip time (the re-pin / registration passes of 2026-10-17 08:47Z and 08:53Z) write
# <run dir>/resume-declaration.json (runtime._write_resume_declaration, owner decision 309) before any gate touch, so the rec2 run
# directory legitimately exists holding exactly that declaration. Tolerate exactly that: the declaration must name this attempt, this
# run and the registered predecessor + trace sha, and nothing else may sit in the directory (an outputs/trace/manifest file = flown).
assert not (data / "attempts" / spec["run"] / (spec["attempt"] + ".json")).exists(), "the rec2 attempt record already exists on the data root"
run_dir = data / "runs" / spec["run"] / spec["attempt"]
if run_dir.exists():
    extra = sorted(p.name for p in run_dir.iterdir() if p.name != "resume-declaration.json")
    assert not extra, "the rec2 run directory holds more than the preflight declaration: %s" % extra[:5]
    decl = json.loads((run_dir / "resume-declaration.json").read_text(encoding="utf-8"))
    expect = {"schema": "saea-resume-declaration-v1", "run_id": spec["run"], "attempt_id": spec["attempt"],
              "predecessors": [{"attempt_id": resume["attempt_id"], "mode": "trace", "pin_sha256": resume["trace_sha256"]}]}
    assert decl == expect, "the preflight resume declaration in the rec2 run directory does not match the registered resume_from"
    print("rec2 run directory holds only the matching preflight resume declaration (tolerated)")
print("resume precondition OK: predecessor trace", resume["trace_sha256"][:12], "unchanged; attempt", spec["attempt"], "not yet opened")
PY
fi
echo "chain start $(date -u +%FT%TZ) segment $SEGMENT commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh|lease_cli' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
[ -e "$DATA/locks/flight.lock" ] && { echo "flight.lock present; abort" >> $LOG; exit 7; }
S=$DATA/serving/$BATCH_SESSION
if [ "$SEGMENT" = arm-only ] && { [ ! -f "$S/session.json" ] || [ -f "$S/session-stop.json" ]; }; then
  # the recovery entry swaps to the chosen geometry itself (serving_swap.sh <target> stops the other geometries and starts this one, strict readiness)
  echo "arm-only: session $BATCH_SESSION is not resident; swapping to $SWAP_TARGET $(date -u +%FT%TZ)" >> $LOG
  bash $SP/serving_swap.sh "$SWAP_TARGET" >> $LOG 2>&1 || { echo "serving_swap.sh $SWAP_TARGET failed; abort" >> $LOG; exit 6; }
fi
if [ ! -f "$S/session.json" ] || [ -f "$S/session-stop.json" ]; then echo "session $BATCH_SESSION is not resident (segment $SEGMENT); swap first (serving_swap.sh $SWAP_TARGET); abort" >> $LOG; exit 6; fi
O=$DATA/serving/$OTHER
if [ -f "$O/session.json" ] && [ ! -f "$O/session-stop.json" ]; then echo "the other geometry's session $OTHER is still recorded resident; stop it first; abort" >> $LOG; exit 6; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt

run_driver() {  # run_driver <segment> : write the queue for that segment and run the batch driver
  for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
  NXT1_SEGMENT=$1 NXT1_MAIN=$MAIN /home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
import os
import sys

sys.path.insert(0, os.environ["NXT1_MAIN"] + "/scripts/flights/nx")
import nxt_r1_family as fam  # noqa: E402

segment = os.environ["NXT1_SEGMENT"]
C = fam.CONTACTS_PER_ROW


def arm_step(order):
    spec = fam.CELLS["arm"]
    stem = spec["cell"][: -len("-v1")]
    return {"order": order, "short": "nxt1-arm", "kind": "cell", "experiment": spec["cell"], "cell": spec["cell"],
            "smoke_experiment": None, "smoke_cell": None, "smoke_run_id": None, "smoke_attempt_id": None,
            "campaign_plan": spec["campaign"], "run_id": spec["run"], "fit_run_id": spec["fit_run"],
            "gen_attempt_id": spec["attempt"], "expected_rows": spec["rows"], "contacts_per_row": C, "ceiling_per_row": C, "notool": True,
            "owner": f"root-{stem}-v1"}


def smoke_step(order):
    spec = fam.CELLS["smoke"]
    return {"order": order, "short": "nxt1-smoke", "kind": "engineering", "experiment": spec["cell"], "cell": spec["cell"],
            "smoke_experiment": spec["cell"], "smoke_cell": spec["cell"], "campaign_plan": None, "run_id": spec["run"], "fit_run_id": spec["fit_run"],
            "gen_attempt_id": spec["attempt"], "smoke_run_id": spec["run"], "smoke_attempt_id": spec["attempt"],
            "expected_rows": fam.SMOKE_ROWS, "contacts_per_row": C, "ceiling_per_row": C, "notool": True, "owner": f"root-{spec['cell']}"}


steps = {"smoke": [smoke_step(1)], "arm": [arm_step(1)]}[segment]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
  echo "queue [segment $1] written; starting driver $(date -u +%FT%TZ)" >> $LOG
  bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
  RC=$?
  echo "driver exit $RC segment $1 $(date -u +%FT%TZ)" >> $LOG
  return $RC
}

wait_signoff() {
  local waited=0 limit=${NXT1_SIGNOFF_WAIT_SECONDS:-43200}
  while [ ! -s "$SIGNOFF_MARKER" ]; do
    [ -e /home/chao/batch-STOP ] && { echo "batch-STOP present while waiting for the sign-off; abort" >> $LOG; return 8; }
    [ $waited -ge $limit ] && { echo "no sign-off marker $SIGNOFF_MARKER after ${limit}s; abort (the column flight is not opened)" >> $LOG; return 5; }
    [ $((waited % 600)) -eq 0 ] && echo "waiting for the sign-off marker $SIGNOFF_MARKER ($waited s) $(date -u +%FT%TZ)" >> $LOG
    sleep 60; waited=$((waited + 60))
  done
  echo "sign-off marker present: $(head -c 200 "$SIGNOFF_MARKER" | tr '\n' ' ')" >> $LOG
  return 0
}

case "$SEGMENT" in
  smoke) run_driver smoke; exit $? ;;
  arm) wait_signoff || exit $?; run_driver arm; exit $? ;;
  arm-only) run_driver arm; exit $? ;;
  all) run_driver smoke || exit $?; wait_signoff || exit $?; run_driver arm; exit $? ;;
esac
