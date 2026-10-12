#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip the COMP-1b TEST-SAMPLE milestone (owner decisions 151 and 202) -- MILESTONE-00-PLAN (the comparator) then
# MILESTONE-01 (COMP-1b) -- to ready on master: model-free, two cells converging at ONE HEAD, which becomes the flight
# commit. NO SMOKE: the allowance names no smoke run id. Root runs this ONLY after:
#   0. cell A2 read NOMINATED or better and the coordinator reported the dev-admitted arm to the owner in
#      conversation (the first-contact gate of decision 151; named in the countersignature of the first row);
#   1. a SUCCESSOR allowance names both FIT run ids, and both fragments pin its bytes;
#   2. preparations 2 and 3 of the sample ran, this roster's agreement table was built, and every PENDING pin is real;
#   3. root re-declared expected_effect_pp from the A2 read (registered-facts redeclared_from_a2_read true);
#   4. the five DRAFT rows are countersigned and coordination/slurp-stage3-comp1b-testsample-v1/root-admission-v1.json
#      is minted (scripts/flights/comp1/comp1b_testsample_mint_receipt.py).
# Steps 1-3 are machine-checked below by comp1b_testsample_preflip_check.py; the flip refuses on any refusal.
# --allow-output-change must never be passed. Loop form (repin_loop_generic.sh): sibling flips move hashes.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
/home/chao/.venvs/speechrl/bin/python -B "$MAIN/scripts/flights/comp1/comp1b_testsample_preflip_check.py" \
  --repo-root "$MAIN" --data-root "$DATA" || { echo "milestone flip REFUSED by the preflip gate"; exit 6; }
for K in plan arm; do
cat > /home/chao/comp1bts-$K-commit.txt <<M
research: flip the COMP-1b test-sample milestone ($K) to ready (owner decisions 151 and 202: MILESTONE-00-PLAN = the locked v2.0 plan, MILESTONE-01 = COMP-1b, on SLURP-TEST-SAMPLE-3010-V1, one attempt each, no smoke; intent primary, official SLU-F1 (slurp-slu-official-test) the guard at the fallback null; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-comp1b-testsample-milestone-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
CP=$(dirname "$0")
bash $SP/repin_loop_generic.sh $CP/comp1b_testsample_repin_plan.sh $RD slurp-native-stage3-plan-testsample-milestone00-v1 plan-generation /home/chao/comp1bts-plan-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $CP/comp1b_testsample_repin_arm.sh  $RD slurp-native-stage3-comp1b-testsample-v1          generation      /home/chao/comp1bts-arm-commit.txt  || exit $?
cd "$MAIN" && git rev-parse HEAD > /home/chao/comp1bts-flight-commit.txt
echo "flight commit $(cat /home/chao/comp1bts-flight-commit.txt)"
