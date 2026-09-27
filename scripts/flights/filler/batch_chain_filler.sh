#!/bin/bash
# Decisions 77 / 162: fly ONE filler chunk on the SLURP np4 serving geometry through the batch driver.
# Mirrors scripts/flights/batch/batch_chain_roll2.sh: ONE step; for chunk 1 the four-row smoke flies
# first (the driver enforces smoke before arm inside a step), every other chunk is arm only -- its form
# is chunk 1's, byte for byte, on other rows.
#
#   bash scripts/flights/filler/batch_chain_filler.sh <k>
#
# Launched by the idle-filler queue (filler_queue.sh), never by hand while a main-line chain is ready.
# The step is NOT typed here: it is read from the flight commit's own
# docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-cKK-v1/queue-step-v1.json (written at registration),
# and its run ids are checked against the chunk's names before the queue file is written.
# ceiling_per_row 19 = 1 + 2 x (1 x 5 + 3 + 1) (the grouped-Solver graph at samples 5, max_revisions 1);
# contacts_per_row 9 is informational (ROLL-2 realised 8.33 on this form).
# Refuses (exit 7) when a batch is running, (exit 6) when a stale batch-flight-repo.txt override exists,
# and never touches serving tasks, the geometry or locks/.
K=${1:?usage: batch_chain_filler.sh <chunk>}
case "$K" in *[!0-9]*) echo "chunk must be a number" >&2; exit 2;; esac
K2=$(printf %02d "$((10#$K))")
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
PY=/home/chao/.venvs/speechrl/bin/python
LOG=/home/chao/batch-chain-filler.out
COMMIT=$(cat /home/chao/filler-flight-commit-c$K2.txt) || { echo "$(date -u +%FT%TZ) c$K2: no flight commit file" >> $LOG; exit 1; }
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) chunk c$K2 commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh|lease_cli' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
if [ -f /home/chao/batch-flight-repo.txt ]; then echo "stale flight-repo override /home/chao/batch-flight-repo.txt present; refuse (archive it)" >> $LOG; exit 6; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
STEP_PATH=docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-c$K2-v1/queue-step-v1.json
git -C "$REPO" show "$COMMIT:$STEP_PATH" > /home/chao/filler-queue-step-c$K2.json || { echo "no queue step at $COMMIT" >> $LOG; exit 2; }
$PY - "$K2" /home/chao/filler-queue-step-c$K2.json <<'PY' || { echo "queue step refused" >> $LOG; exit 2; }
import json, sys
k2, path = sys.argv[1], sys.argv[2]
step = json.load(open(path))
tag = f"FILLER-FOLD-B-C{k2}"
assert step["run_id"] == f"SAEA-SLURP-STAGE3-{tag}-V1", step["run_id"]
assert step["fit_run_id"] == f"SAEA-SLURP-STAGE3-{tag}-FIT-V1", step["fit_run_id"]
assert step["cell"] == step["experiment"] == f"slurp-native-stage3-filler-fold-b-c{k2}-v1", step["cell"]
assert step["campaign_plan"] == f"configs/campaign/slurp-native-stage3-filler-fold-b-c{k2}-v1.json"
assert (step["smoke_cell"] is not None) == (k2 == "01"), "only chunk 01 carries a smoke"
assert step["ceiling_per_row"] == 19 and step["notool"] is True
json.dump([step], open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
echo "queue [filler c$K2] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
RC=$?
echo "driver exit $RC $(date -u +%FT%TZ)" >> $LOG
exit $RC
