#!/bin/bash
# Re-pin the Audio2Tool module all-off arm (paired 400). ARM=1: records the flight commit, prints the check summary and runs
# the results-ledger gate; the check attaches to NOTHING. Model-free. Carrier admission gate (design 2b.3). HELD under
# decision 187: run only after the owner reopens Audio2Tool.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-30-a2t-native-stage3-module-alloff-v1 CELL=a2t-native-stage3-module-alloff-v1 PKG=a2t-native-stage3-module-alloff-v1 PREREG=docs/readiness/2026-09-30-a2t-native-stage3-module-alloff-v1-preregistration.md DEC_PATH=coordination/a2t-native-stage3-module-alloff-v1/root-admission-v1.json DEC_ID=a2t-native-stage3-module-alloff-v1-admission-v1 TAG=module-alloff-a2t0-arm ARM=1 MSG=/home/chao/module-alloff-a2t0-arm-commit.txt bash $SP/repin_cell_generic.sh
