#!/bin/bash
# A2T-AA pass A flip: env for repin_cell_generic.sh (loop form; plan prefix a-generation). Prefer a2taa_flip_all.sh.
export RD=docs/readiness/2026-09-27-a2t-stage3-aa-paired-400-v1
export CELL=a2t-stage3-aa-paired-400-a-v1
export PKG=a2t-stage3-aa-paired-400-v1
export PREREG=docs/readiness/2026-09-27-a2t-stage3-aa-paired-400-v1-preregistration.md
export DEC_PATH=coordination/a2t-stage3-aa-paired-400-v1/root-admission-v1.json
export DEC_ID=a2t-stage3-aa-paired-400-admission-v1
export TAG=a2taa-a ARM=1
export MSG=/home/chao/a2taa-a-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
