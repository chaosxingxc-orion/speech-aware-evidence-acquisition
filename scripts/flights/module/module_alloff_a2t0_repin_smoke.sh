#!/bin/bash
# Re-pin the Audio2Tool module all-off arm's four-row form smoke through the generic flip. Model-free. Carrier admission gate
# (design 2b.3; owner decision 196, direction 205). HELD under decision 187: run only after the owner reopens Audio2Tool.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-30-a2t-native-stage3-module-alloff-v1 CELL=a2t-native-stage3-module-alloff-smoke-4-v1 PKG=a2t-native-stage3-module-alloff-v1 PREREG=docs/readiness/2026-09-30-a2t-native-stage3-module-alloff-v1-preregistration.md DEC_PATH=coordination/a2t-native-stage3-module-alloff-v1/root-admission-v1.json DEC_ID=a2t-native-stage3-module-alloff-v1-admission-v1 TAG=module-alloff-a2t0-smoke MSG=/home/chao/module-alloff-a2t0-smoke-commit.txt bash $SP/repin_cell_generic.sh
