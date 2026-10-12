#!/bin/bash
# Flip cell R-PRIM (smoke, then the 1,080-row arm) to ready on master: model-free; the flight itself waits for the SLURP geometry.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-22-slurp-review-primitives-v1
cat > /home/chao/rprim-smoke-commit.txt <<'M'
research: flip the R-PRIM four-row smoke to ready (item E37, owner decision 84; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-review-primitives-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
cat > /home/chao/rprim-arm-commit.txt <<'M'
research: flip cell R-PRIM (1,080-row TRAIN A arm) to ready (item E37, owner decision 84; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-review-primitives-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
bash $SP/repin_loop_generic.sh $SP/rprim_repin_smoke.sh $RD slurp-native-review-primitives-smoke-4-v1 smoke-generation /home/chao/rprim-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/rprim_repin_arm.sh $RD slurp-native-review-primitives-v1 generation /home/chao/rprim-arm-commit.txt
