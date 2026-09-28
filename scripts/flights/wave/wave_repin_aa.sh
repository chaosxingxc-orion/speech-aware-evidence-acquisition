#!/bin/bash
# Re-pin the knowledge wave's shared in-chain A/A (the retained AGREE arm's own bytes) through the generic
# flip. Model-free. No ALLOW_OUTPUT_CHANGE: the cell carries NO committed prepared_phase_supply pin, so
# core.flight.repin.ensure_artifact_pinned MINTS its own under its own run id (item E16), and that supply
# must carry the AGREE arm's output digest eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae
# -- anything else means the Perception channel moved: stop and report (never pass --allow-output-change).
# Not ARM=1: the flight commit is recorded by scripts/flights/wave/wave_flip.sh once ALL wave cycles converge.
export RD=docs/readiness/2026-09-27-slurp-stage3-wave1-aa-fold-a-v1
export CELL=slurp-native-stage3-wave1-aa-fold-a-v1
export EXP=slurp-native-stage3-wave1-aa-fold-a-v1
export PKG=slurp-stage3-wave1-aa-fold-a-v1
export PREREG=docs/readiness/2026-09-27-slurp-stage3-wave1-aa-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-wave1-aa-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-wave1-aa-fold-a-admission-v1
export TAG=wave-aa
export MSG=/home/chao/wave-aa-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
