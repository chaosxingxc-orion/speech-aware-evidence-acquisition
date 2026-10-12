#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# VARIANT 2 of the COMP-1 recovery: flip the -REC recovery re-registration (smoke, arm) and G5's smoke and arm to
# ready on master, model-free, converged at ONE HEAD, which becomes the flight commit of batch_chain_comp1_rec.sh.
#
# Root runs this ONLY after, in order:
#   1. the OWNER has ruled for the -REC re-registration (a full 1,080-row re-fly under a fresh run id);
#   2. the branch carrying the fix (fable/comp1rec, a451f942) and this registration (fable/comp1res) is merged;
#   3. root has countersigned the four -REC DRAFT rows, marked the aborted run's two rows
#      (SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1 and its FIT row) consumed = yes, and marked the resume clauses and the
#      resume proof row superseded unflown;
#   4. root has minted $DATA/coordination/slurp-stage3-comp1-fold-a-v1/root-admission-rec-v1.json (decision id
#      slurp-stage3-comp1-fold-a-rec-admission-v1, status decided, eligible_run_ids naming the four -REC run ids).
# --allow-output-change is never passed: each -REC cell INHERITS its parent's prepared supply pin, and the re-pin
# rebuilds it under the -REC run id and ASSERTS the output unchanged (arm ce68bebc..., smoke 1d55ea73...).
# G5 never started in the aborted chain; it is re-converged here unchanged.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
CP=$MAIN/scripts/flights/comp1
G5=$MAIN/scripts/flights/g5
XRD=docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-rec-v1
G5RD=docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1
PY=/home/chao/.venvs/speechrl/bin/python
cd "$MAIN" || exit 1

$PY -B - "$MAIN" "$DATA" <<'PY' || exit 6
import json, sys
from pathlib import Path
main, data = map(Path, sys.argv[1:3])
REC = ["SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-V1", "SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-FIT-V1",
       "SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-SMOKE-4-V1", "SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-SMOKE-4-FIT-V1"]
problems = []
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
receipt_path = data / "coordination/slurp-stage3-comp1-fold-a-v1/root-admission-rec-v1.json"
if not receipt_path.is_file():
    problems.append("the -REC decision receipt root-admission-rec-v1.json is not minted")
else:
    eligible = set(load(receipt_path).get("eligible_run_ids", []))
    missing = [run for run in REC if run not in eligible]
    if missing:
        problems.append(f"the -REC receipt does not list {missing} as eligible")
ledger = (main / "docs/exposure-ledger.md").read_text(encoding="utf-8").split("\n")
def consumed(run):
    rows = [ln for ln in ledger if ln.startswith("|") and f"| {run} |" in ln]
    return None if len(rows) != 1 else rows[0].split("|")[9].replace("*", "").strip().lower().split(";")[0].split("(")[0].strip()
for run in ("SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1", "SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1"):
    if consumed(run) != "yes":
        problems.append(f"{run}: the aborted run's row must read consumed = yes before a -REC flight (B5e precedent)")
for run in REC:
    if consumed(run) != "no":
        problems.append(f"{run}: needs exactly one row reading consumed = no")
aa = load(data / "attempts/SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1/attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1.json")
if aa.get("state") != "FINALIZED":
    problems.append(f"the shared A/A attempt is {aa.get('state')!r}, not FINALIZED")
for run in REC[::2] + ["SAEA-SLURP-STAGE3-G5-FOLD-A-V1", "SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-V1"]:
    if (data / "runs" / run).exists() or (data / "attempts" / run).exists():
        problems.append(f"{run} has a run or attempt directory already -- stop and re-plan")
for problem in problems:
    print("refusing to flip the COMP-1 -REC:", problem)
sys.exit(1 if problems else 0)
PY

for K in smoke arm; do
cat > /home/chao/comp1-rec-$K-commit.txt <<M
research: flip the COMP-1 -REC recovery re-registration ($K) to ready (COMP-1's ONE recovery re-registration after the 2026-09-28 citation-contract abort of SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1: a full 1,080-row re-fly under a fresh run id, the parent's bytes except identities and the recovery note, its prepared supply rebuilt with the output unchanged; the shared in-chain A/A never re-flown; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-comp1-fold-a-rec-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
cat > /home/chao/g5-$K-commit.txt <<M
research: re-converge G5 ($K) at the COMP-1 -REC flight commit (G5 never started in the aborted chain; its registration, receipt and replicate SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 are unchanged; owner decisions 127, 135, 138, 153 and 160; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-g5-fold-a-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done

CYCLES=(
  "$CP/comp1_repin_rec_smoke.sh $XRD slurp-native-stage3-comp1-fold-a-rec-smoke-4-v1 smoke-generation /home/chao/comp1-rec-smoke-commit.txt"
  "$CP/comp1_repin_rec_arm.sh $XRD slurp-native-stage3-comp1-fold-a-rec-v1 generation /home/chao/comp1-rec-arm-commit.txt"
  "$G5/g5_repin_smoke.sh $G5RD slurp-native-stage3-g5-fold-a-smoke-4-v1 smoke-generation /home/chao/g5-smoke-commit.txt"
  "$G5/g5_repin_arm.sh $G5RD slurp-native-stage3-g5-fold-a-v1 generation /home/chao/g5-arm-commit.txt"
)
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  for cycle in "${CYCLES[@]}"; do
    # shellcheck disable=SC2086
    bash $SP/repin_loop_generic.sh $cycle || exit $?
  done
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/comp1rec-flight-commit.txt
echo "flight commit $CONVERGED (the COMP-1 -REC smoke / arm and G5 smoke / arm all ready at it)"
