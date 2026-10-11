#!/bin/bash
# Decisions 77 / 187: fly the loop iteration cells on the SLURP np4 geometry (session serving-slurp-native-candidate-five-train-a-np4-v1)
# through the batch driver. DRAFT / HELD: NOT executed by the loop driver; the coordinator or owner starts SAEA-Batch-Driver from PowerShell.
#   TFRL_ITER=1 bash scripts/flights/tfrl/batch_chain_tfrl_i1.sh column      # the four-row smoke, then the 1,080-row supply column
#   TFRL_ITER=1 bash scripts/flights/tfrl/batch_chain_tfrl_i1.sh proposers   # the typed proposer cell, then the ACE reflector cell (text-only)
#   TFRL_ONLY=ace TFRL_ITER=1 bash scripts/flights/tfrl/batch_chain_tfrl_i1.sh proposers   # queue only the reflector (typed already flown and sealed); typed|ace, default both
# The column's ceiling_per_row is the iteration's program ceiling (c4 with the typed arm empty, c5 with typ or par, c6 with both): read
# from the cell's registered facts, never hard-coded. Preconditions: the cells flipped in one converged loop (tfrl_i1_flip.sh wrote
# /home/chao/tfrl-i<n>-<which>-flight-commit.txt), the resident session is the np4 one above, no other batch is running (one experiment in
# flight), and the driver's registration gate (scripts/checks/flight_registration_check.py) refuses a step whose rows are not countersigned.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
ITER=${TFRL_ITER:-1}
WHICH=${1:-column}
SHORT=tfrl-i$ITER
ONLY=${TFRL_ONLY:-}
case "$ONLY" in ""|typed|ace) ;; *) echo "TFRL_ONLY must be typed or ace" >&2; exit 2 ;; esac
[ -z "$ONLY" ] || [ "$WHICH" = proposers ] || { echo "TFRL_ONLY applies to the proposers mode only" >&2; exit 2; }
LOG=/home/chao/batch-chain-$SHORT-$WHICH.out
COMMIT=$(cat /home/chao/$SHORT-$WHICH-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION which $WHICH only ${ONLY:-both}" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
TFRL_ITER=$ITER TFRL_WHICH=$WHICH TFRL_SHORT=$SHORT TFRL_ONLY=$ONLY /home/chao/.venvs/speechrl/bin/python "$MAIN/scripts/flights/tfrl/tfrl_i1_queue.py" /home/chao/batch-queue.json || { echo "queue build failed" >> $LOG; exit 3; }
echo "queue [$SHORT $WHICH] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
