#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# NX-T R1 SEAL-ONLY completion of the stopped column flight (owner decision 320 A, proposed) through the batch driver (owner decisions 22, 77).
# ONE queue of one step:
#   step 1 (nxt1seal, kind seal-only): core.flight.cli seal-only on the seal-only cell -- the attempt named by nxt_r1_family.sealonly_spec()["attempt"], resume_from the stopped
#          rec1 column attempt by TRACE sha256 (mode A), the roster the stopped attempt's complete rows. The predecessor covers the roster: ZERO model contacts, no lease, no
#          slot, no session attach; it seals the manifest and runs the one official finalize job. NO smoke and no campaign plan (the cell allows check / prepare-supply /
#          seal-only only). The driver's prelaunch is unchanged: it still requires the resident session idle and healthy, runs the registration gate and -- because the cell
#          declares resume_from -- the resume replay gate. The driver then inspects the seal-only attempt as an arm: FINALIZED, the roster's distinct rows, one score job,
#          manifest study_commit = the flight commit.
#
# Preconditions: nxt_r1_sealonly_flip.sh converged the seal-only cell at one HEAD and wrote /home/chao/nxt1seal-flight-commit.txt; the resident session is the Thinking
# session of the family; no other batch is running; the predecessor attempt directory is untouched; the idle watchdog is HELD (/home/chao/saea-queue/watchdog.hold) while the
# Thinking session is resident; and `/home/chao/batch-STOP` does NOT exist -- THIS CHAIN REFUSES (exit 8) WHILE IT EXISTS and never moves it aside (unlike the flight chains):
# the coordinator parks the queue with batch-STOP first and removes it only when it wants this chain to run.
#   bash scripts/flights/nx/batch_chain_nxt_r1_sealonly.sh
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
SP=$MAIN/scripts/flights/batch
DATA=$SAEA_DATA_ROOT
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-nxt1seal.out
QUEUE=/home/chao/batch-queue.json
PY=${SAEA_PY:-/home/chao/.venvs/speechrl/bin/python}
FLIGHT_FILE=/home/chao/nxt1seal-flight-commit.txt
STOP=/home/chao/batch-STOP
echo "chain start $(date -u +%FT%TZ)" >> $LOG
if [ -e "$STOP" ]; then echo "batch-STOP exists ($STOP); the coordinator parks the queue first and removes it deliberately; abort" >> $LOG; echo "refusing: batch-STOP exists"; exit 8; fi
[ -s "$FLIGHT_FILE" ] || { echo "no flight commit file $FLIGHT_FILE (run nxt_r1_sealonly_flip.sh first); abort" >> $LOG; echo "refusing: no flight commit"; exit 1; }
COMMIT=$(cat "$FLIGHT_FILE") || exit 1
# The identities come from the family; the session is the Thinking session of the arm's geometry.
eval "$(PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src $PY -B -c "
import sys; sys.path.insert(0, '$MAIN/scripts/flights/nx'); import nxt_r1_family as f
s = f.sealonly_spec()
print('THINK_SESSION=%s SWAP_TARGET=%s CELL=%s' % (f.THINK_SESSION, f.THINK_SWAP_TARGET, s['cell']))
")" || { echo "cannot read the seal-only identities from the family" >> $LOG; exit 66; }
export BATCH_SESSION=$THINK_SESSION
echo "chain commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh|lease_cli' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
[ -e "$DATA/locks/flight.lock" ] && { echo "flight.lock present; abort" >> $LOG; exit 7; }
S=$DATA/serving/$BATCH_SESSION
if [ ! -f "$S/session.json" ] || [ -f "$S/session-stop.json" ]; then echo "session $BATCH_SESSION is not resident; swap first (serving_swap.sh $SWAP_TARGET); abort" >> $LOG; exit 6; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO/src" $PY -B - "$REPO" "$DATA" <<'PY' >> $LOG 2>&1 || { echo "seal-only precondition refused; abort" >> $LOG; exit 6; }
import hashlib, json, sys
from pathlib import Path
repo, data = map(Path, sys.argv[1:3])
sys.path.insert(0, str(repo / "scripts/flights/nx"))
import nxt_r1_family as fam
S = fam.sealonly_spec()
RUN, FIT_RUN, PRED, SO, FSO = S["run"], S["fit_run"], S["predecessor_attempt"], S["attempt"], S["fit_attempt"]
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
cell = load(repo / f"configs/experiment/{S['experiment']}.json")["cells"][0]
assert cell["run_id"] == RUN and cell["readiness"]["state"] == "ready", cell["readiness"]["state"]
assert cell["attempt_id"] == SO, cell["attempt_id"]
assert "seal-only" in cell["allowed_execution_stages"] and "campaign" not in cell["allowed_execution_stages"] and "worker" not in cell["allowed_execution_stages"]
resume = cell["resume_from"]
assert set(resume) == {"attempt_id", "trace_sha256"} and resume["attempt_id"] == PRED, "resume_from is not the registered mode-A predecessor"
assert sha(data / f"runs/{RUN}/{PRED}/{RUN}.trace.jsonl") == resume["trace_sha256"], "the predecessor trace moved"
assert load(data / f"attempts/{RUN}/{PRED}.json")["state"] == "ABORTED", "the predecessor attempt is not ABORTED"
for path in (f"runs/{RUN}/{SO}", f"attempts/{RUN}/{SO}.json", f"prepared/{FIT_RUN}/{FSO}"):
    assert not (data / path).exists(), f"{path} already exists"
