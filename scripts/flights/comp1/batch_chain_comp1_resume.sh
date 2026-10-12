#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# VARIANT 1 of the COMP-1 recovery: fly the RESUME-RECOVERY of the aborted COMP-1 arm, then G5, on the SLURP np4
# geometry through the batch driver (owner decisions 22, 77, 160). ONE queue of two steps:
#   step 1 (comp1res, kind resume): 2026-09-29, resume attempt 3: the FOUR-ROW DRY RUN of owner decision 181 is the
#          step's smoke (SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME3-SMOKE-4-V1, fresh run / attempt / FIT ids; the driver
#          stops before the resume opens unless it passes its structural check), then the single-cell campaign plan
#          configs/campaign/slurp-native-stage3-comp1-fold-a-v1-resume.json -- the resume cell only. The shared A/A
#          SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 is FINALIZED and scored in the aborted chain and is NEVER re-flown.
#          The attempt keeps 471 COMPLETE rows under I7r custody and flies 609; the merged manifest is 1,080 rows.
#   step 2 (g5): exactly as batch_chain_comp1_g5.sh had it -- the G5 four-row smoke, then G5's campaign plan [the G5
#          arm]. G5 never started in the aborted chain (no runs/ or attempts/ directory under its run ids).
# The driver inspects each step's last cell: the resume attempt (1,080 merged rows; the manifest's study_commit is
# the new flight commit), then the G5 arm.
#
# Preconditions: comp1_resume_flip.sh converged the resume cell and G5's smoke and arm at one HEAD and wrote
# /home/chao/comp1res-flight-commit.txt; the resident session is serving-slurp-native-candidate-five-train-a-np4-v1;
# no other batch is running; the predecessor attempt directory is untouched.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=$SAEA_DATA_ROOT
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-comp1res.out
QUEUE=/home/chao/batch-queue.json
COMMIT=$(cat /home/chao/comp1res-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
/home/chao/.venvs/speechrl/bin/python -B - "$REPO" "$DATA" <<'PY' >> $LOG 2>&1 || { echo "resume precondition refused; abort" >> $LOG; exit 6; }
import hashlib, json, sys
from pathlib import Path
repo, data = map(Path, sys.argv[1:3])
RUN = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
TRACE = "029a2dbbd62bc8752ff9e7d6a53dfee0cb49872f48b11267e49c4022c9561997"
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def cells(name):
    return [c["cell"] for c in load(repo / f"configs/campaign/{name}.json")["cells"]]
assert cells("slurp-native-stage3-comp1-fold-a-v1-resume") == ["slurp-native-stage3-comp1-fold-a-v1-resume"]
assert cells("slurp-native-stage3-g5-fold-a-v1") == ["slurp-native-stage3-g5-fold-a-v1"]
cell = load(repo / "configs/experiment/slurp-native-stage3-comp1-fold-a-v1-resume.json")["cells"][0]
assert cell["run_id"] == RUN and cell["readiness"]["state"] == "ready", cell["readiness"]["state"]
assert cell["resume_from"] == {"attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-generation-v1", "trace_sha256": TRACE}
trace = data / f"runs/{RUN}/attempt-slurp-native-stage3-comp1-fold-a-generation-v1/{RUN}.trace.jsonl"
digest = hashlib.sha256()
with trace.open("rb") as handle:
    for block in iter(lambda: handle.read(1 << 20), b""):
        digest.update(block)
assert digest.hexdigest() == TRACE, "the predecessor trace moved"
assert not (data / f"runs/{RUN}/attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3").exists(), "resume attempt 3 already exists"
assert not (data / f"prepared/SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1/attempt-slurp-native-stage3-comp1-fold-a-fit-v1-resume-3").exists(), "the attempt-3 FIT identity root already exists"
for dry in ("runs/SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME3-SMOKE-4-V1", "attempts/SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME3-SMOKE-4-V1",
            "prepared/SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME3-SMOKE-4-FIT-V1"):
    assert not (data / dry).exists(), f"the dry run already started: {dry}"
dcell = load(repo / "configs/experiment/slurp-native-stage3-comp1-fold-a-resume3-smoke-4-v1.json")["cells"][0]
assert dcell["readiness"]["state"] == "ready", dcell["readiness"]["state"]
assert cell["attempt_id"] == "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3", cell["attempt_id"]
assert load(data / "coordination/slurp-stage3-comp1-fold-a-v1/resume-byte-identity-proof-v1.json")["verdict"] == "PASS"
assert load(data / "attempts/SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1/attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1.json")["state"] == "FINALIZED"
facts = load(repo / "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1/registered-facts-v1.json")
assert facts["stage3_measurement"]["SAEA-SLURP-STAGE3-G5-FOLD-A-V1"]["replicate_run_id"] == "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1"
for g5 in ("SAEA-SLURP-STAGE3-G5-FOLD-A-V1", "SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-V1"):
    assert not (data / "runs" / g5).exists() and not (data / "attempts" / g5).exists(), f"{g5} already started"
print("resume preconditions hold at", repo)
PY
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
QUEUE="$QUEUE" /home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
import os
steps = [
    {"order": 1, "short": "comp1res", "kind": "resume",
     "experiment": "slurp-native-stage3-comp1-fold-a-v1-resume",
     "cell": "slurp-native-stage3-comp1-fold-a-v1-resume",
     "smoke_experiment": "slurp-native-stage3-comp1-fold-a-resume3-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-comp1-fold-a-resume3-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-comp1-fold-a-v1-resume.json",
     "run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3",
     "smoke_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME3-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3-smoke",
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
echo "queue [comp1res: the four-row dry run (owner decision 181) as the smoke, then resume attempt 3 (the A/A never re-flown); g5: smoke, then the G5 arm] written; starting driver $(date -u +%FT%TZ)" >> $LOG
# Coordinator, after the COMP-1 resume attempt 3 seal abort: EVERY resume launch first passes the
# OFFLINE full-trace replay check, run here directly (belt) as well as by the driver's own
# per-step prelaunch (suspenders, scripts/flights/batch/batch_driver.sh resume_gate_run) -- this
# call fails the chain fast, before any lease or smoke overhead, on the resume cell specifically.
echo "resume prelaunch replay gate: checking $(date -u +%FT%TZ)" >> $LOG
GATEOUT=$(bash $SP/resume_prelaunch_gate.sh --repo-root "$REPO" --data-root "$DATA" \
  --experiment slurp-native-stage3-comp1-fold-a-v1-resume \
  --cell slurp-native-stage3-comp1-fold-a-v1-resume 2>&1)
GATERC=$?
printf '%s\n' "$GATEOUT" >> "$LOG"
if [ $GATERC -ne 0 ]; then echo "resume prelaunch replay gate REFUSED (exit $GATERC); abort" >> "$LOG"; exit 5; fi
echo "resume prelaunch replay gate OK $(date -u +%FT%TZ)" >> "$LOG"
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
