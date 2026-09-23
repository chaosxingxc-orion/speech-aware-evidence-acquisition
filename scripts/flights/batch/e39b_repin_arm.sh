#!/bin/bash
# E39b flip (the one recovery of the E39 dry run, caps 640 / 640): env for repin_cell_generic.sh
export RD=docs/readiness/2026-09-23-e21-native-window-four-row-e39b-v1
export CELL=e21-native-window-system-four-row-e39b-v1 EXP=e21-native-window-four-row-e39b-dry-run-v1
export PKG=e21-native-window-four-row-e39b-v1
export PREREG=docs/readiness/2026-09-23-e21-native-window-four-row-e39b-v1-preregistration.md
export DEC_PATH=coordination/e21-native-window-four-row-e39b-v1/root-admission-v1.json
export DEC_ID=e21-native-window-four-row-e39b-admission-v1
export TAG=e39b-arm ARM=1
export MSG=/home/chao/e39b-arm-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
