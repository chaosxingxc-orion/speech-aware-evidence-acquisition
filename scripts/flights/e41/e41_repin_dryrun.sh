#!/bin/bash
# Item E41 dry-run flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# The E41 dry run is the sealed E39b dry-run form (base lock v3.1) with ONE pin moved -- the Perception
# instruction, v1 -> the bounded note v2 (owner decisions 103 and 158) -- on the E35 / E39 / E39b four-row roster.
# No ALLOW_OUTPUT_CHANGE: the program declares no supplied first phase (item E38), so the re-pin tool pins no
# prepared artifact and flips on the decision requirement alone.
# ARM=1: records the flight commit, prints the check summary and runs the results-ledger gate. The check
# attaches to NOTHING; the resident SLURP np4 session is untouched at flip time.
export RD=docs/readiness/2026-09-27-e21-native-window-e41-v1
export CELL=e21-native-window-system-four-row-e41-v1
export EXP=e21-native-window-four-row-e41-dry-run-v1
export PKG=e21-native-window-e41-v1
export PREREG=docs/readiness/2026-09-27-e21-native-window-e41-v1-preregistration.md
export DEC_PATH=coordination/e21-native-window-e41-v1/root-admission-dry-run-v1.json
export DEC_ID=e21-native-window-e41-dry-run-admission-v1
export TAG=e41-dryrun ARM=1
export MSG=/home/chao/e41-dryrun-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
