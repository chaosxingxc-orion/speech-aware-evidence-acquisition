#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Decisions 77 / 151 / 301 A: fly the SUCCESSOR-3 cell (the Thinking system on SLURP-TEST-SAMPLE-3010-V1, the SLURP lock candidate v3.0) on the Thinking geometry
# (think-budget-np4, session serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1) through the batch driver. ONE step, ONE cell, NO SMOKE, NO TWIN: the
# queue step sets smoke_experiment and smoke_cell to None (batch_driver.sh skips fly_smoke then), because the allowance lists a test-sample smoke as not authorised and
# a smoke under the read id would consume its one attempt. ONE ATTEMPT, EVER: never re-launch after a failure (the gate refuses a second attempt of a read run id).
# contacts_per_row 2 and ceiling_per_row 2 are the program maximum (policy phase-native-module-v1-c2: Perception 1 + Solver 1); the plan ceiling adds the answer-only fallbacks.
# REFUSES (nothing is started) unless: the think-budget session is the RESIDENT one and the Instruct session is not; the signed allowance is pinned and authorised
# (successor3_thinking_preflip_check.py at the flight commit); the Thinking sample promotion receipt exists and is pinned; the packets exposure row is root-countersigned;
# no flight, lease or driver is alive; no attempt exists for either run id. WHILE the Thinking session is resident the idle watchdog MUST be held.
#   bash scripts/flights/nx/batch_chain_successor3_thinking.sh
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
DATA=$SAEA_DATA_ROOT
SHORT=ms3
CELL=slurp-milestone-successor3-thinking-system-v1
RUN=SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1
FIT_RUN=SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-FIT-V1
PACKETS_RUN=SAEA-SLURP-TEST-SAMPLE-3010-THINKING-PACKETS-GPU-V1
PKG=docs/readiness/2026-10-14-slurp-milestone-successor3-thinking-system-v1
RECEIPT=/home/chao/feat-cache/slurp-q4km-packets-thinking-gpu-afdaeff6/TEST-SAMPLE-3010-promotion.json
LOG=/home/chao/batch-chain-$SHORT.out
PY=/home/chao/.venvs/speechrl/bin/python
COMMIT=$(cat /home/chao/$SHORT-flight-commit.txt) || exit 1
THINK_SESSION=serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1
INSTRUCT_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
export BATCH_SESSION=$THINK_SESSION
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION cell $CELL" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh|lease_cli' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
[ -e "$DATA/locks/flight.lock" ] && { echo "flight.lock present; abort" >> $LOG; exit 7; }
S=$DATA/serving/$BATCH_SESSION
if [ ! -f "$S/session.json" ] || [ -f "$S/session-stop.json" ]; then echo "session $BATCH_SESSION is not resident; swap first (serving_swap.sh think-budget-np4); abort" >> $LOG; exit 6; fi
O=$DATA/serving/$INSTRUCT_SESSION
if [ -f "$O/session.json" ] && [ ! -f "$O/session-stop.json" ]; then echo "the Instruct session $INSTRUCT_SESSION is still recorded resident; stop it first; abort" >> $LOG; exit 6; fi
for R in $RUN $FIT_RUN; do
  if [ -d "$DATA/attempts/$R" ] && [ -n "$(ls -A "$DATA/attempts/$R" 2>/dev/null)" ]; then
    echo "$R already has an attempt: ONE attempt, ever; refusing to launch" >> $LOG; exit 8
  fi
done
[ -f "$RECEIPT" ] || { echo "the Thinking sample promotion receipt $RECEIPT is absent; abort" >> $LOG; exit 8; }
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
# The packets exposure row must be root-countersigned (it may already be consumed by now: only its countersignature is checked here).
$PY -B - "$REPO" "$PACKETS_RUN" <<'PY' >> $LOG 2>&1 || { echo "the packets exposure row is absent or not root-countersigned; abort" >> $LOG; exit 11; }
import re, sys
sys.path.insert(0, sys.argv[1] + "/src")
from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables
rows = [r for r in _parse_ledger_tables(open(sys.argv[1] + "/docs/exposure-ledger.md", encoding="utf-8").read()) if r.get("run/experiment id") == sys.argv[2]]
assert len(rows) == 1, f"{len(rows)} packets rows"
text = " ".join(str(v) for v in rows[0].values())
assert not re.search(r"\bdraft\b", text, re.I) and re.search(r"root countersigned", text, re.I), "packets row is a draft or not countersigned"
print("packets row countersigned")
PY
# The flight commit must carry the signed pin, the one-cell plan, the exception and no smoke -- read from the checkout that will fly.
$PY -B "$REPO/scripts/flights/nx/successor3_thinking_preflip_check.py" --repo-root "$REPO" --data-root "$DATA" >> $LOG 2>&1 \
  || { echo "successor-3 preconditions refused at the flight commit; abort" >> $LOG; exit 6; }
$PY -B - "$REPO" "$PKG" <<'PY' >> $LOG 2>&1 || { echo "successor-3 plan refused; abort" >> $LOG; exit 6; }
import json, sys
repo, pkg = sys.argv[1], sys.argv[2]
cell = "slurp-milestone-successor3-thinking-system-v1"
plan = [c["cell"] for c in json.load(open(f"{repo}/configs/campaign/{cell}.json"))["cells"]]
assert plan == [cell], plan
fragment = json.load(open(f"{repo}/configs/experiment/{cell}.json"))
assert fragment["cells"][0]["readiness"]["state"] == "ready", fragment["cells"][0]["readiness"]["state"]
assert fragment["owner_allowance"]["sha256"] != "0" * 64
policy = fragment["failure_policy"]
assert policy.startswith("ONE ATTEMPT, EVER") and "NO recovery re-registration" in policy and "NO resume-recovery" in policy, policy[:80]
block = json.load(open(f"{repo}/{pkg}/registered-facts-v1.json"))["stage3_measurement"]["SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1"]
assert block["measurement_design"] == "cross-flight-no-replicate" and block["owner_ruling_301_a"]["date"] == "2026-10-13" and block["claims_benefit"] is False
declared = block["expected_effect_pp"]
assert isinstance(declared, (int, float)) and not isinstance(declared, bool), f"expected_effect_pp is {declared!r}"
baseline = json.load(open(f"{repo}/configs/baseline/{fragment['cells'][0]['baseline_fragment']}.json"))
assert baseline["speech_packet_promotion_receipt_sha256"] != "0" * 64
print("successor-3 preconditions hold at", repo, "declared", declared)
PY
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
$PY - <<'PY'
import json
steps = [{
    "order": 1, "short": "ms3", "kind": "cell",
    "experiment": "slurp-milestone-successor3-thinking-system-v1",
    "cell": "slurp-milestone-successor3-thinking-system-v1",
    "smoke_experiment": None, "smoke_cell": None, "smoke_run_id": None, "smoke_attempt_id": None,
    "campaign_plan": "configs/campaign/slurp-milestone-successor3-thinking-system-v1.json",
    "run_id": "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1",
    "fit_run_id": "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-FIT-V1",
    "gen_attempt_id": "attempt-slurp-milestone-successor3-thinking-system-generation-v1",
    "expected_rows": 3010, "contacts_per_row": 2, "ceiling_per_row": 2, "notool": True,
    "owner": "root-slurp-milestone-successor3-thinking-system-v1",
}]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [ms3: the one-cell campaign, no smoke] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
