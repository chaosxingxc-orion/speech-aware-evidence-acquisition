#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# P-SV-1 SEAL-ONLY completion (owner decision 197) through the batch driver (owner decisions 22, 77).
# ONE queue of one step:
#   step 1 (psv1seal, kind seal-only): core.flight.cli seal-only on the resume cell -- attempt
#          attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only, resume_from the aborted arm attempt
#          attempt-slurp-native-stage3-psv1-fold-b-generation-v1 (1,080 complete rows, trace 0c1edb20...). The
#          predecessor covers the roster: ZERO model contacts, no lease, no slot, no session attach; it seals the
#          manifest and runs the one official finalize job. NO smoke (a smoke would fly contacts the completion does
#          not need) and no campaign plan (the cell allows check / prepare-supply / seal-only only). P-SV-1 has no A/A
#          cell: the twin branch is the null, inside every row.
# The driver's prelaunch is unchanged: it still requires the resident session idle and healthy, runs the registration
# gate and -- because the cell declares resume_from -- the resume replay gate. The driver then inspects the seal-only
# attempt as an arm: FINALIZED, 1,080 distinct rows, one score job, manifest study_commit = the flight commit.
#
# Preconditions: psv1_sealonly_flip.sh converged the seal-only cell at one HEAD and wrote
# /home/chao/psv1seal-flight-commit.txt; the resident session is serving-slurp-native-candidate-five-train-a-np4-v1;
# no other batch is running; the predecessor attempt directory is untouched.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=$SAEA_DATA_ROOT
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-psv1seal.out
QUEUE=/home/chao/batch-queue.json
COMMIT=$(cat /home/chao/psv1seal-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
/home/chao/.venvs/speechrl/bin/python -B - "$REPO" "$DATA" <<'PY' >> $LOG 2>&1 || { echo "seal-only precondition refused; abort" >> $LOG; exit 6; }
import hashlib, json, sys
from pathlib import Path
repo, data = map(Path, sys.argv[1:3])
RUN = "SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1"
PRED = "attempt-slurp-native-stage3-psv1-fold-b-generation-v1"
PIN = "0c1edb20c37756ec8567fbba8edc56d8ff24ce3ea32b94bccad8c3667285d20a"
SO = "attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only"
FSO = "attempt-slurp-native-stage3-psv1-fold-b-fit-v1-seal-only"
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
cell = load(repo / "configs/experiment/slurp-native-stage3-psv1-fold-b-v1-resume.json")["cells"][0]
assert cell["run_id"] == RUN and cell["readiness"]["state"] == "ready", cell["readiness"]["state"]
assert cell["attempt_id"] == SO, cell["attempt_id"]
assert "seal-only" in cell["allowed_execution_stages"] and "campaign" not in cell["allowed_execution_stages"]
assert cell["resume_from"] == {"attempt_id": PRED, "trace_sha256": PIN}, "resume_from is not the registered predecessor"
assert sha(data / f"runs/{RUN}/{PRED}/{RUN}.trace.jsonl") == PIN, "the predecessor trace moved"
assert load(data / f"attempts/{RUN}/{PRED}.json")["state"] == "ABORTED", "the predecessor attempt is not ABORTED"
for path in (f"runs/{RUN}/{SO}", f"attempts/{RUN}/{SO}.json", f"prepared/SAEA-SLURP-STAGE3-PSV1-FOLD-B-FIT-V1/{FSO}"):
    assert not (data / path).exists(), f"{path} already exists"
proof = load(repo / "docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1-resume-v1/generation-plan-registered-v1.json")["resume_replay_proof"]
assert (proof["rows_checked"], proof["rows_failing"], proof["sealed_twice"]) == (1080, 0, 0), proof
receipt = load(data / "coordination/slurp-stage3-psv1-fold-b-v1/root-admission-sealonly-v1.json")
assert receipt["status"] == "decided" and receipt["decision_id"] == "slurp-stage3-psv1-fold-b-sealonly-admission-v1"
assert SO in receipt["eligible_attempt_ids"] and RUN in receipt["eligible_run_ids"]
print("seal-only preconditions hold at", repo)
PY
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
QUEUE="$QUEUE" /home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
import os
steps = [
    {"order": 1, "short": "psv1seal", "kind": "seal-only",
     "experiment": "slurp-native-stage3-psv1-fold-b-v1-resume",
     "cell": "slurp-native-stage3-psv1-fold-b-v1-resume",
     "smoke_experiment": None, "smoke_cell": None,
     "campaign_plan": None,
     "run_id": "SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-PSV1-FOLD-B-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only",
     "smoke_run_id": None, "smoke_attempt_id": None,
     "expected_rows": 1080, "contacts_per_row": 8, "ceiling_per_row": 15, "notool": True,
     "owner": "root-slurp-native-stage3-psv1-fold-b-v1-resume"},
]
json.dump(steps, open(os.environ["QUEUE"], "w"), indent=1)
PY
echo "queue [psv1seal: seal-only completion (zero contacts)] written $(date -u +%FT%TZ)" >> $LOG
# Belt and suspenders, as in batch_chain_e4_sealonly.sh: the resume prelaunch replay gate runs here directly on the
# seal-only cell before the driver starts, and again in the driver's own prelaunch.
echo "resume prelaunch replay gate: checking $(date -u +%FT%TZ)" >> $LOG
GATEOUT=$(bash $SP/resume_prelaunch_gate.sh --repo-root "$REPO" --data-root "$DATA" \
  --experiment slurp-native-stage3-psv1-fold-b-v1-resume \
  --cell slurp-native-stage3-psv1-fold-b-v1-resume 2>&1)
GATERC=$?
printf '%s\n' "$GATEOUT" >> "$LOG"
if [ $GATERC -ne 0 ]; then echo "resume prelaunch replay gate REFUSED (exit $GATERC); abort" >> "$LOG"; exit 5; fi
echo "resume prelaunch replay gate OK $(date -u +%FT%TZ); starting driver" >> "$LOG"
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
