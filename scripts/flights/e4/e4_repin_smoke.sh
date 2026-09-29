#!/bin/bash
# Cell E4-1 charged four-row dry run flip: env for scripts/flights/batch/repin_cell_generic.sh.
# Model-free. The same program switch and native_episode.relisten block on four TRAIN Fold A rows
# chosen to exercise the blind and forced-choice contacts (scripts/flights/e4/e4_cost_measure.py);
# form proof only, never scored for benefit, never read. No ALLOW_OUTPUT_CHANGE; the dry run's roster
# is new, so its minted supply has no AGREE counterpart digest.
export RD=docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1
export CELL=slurp-native-stage3-relisten-fold-a-smoke-4-v1
export EXP=slurp-native-stage3-relisten-fold-a-smoke-4-v1
export PKG=slurp-stage3-relisten-fold-a-v1
export PREREG=docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-relisten-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-relisten-fold-a-admission-v1
export TAG=e4-smoke
export MSG=/home/chao/e4-smoke-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
