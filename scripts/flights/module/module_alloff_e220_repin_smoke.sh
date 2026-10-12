#!/bin/bash
# Re-pin the Earnings-22 module all-off arm's four-row form smoke through the generic flip. Model-free. Carrier admission
# gate (design 2b.3; owner decision 196, direction 205). HELD under decision 187: run only after the owner reopens Earnings.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-10-11-earnings22-module-alloff-v1 CELL=earnings22-native-stage3-module-alloff-smoke-4-v1 PKG=earnings22-native-stage3-module-alloff-v1 PREREG=docs/readiness/2026-10-11-earnings22-module-alloff-v1-preregistration.md DEC_PATH=coordination/earnings22-native-stage3-module-alloff-v1/root-admission-v1.json DEC_ID=earnings22-native-stage3-module-alloff-v1-admission-v1 TAG=module-alloff-e220-smoke MSG=/home/chao/module-alloff-e220-smoke-commit.txt bash $SP/repin_cell_generic.sh