rows = load(repo / S["complete_rows"])
plan = load(repo / S["package"] / "generation-plan-registered-v1.json")
proof = plan["resume_replay_proof"]
n = rows["count"]
assert len(rows["items"]) == n and (proof["rows_checked"], proof["rows_failing"], proof["sealed_twice"], proof["union_complete_rows"]) == (n, 0, 0, n), proof
receipt = load(data / S["decision_relpath"])
assert receipt["status"] == "decided" and receipt["decision_id"] == S["decision_id"]
assert SO in receipt["eligible_attempt_ids"] and RUN in receipt["eligible_run_ids"]
print("seal-only preconditions hold at", repo, "rows", n)
PY
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
# Unlike the flight chains, batch-STOP is NOT in this list: its absence was checked above and it is never moved aside.
for f in /home/chao/batch-status.jsonl /home/chao/batch-done; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
QUEUE="$QUEUE" NXT1_MAIN="$REPO" PYTHONPATH="$REPO/src" $PY - <<'PY'
import json
import os
import sys

sys.path.insert(0, os.environ["NXT1_MAIN"] + "/scripts/flights/nx")
import nxt_r1_family as fam

S = fam.sealonly_spec()
rows = json.load(open(os.path.join(os.environ["NXT1_MAIN"], S["complete_rows"]), encoding="utf-8"))["count"]
C = fam.CONTACTS_PER_ROW
steps = [
    {"order": 1, "short": "nxt1seal", "kind": "seal-only",
     "experiment": S["experiment"], "cell": S["cell"],
     "smoke_experiment": None, "smoke_cell": None,
     "campaign_plan": None,
     "run_id": S["run"], "fit_run_id": S["fit_run"], "gen_attempt_id": S["attempt"],
     "smoke_run_id": None, "smoke_attempt_id": None,
     "expected_rows": rows, "contacts_per_row": C, "ceiling_per_row": C, "notool": True,
     "owner": "root-" + S["cell"]},
]
json.dump(steps, open(os.environ["QUEUE"], "w"), indent=1)
PY
echo "queue [nxt1seal: seal-only completion (zero contacts)] written $(date -u +%FT%TZ)" >> $LOG
# Belt and suspenders, as in batch_chain_psv1_sealonly.sh: the resume prelaunch replay gate runs here directly on the seal-only cell before the driver starts, and again in
# the driver's own prelaunch.
echo "resume prelaunch replay gate: checking $(date -u +%FT%TZ)" >> $LOG
GATEOUT=$(bash $SP/resume_prelaunch_gate.sh --repo-root "$REPO" --data-root "$DATA" --experiment "$CELL" --cell "$CELL" 2>&1)
GATERC=$?
printf '%s\n' "$GATEOUT" >> "$LOG"
if [ $GATERC -ne 0 ]; then echo "resume prelaunch replay gate REFUSED (exit $GATERC); abort" >> "$LOG"; exit 5; fi
echo "resume prelaunch replay gate OK $(date -u +%FT%TZ); starting driver" >> "$LOG"
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
