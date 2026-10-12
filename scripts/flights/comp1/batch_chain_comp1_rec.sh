#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# VARIANT 2 of the COMP-1 recovery: fly the -REC recovery re-registration of the aborted COMP-1 arm, then G5, on the
# SLURP np4 geometry through the batch driver (owner decisions 77, 160). ONE queue of two steps:
#   step 1 (comp1rec, kind cell): the -REC four-row form smoke (the fixed tree's dry run), then the single-cell
#          campaign plan configs/campaign/slurp-native-stage3-comp1-fold-a-rec-v1.json -- the -REC arm only, all
#          1,080 rows. The shared A/A SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 is FINALIZED and scored in the aborted
#          chain and is NEVER re-flown.
#   step 2 (g5): exactly as batch_chain_comp1_g5.sh had it -- the G5 four-row smoke, then G5's campaign plan [the G5
#          arm]. G5 never started in the aborted chain.
#
# Preconditions: comp1_rec_flip.sh converged the -REC smoke / arm and G5's smoke / arm at one HEAD and wrote
# /home/chao/comp1rec-flight-commit.txt; the resident session is serving-slurp-native-candidate-five-train-a-np4-v1;
# no other batch is running.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=$SAEA_DATA_ROOT
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-comp1rec.out
QUEUE=/home/chao/batch-queue.json
COMMIT=$(cat /home/chao/comp1rec-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
/home/chao/.venvs/speechrl/bin/python -B - "$REPO" "$DATA" <<'PY' >> $LOG 2>&1 || { echo "-REC precondition refused; abort" >> $LOG; exit 6; }
import json, sys
from pathlib import Path
repo, data = map(Path, sys.argv[1:3])
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def cells(name):
    return [c["cell"] for c in load(repo / f"configs/campaign/{name}.json")["cells"]]
assert cells("slurp-native-stage3-comp1-fold-a-rec-v1") == ["slurp-native-stage3-comp1-fold-a-rec-v1"]
assert cells("slurp-native-stage3-g5-fold-a-v1") == ["slurp-native-stage3-g5-fold-a-v1"]
for name in ("slurp-native-stage3-comp1-fold-a-rec-v1", "slurp-native-stage3-comp1-fold-a-rec-smoke-4-v1"):
    cell = load(repo / f"configs/experiment/{name}.json")["cells"][0]
    assert cell["readiness"]["state"] == "ready" and "resume_from" not in cell, name
facts = load(repo / "docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-rec-v1/registered-facts-v1.json")
block = facts["stage3_measurement"]["SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-V1"]
assert block["expected_effect_pp"] == 3.23 and block["replicate_run_id"] == "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1"
assert load(data / "attempts/SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1/attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1.json")["state"] == "FINALIZED"
g5 = load(repo / "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1/registered-facts-v1.json")
assert g5["stage3_measurement"]["SAEA-SLURP-STAGE3-G5-FOLD-A-V1"]["replicate_run_id"] == "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1"
for run in ("SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-V1", "SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-SMOKE-4-V1",
            "SAEA-SLURP-STAGE3-G5-FOLD-A-V1", "SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-V1"):
    assert not (data / "runs" / run).exists() and not (data / "attempts" / run).exists(), f"{run} already started"
print("-REC preconditions hold at", repo)
PY
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
QUEUE="$QUEUE" /home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
import os
steps = [
    {"order": 1, "short": "comp1rec", "kind": "cell",
     "experiment": "slurp-native-stage3-comp1-fold-a-rec-v1",
     "cell": "slurp-native-stage3-comp1-fold-a-rec-v1",
     "smoke_experiment": "slurp-native-stage3-comp1-fold-a-rec-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-comp1-fold-a-rec-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-comp1-fold-a-rec-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-rec-generation-v1",
     "smoke_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-rec-smoke-4-generation-v1",
     "expected_rows": 1080, "contacts_per_row": 5, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-comp1-fold-a-rec-v1"},
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
echo "queue [comp1rec: -REC smoke, then the -REC arm (the A/A never re-flown); g5: smoke, then the G5 arm] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
