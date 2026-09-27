#!/bin/bash
# Item E41 sub10 re-read flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# Run ONLY after the E41 dry-run read holds R1-R3 and the sub10 decision receipt is minted
# (scripts/flights/e41/e41_mint_receipt.py --which sub10 refuses while its dry_run_read antecedent is a placeholder).
# Same package as the dry run, but the two cells share no hash: the shared protocol document quotes neither cell's
# composed / protocol hash, so this flip rewrites only the sub10 plan files, the facts, the README and the
# preregistration -- never the (by then flown) dry-run plans.
export RD=docs/readiness/2026-09-27-e21-native-window-e41-v1
export CELL=e21-native-window-system-sub10-e41-v1
export EXP=e21-native-window-sub10-e41-v1
export PKG=e21-native-window-e41-v1
export PREREG=docs/readiness/2026-09-27-e21-native-window-e41-v1-preregistration.md
export DEC_PATH=coordination/e21-native-window-e41-v1/root-admission-sub10-v1.json
export DEC_ID=e21-native-window-e41-sub10-admission-v1
export TAG=e41-sub10 ARM=1
export MSG=/home/chao/e41-sub10-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
