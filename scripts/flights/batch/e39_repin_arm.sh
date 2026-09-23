#!/bin/bash
# E39 four-row dry run flip (item E39, base lock v3.1 candidate): env for repin_cell_generic.sh
export RD=docs/readiness/2026-09-23-e21-native-window-four-row-e39-v1
export CELL=e21-native-window-system-four-row-e39-v1 EXP=e21-native-window-four-row-e39-dry-run-v1
export PKG=e21-native-window-four-row-e39-v1
export PREREG=docs/readiness/2026-09-23-e21-native-window-four-row-e39-v1-preregistration.md
export DEC_PATH=coordination/e21-native-window-four-row-e39-v1/root-admission-v1.json
export DEC_ID=e21-native-window-four-row-e39-admission-v1
export TAG=e39-arm ARM=1
export MSG=/home/chao/e39-arm-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
