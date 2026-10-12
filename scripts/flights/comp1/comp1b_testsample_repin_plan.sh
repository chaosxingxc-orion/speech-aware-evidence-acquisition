#!/bin/bash
# Re-pin MILESTONE-00-PLAN (the locked v2.0 plan on SLURP-TEST-SAMPLE-3010-V1; owner decisions 151 and 202). Its own
# first-phase supply is minted model-free at this step (item E16); never pass --allow-output-change. Model-free.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1 CELL=slurp-native-stage3-plan-testsample-milestone00-v1 PKG=slurp-stage3-comp1b-testsample-v1 PREREG=docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1-preregistration.md DEC_PATH=coordination/slurp-stage3-comp1b-testsample-v1/root-admission-v1.json DEC_ID=slurp-stage3-comp1b-testsample-milestone-admission-v1 TAG=comp1bts-plan MSG=/home/chao/comp1bts-plan-commit.txt bash $SP/repin_cell_generic.sh
