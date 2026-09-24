#!/bin/bash
# Decision 77 and the owner directive of 2026-09-24 (training-free RL gains come from rolling out
# VARIATIONS of prompts, data and content construction over an optimisation space, scored per
# variant): fly the VAR-1 construction-variant family on the SLURP serving geometry through the
# batch driver, in SIX steps, one experiment in flight at a time.
#
#   1. VAR1-PLAN      -- the COMPARATOR: the locked v2.0 plan re-pointed at R01C, 625 rows, NO
#                        SMOKE (it is the locked plan's own sealed form; a request-identical form
#                        already flown on TRAIN and DEV raises no structural question a four-row
#                        flight would answer). A step without a smoke sets smoke_experiment and
#                        smoke_cell to None, exactly as batch_chain_cell1.sh does.
#   2. VAR1-PLANR     -- the roster's OWN NULL: the request-identical second pass of step 1. No
#                        smoke, for the same reason and for cell B6's own why_no_smoke rule. Its
#                        margin table is read and SEALED before any variant contrast is read.
#   3. VAR1-EX-K10    -- exemplars k 20 -> 10 (coverage 10/10/10). No smoke: no contract byte moves.
#   4. VAR1-EX-K30    -- exemplars k 20 -> 30 (coverage 30/30/30). No smoke, same reason.
#   5. VAR1-EX-DIV    -- exemplar coverage c 20 -> 4 at k 20. No smoke, same reason.
#   6. VAR1-PER-K16C5 -- its own FOUR-ROW SMOKE, then the 625-row arm. This is the only VAR-1 form
#                        whose CONTRACT SHAPE changes (five Perception candidates instead of three,
#                        sixteen intent cards instead of eight), so it is the only one that needs a
#                        four-row form proof, and the driver flies that smoke before the arm.
#
# The driver enforces both orderings: one step at a time, smoke before arm inside a step. No two
# variants ever fly together, so a failure in one never contaminates another's contacts.
#
# ceiling_per_row 11 is the locked plan's OWN per-row ceiling (configs/policy/
# phase-native-candidates-review-revise-v1.json max_contacts 11, resolved from the unchanged role
# graph perception 1 / solver 1 / reviewer 3 / planner 1 with max_revisions 1 as 1 + 2 x (3+1+1));
# contacts_per_row 4 is the REALISED figure cell PLAN measured on TRAIN Fold A (4.0963) and cell
# B6's plan arm on DEV-2000-ADDED (4.071), and is informational. No VAR-1 knob adds a contact:
# every one of them changes how much text an already-scheduled request carries. The smoke's own
# expected row count is hardcoded at 4 inside batch_driver.sh.
#
# Before this runs: the flight lock must be clear. An aborted campaign leaves locks/flight.lock
# behind and the next launch refuses on it.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-var1.out
COMMIT=$(cat /home/chao/var1-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
def step(order, short, stem, smoke=False):
    cell = "slurp-native-stage3-var1-%s-v1" % stem
    run = "SAEA-SLURP-STAGE3-VAR1-%s-V1" % stem.upper().replace("-R01C", "-R01C")
    return {
        "order": order, "short": short, "kind": "cell",
        "experiment": cell,
        "cell": cell,
        "smoke_experiment": "slurp-native-stage3-var1-smoke-4-v1" if smoke else None,
        "smoke_cell": "slurp-native-stage3-var1-smoke-4-v1" if smoke else None,
        "campaign_plan": "configs/campaign/%s.json" % cell,
        "run_id": run,
        "fit_run_id": run[:-3] + "-FIT-V1",
        "gen_attempt_id": "attempt-%s-generation" % cell,
        "smoke_run_id": "SAEA-SLURP-STAGE3-VAR1-SMOKE-4-V1" if smoke else None,
        "smoke_attempt_id": (
            "attempt-slurp-native-stage3-var1-smoke-4-v1-generation" if smoke else None
        ),
        "expected_rows": 625, "contacts_per_row": 4, "ceiling_per_row": 11, "notool": True,
        "owner": "root-%s" % cell,
    }

steps = [
    step(1, "var1plan", "plan-r01c"),
    step(2, "var1planr", "planr-r01c"),
    step(3, "var1exk10", "ex-k10-r01c"),
    step(4, "var1exk30", "ex-k30-r01c"),
    step(5, "var1exdiv", "ex-div-r01c"),
    step(6, "var1perk16c5", "per-k16c5-r01c", smoke=True),
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [var1plan, var1planr, var1exk10, var1exk30, var1exdiv, var1perk16c5] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
