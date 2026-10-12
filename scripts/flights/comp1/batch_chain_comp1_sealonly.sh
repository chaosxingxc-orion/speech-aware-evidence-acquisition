#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# COMP-1 SEAL-ONLY completion (owner decision 189 option A), then G5, on the SLURP np4 geometry through the batch
# driver (owner decisions 22, 77, 160, 175, 181). ONE queue of two steps:
#   step 1 (comp1seal, kind seal-only): core.flight.cli seal-only on the resume cell -- attempt
#          attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only, resume_from [the original aborted
#          attempt (471 complete rows), resume attempt 3 (609 complete rows)]. The union covers the 1,080-row roster:
#          ZERO model contacts, no lease, no slot, no session attach; it seals the merged manifest and runs the one
#          official finalize job. NO smoke (a smoke would fly contacts the completion does not need) and no campaign
#          plan (the cell no longer allows campaign mode; the registration gate runs on --cell). The shared A/A
#          SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 is FINALIZED and never re-flown.
#   step 2 (g5): exactly as batch_chain_comp1_resume.sh had it -- the G5 four-row smoke, then G5's campaign plan.
# The driver's prelaunch is unchanged for step 1: it still requires the resident session idle and healthy (the
# resident SLURP np4 satisfies it, and step 2 needs it anyway), runs the registration gate and -- because the cell
# declares resume_from -- the resume replay gate over BOTH predecessors. The driver then inspects the seal-only
# attempt as an arm: FINALIZED, 1,080 distinct rows, one score job, manifest study_commit = the flight commit.
#
# Preconditions: comp1_sealonly_flip.sh converged the seal-only cell and G5's smoke and arm at one HEAD and wrote
# /home/chao/comp1seal-flight-commit.txt; the resident session is serving-slurp-native-candidate-five-train-a-np4-v1;
# no other batch is running; neither predecessor attempt directory is touched.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=$SAEA_DATA_ROOT
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-comp1seal.out
QUEUE=/home/chao/batch-queue.json
COMMIT=$(cat /home/chao/comp1seal-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
/home/chao/.venvs/speechrl/bin/python -B - "$REPO" "$DATA" <<'PY' >> $LOG 2>&1 || { echo "seal-only precondition refused; abort" >> $LOG; exit 6; }
import hashlib, json, sys
from pathlib import Path
repo, data = map(Path, sys.argv[1:3])
RUN = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
SO = "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only"
FSO = "attempt-slurp-native-stage3-comp1-fold-a-fit-v1-seal-only"
PRED = [
    ("attempt-slurp-native-stage3-comp1-fold-a-generation-v1", "029a2dbbd62bc8752ff9e7d6a53dfee0cb49872f48b11267e49c4022c9561997"),
    ("attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3", "87be5cefcaa395ad58a010b6d79986c5c79981c8cebe0279029bd22f7343df26"),
]
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
cell = load(repo / "configs/experiment/slurp-native-stage3-comp1-fold-a-v1-resume.json")["cells"][0]
assert cell["run_id"] == RUN and cell["readiness"]["state"] == "ready", cell["readiness"]["state"]
assert cell["attempt_id"] == SO, cell["attempt_id"]
assert "seal-only" in cell["allowed_execution_stages"] and "campaign" not in cell["allowed_execution_stages"]
assert cell["resume_from"] == [{"attempt_id": a, "trace_sha256": t} for a, t in PRED], "resume_from is not the registered list"
for attempt, pin in PRED:
    assert sha(data / f"runs/{RUN}/{attempt}/{RUN}.trace.jsonl") == pin, f"the predecessor trace of {attempt} moved"
assert load(data / f"attempts/{RUN}/{PRED[1][0]}.json")["state"] == "ABORTED", "resume attempt 3 is not ABORTED"
for path in (f"runs/{RUN}/{SO}", f"attempts/{RUN}/{SO}.json", f"prepared/SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1/{FSO}"):
    assert not (data / path).exists(), f"{path} already exists"
proof = load(repo / "docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1/generation-plan-registered-v1.json")["resume_replay_proof"]
assert (proof["rows_checked"], proof["rows_failing"], proof["sealed_twice"]) == (1080, 0, 0), proof
receipt = load(data / "coordination/slurp-stage3-comp1-fold-a-v1/root-admission-sealonly-v1.json")
assert receipt["status"] == "decided" and receipt["decision_id"] == "slurp-stage3-comp1-fold-a-sealonly-admission-v1"
assert SO in receipt["eligible_attempt_ids"] and RUN in receipt["eligible_run_ids"]
assert load(data / "attempts/SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1/attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1.json")["state"] == "FINALIZED"
facts = load(repo / "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1/registered-facts-v1.json")
assert facts["stage3_measurement"]["SAEA-SLURP-STAGE3-G5-FOLD-A-V1"]["replicate_run_id"] == "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1"
for g5 in ("SAEA-SLURP-STAGE3-G5-FOLD-A-V1", "SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-V1"):
    assert not (data / "runs" / g5).exists() and not (data / "attempts" / g5).exists(), f"{g5} already started"
print("seal-only preconditions hold at", repo)
PY
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
QUEUE="$QUEUE" /home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
import os
steps = [
    {"order": 1, "short": "comp1seal", "kind": "seal-only",
     "experiment": "slurp-native-stage3-comp1-fold-a-v1-resume",
     "cell": "slurp-native-stage3-comp1-fold-a-v1-resume",
     "smoke_experiment": None, "smoke_cell": None,
     "campaign_plan": None,
     "run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only",
     "smoke_run_id": None, "smoke_attempt_id": None,
     "expected_rows": 1080, "contacts_per_row": 5, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-comp1-fold-a-v1-resume"},
    {"order": 2, "short": "g5", "kind": "cell",
     "experiment": "slurp-native-stage3-g5-fold-a-v1",
     "cell": "slurp-native-stage3-g5-fold-a-v1",
     "smoke_experiment": "slurp-native-stage3-g5-fold-a-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-g5-fold-a-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-g5-fold-a-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-G5-FOLD-A-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-G5-FOLD-A-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-g5-fold-a-generation-v1",
     "smoke_run_id": "SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-g5-fold-a-smoke-4-generation-v1",
     "expected_rows": 1080, "contacts_per_row": 5, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-g5-fold-a-v1"},
]
json.dump(steps, open(os.environ["QUEUE"], "w"), indent=1)
PY
echo "queue [comp1seal: seal-only completion (zero contacts; the A/A never re-flown); g5: smoke, then the G5 arm] written $(date -u +%FT%TZ)" >> $LOG
# Belt and suspenders, as in batch_chain_comp1_resume.sh: the resume prelaunch replay gate runs here directly on the
# seal-only cell (both predecessors) before the driver starts, and again in the driver's own prelaunch.
echo "resume prelaunch replay gate: checking $(date -u +%FT%TZ)" >> $LOG
GATEOUT=$(bash $SP/resume_prelaunch_gate.sh --repo-root "$REPO" --data-root "$DATA" \
  --experiment slurp-native-stage3-comp1-fold-a-v1-resume \
  --cell slurp-native-stage3-comp1-fold-a-v1-resume 2>&1)
GATERC=$?
printf '%s\n' "$GATEOUT" >> "$LOG"
if [ $GATERC -ne 0 ]; then echo "resume prelaunch replay gate REFUSED (exit $GATERC); abort" >> "$LOG"; exit 5; fi
echo "resume prelaunch replay gate OK $(date -u +%FT%TZ); starting driver" >> "$LOG"
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
