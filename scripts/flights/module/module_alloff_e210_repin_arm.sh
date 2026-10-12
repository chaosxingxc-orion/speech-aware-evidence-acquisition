#!/bin/bash
# Re-pin the Earnings-21 module all-off arm (full 44-call discovery, 1,593 windows). ARM=1: records the flight commit,
# prints the check summary and runs the results-ledger gate; the check attaches to NOTHING. Model-free. Carrier admission
# gate (design 2b.3). HELD under decision 187: run only after the owner reopens Earnings.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-30-earnings21-native-stage3-module-alloff-v1 CELL=earnings21-native-stage3-module-alloff-v1 PKG=earnings21-native-stage3-module-alloff-v1 PREREG=docs/readiness/2026-09-30-earnings21-native-stage3-module-alloff-v1-preregistration.md DEC_PATH=coordination/earnings21-native-stage3-module-alloff-v1/root-admission-v1.json DEC_ID=earnings21-native-stage3-module-alloff-v1-admission-v1 TAG=module-alloff-e210-arm ARM=1 MSG=/home/chao/module-alloff-e210-arm-commit.txt bash $SP/repin_cell_generic.sh
