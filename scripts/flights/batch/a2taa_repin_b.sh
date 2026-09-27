#!/bin/bash
# A2T-AA pass B flip: env for repin_cell_generic.sh (loop form; plan prefix b-generation). Prefer a2taa_flip_all.sh.
# In the loop form this is the LAST flip, so /home/chao/a2taa-b-flight-commit.txt is the chain's flight commit.
export RD=docs/readiness/2026-09-27-a2t-stage3-aa-paired-400-v1
export CELL=a2t-stage3-aa-paired-400-b-v1
export PKG=a2t-stage3-aa-paired-400-v1
export PREREG=docs/readiness/2026-09-27-a2t-stage3-aa-paired-400-v1-preregistration.md
export DEC_PATH=coordination/a2t-stage3-aa-paired-400-v1/root-admission-v1.json
export DEC_ID=a2t-stage3-aa-paired-400-admission-v1
export TAG=a2taa-b ARM=1
export MSG=/home/chao/a2taa-b-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
