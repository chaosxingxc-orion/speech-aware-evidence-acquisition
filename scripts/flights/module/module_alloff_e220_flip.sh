#!/bin/bash
# Flip the Earnings-22 consumption-module ALL-OFF arm (carrier admission gate, design 2b.3; owner decision 196, direction
# 205) -- smoke, then arm -- to ready on master: model-free, two cells converging at ONE HEAD, which becomes the flight
# commit. HELD: decision 187 keeps the GPU on SLURP; root runs this ONLY after the owner reopens Earnings and:
#   1. the three DRAFT exposure rows are countersigned (arm, smoke, READ; the direct baselines declare no fit identity);
#   2. coordination/earnings22-native-stage3-module-alloff-v1/root-admission-v1.json is minted
#      (scripts/flights/module/module_alloff_mint_receipt.py --carrier e22);
#   3. python -B scripts/analysis/module_equivalence_proof.py --at e220 reports ok.
# --allow-output-change must never be passed. Loop form: repin_loop_generic.sh re-runs each cycle until convergence.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-10-11-earnings22-module-alloff-v1
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
for K in smoke arm; do
cat > /home/chao/module-alloff-e220-$K-commit.txt <<M
research: flip the Earnings-22 consumption-module all-off arm ($K) to ready (carrier admission gate, design 2b.3: every component off compiles to the E22 direct base bytes, byte proof e220; form proof, claims_benefit false; re-pinned by scripts/flights/repin_cell.py, decision receipt earnings22-native-stage3-module-alloff-v1-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
CP=$(dirname "$0")
bash $SP/repin_loop_generic.sh $CP/module_alloff_e220_repin_smoke.sh $RD earnings22-native-stage3-module-alloff-smoke-4-v1 smoke-generation /home/chao/module-alloff-e220-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $CP/module_alloff_e220_repin_arm.sh   $RD earnings22-native-stage3-module-alloff-v1         generation       /home/chao/module-alloff-e220-arm-commit.txt   || exit $?
cd "$MAIN" && git rev-parse HEAD > /home/chao/module-alloff-e220-flight-commit.txt
echo "flight commit $(cat /home/chao/module-alloff-e220-flight-commit.txt)"
