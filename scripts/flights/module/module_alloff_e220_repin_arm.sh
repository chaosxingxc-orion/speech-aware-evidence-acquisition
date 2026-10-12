#!/bin/bash
# Re-pin the Earnings-22 module all-off arm (whole 10-call dev split, 451 windows). ARM=1: records the flight commit,
# prints the check summary and runs the results-ledger gate; the check attaches to NOTHING. Model-free. Carrier admission
# gate (design 2b.3). HELD under decision 187: run only after the owner reopens Earnings.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-10-11-earnings22-module-alloff-v1 CELL=earnings22-native-stage3-module-alloff-v1 PKG=earnings22-native-stage3-module-alloff-v1 PREREG=docs/readiness/2026-10-11-earnings22-module-alloff-v1-preregistration.md DEC_PATH=coordination/earnings22-native-stage3-module-alloff-v1/root-admission-v1.json DEC_ID=earnings22-native-stage3-module-alloff-v1-admission-v1 TAG=module-alloff-e220-arm ARM=1 MSG=/home/chao/module-alloff-e220-arm-commit.txt bash $SP/repin_cell_generic.sh
