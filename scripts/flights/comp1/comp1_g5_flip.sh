#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Owner decision 160: flip the COMP-1 family (smoke, the SHARED in-chain A/A, arm) and the G5 family
# (smoke, arm -- NEVER G5's superseded A/A) to ready on master, model-free, converged at ONE HEAD, which
# becomes the flight commit of the one combined chain (batch_chain_comp1_g5.sh).
#
# Root runs this ONLY after, in order:
#   1. the coordinator has replaced COMP-1's expected_effect_pp placeholder with the number composed from
#      the AGREE and KPROBE reads in BOTH places (registered-facts-v1.json and the preregistration fence;
#      decisions 139 and 152) -- comp1_flip.sh refuses while the placeholder stands;
#   2. the branch carrying decision 160's wiring is merged to master;
#   3. root has countersigned COMP-1's seven DRAFT rows and G5's five live DRAFT rows (the arm, the smoke,
#      their FIT identities, and SAEA-SLURP-G5-REVIEWER-INSTRUCTION-TOKEN-MEASUREMENT-V1) -- G5's own A/A
#      pair is superseded unflown and is never countersigned for flight;
#   4. root has minted BOTH receipts: scripts/flights/comp1/comp1_mint_receipt.py (six eligible ids) and
#      scripts/flights/g5/g5_mint_receipt.py --drop-aa (four eligible ids).
# --allow-output-change is never passed: every cell mints its own first-phase supply (item E16), and the
# shared A/A's, the G5 arm's and both smokes' plan-supply digests are checked by the re-pin tool as
# registered (the A/A's must again be ba5e1faa...).
#
# Sequence (the agree_flip_all.sh shape, one family after the other): COMP-1's three cycles through its
# own comp1_flip.sh, then G5's smoke and arm cycles through repin_loop_generic.sh, then a CONVERGENCE
# pass: all five cycles re-run until one whole pass commits nothing, because a later flip rewrites shared
# files (the exposure ledger) after an earlier cell reported "satisfied". Only then is HEAD recorded.
# Untracked files count as dirt for core.flight.cli check.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
CP=$MAIN/scripts/flights/comp1
G5=$MAIN/scripts/flights/g5
C1RD=docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1
G5RD=docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1
PY=/home/chao/.venvs/speechrl/bin/python
cd "$MAIN" || exit 1

# The shared mode must be what master carries, and G5's receipt must have been minted without its A/A.
$PY -B - "$MAIN" "$DATA" <<'PY' || exit 6
import json, sys
main, data = sys.argv[1:3]
def load(path):
    return json.load(open(path, encoding="utf-8"))
proof = load(f"{main}/docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/shared-aa-proof-v1.json")
problems = []
if proof.get("verdict") != "IDENTICAL":
    problems.append(f"the shared A/A proof's verdict is {proof.get('verdict')!r}, not IDENTICAL")
g5_plan = [c["cell"] for c in load(f"{main}/configs/campaign/slurp-native-stage3-g5-fold-a-v1.json")["cells"]]
if g5_plan != ["slurp-native-stage3-g5-fold-a-v1"]:
    problems.append(f"the G5 campaign plan is {g5_plan}, not the arm alone")
comp1_plan = [c["cell"] for c in load(f"{main}/configs/campaign/slurp-native-stage3-comp1-fold-a-v1.json")["cells"]]
if comp1_plan != ["slurp-native-stage3-comp1-aa-fold-a-v1", "slurp-native-stage3-comp1-fold-a-v1"]:
    problems.append(f"the COMP-1 campaign plan is {comp1_plan}, not [the shared A/A, the COMP-1 arm]")
facts = load(f"{main}/docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1/registered-facts-v1.json")
replicate = facts["stage3_measurement"]["SAEA-SLURP-STAGE3-G5-FOLD-A-V1"]["replicate_run_id"]
if replicate != "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1":
    problems.append(f"the G5 arm's replicate_run_id is {replicate!r}")
try:
    receipt = load(f"{data}/coordination/slurp-stage3-g5-fold-a-v1/root-admission-v1.json")
except FileNotFoundError:
    receipt = None
    problems.append("the G5 receipt is not minted (scripts/flights/g5/g5_mint_receipt.py --drop-aa)")
if receipt is not None and "SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1" in receipt.get("eligible_run_ids", []):
    problems.append("the G5 receipt lists the superseded A/A as eligible: it was not minted with --drop-aa")
for problem in problems:
    print("refusing to flip (owner decision 160):", problem)
sys.exit(1 if problems else 0)
PY

# 1. COMP-1: the placeholder refusal and its three cycles (smoke, the shared A/A, arm).
bash "$CP/comp1_flip.sh" || exit $?

# 2. G5: the smoke and the arm; the superseded A/A is never re-pinned, flipped or flown.
for K in smoke arm; do
cat > /home/chao/g5-$K-commit.txt <<M
research: flip G5 ($K) to ready (the Reviewer-instruction repair -- the two sentences ordering the task-contract tool retired as item E25 deleted from the Reviewer instruction, nothing added, -51 prompt tokens per Reviewer contact -- read on no harm at the SHARED in-chain A/A SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 flown in the same chain (owner decision 160; G5's own A/A pair superseded unflown); owner decisions 127, 135, 138, 153 and 160; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-g5-fold-a-admission-v1 minted with --drop-aa)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $G5/g5_repin_smoke.sh $G5RD slurp-native-stage3-g5-fold-a-smoke-4-v1 smoke-generation /home/chao/g5-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $G5/g5_repin_arm.sh   $G5RD slurp-native-stage3-g5-fold-a-v1          generation       /home/chao/g5-arm-commit.txt   || exit $?

# 3. Convergence at ONE HEAD: every cycle re-run until a whole pass commits nothing.
CYCLES=(
  "$CP/comp1_repin_smoke.sh $C1RD slurp-native-stage3-comp1-fold-a-smoke-4-v1 smoke-generation /home/chao/comp1-smoke-commit.txt"
  "$CP/comp1_repin_aa.sh $C1RD slurp-native-stage3-comp1-aa-fold-a-v1 aa-generation /home/chao/comp1-aa-commit.txt"
  "$CP/comp1_repin_arm.sh $C1RD slurp-native-stage3-comp1-fold-a-v1 generation /home/chao/comp1-arm-commit.txt"
  "$G5/g5_repin_smoke.sh $G5RD slurp-native-stage3-g5-fold-a-smoke-4-v1 smoke-generation /home/chao/g5-smoke-commit.txt"
  "$G5/g5_repin_arm.sh $G5RD slurp-native-stage3-g5-fold-a-v1 generation /home/chao/g5-arm-commit.txt"
)
CONVERGED=""
for pass in 1 2 3; do
  BEFORE=$(git rev-parse HEAD)
  for cycle in "${CYCLES[@]}"; do
    # shellcheck disable=SC2086
    bash $SP/repin_loop_generic.sh $cycle || exit $?
  done
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after three passes"; exit 5; }
echo "$CONVERGED" > /home/chao/comp1g5-flight-commit.txt
echo "flight commit $CONVERGED (COMP-1 smoke / shared A/A / arm and G5 smoke / arm all ready at it)"
