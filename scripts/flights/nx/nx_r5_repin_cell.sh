#!/bin/bash
# Per-cell environment for scripts/flights/batch/repin_cell_generic.sh, for the NX R5 composed cells. Model-free.
# The caller exports NX_KIND (arm | smoke); repin_loop_generic.sh runs this script with no arguments on every pass.
# No ALLOW_OUTPUT_CHANGE: the cell carries NO committed prepared_phase_supply, so the re-pin tool MINTS the cell's own first-phase supply
# under its own run id (item E16). Expected output digests (registered-facts-v1.json prepared_supplies): arm ecca16a2..., smoke d5ec9b15...
# (the HELD module cells' own, which the lock, review-off and normaliser leaves never touch); a CHANGED digest means the knowledge channel
# moved -- stop and report. The replicate is re-pinned by scripts/flights/module/module_comp1bdev_repin_aa.sh, not here.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
SLUG=nx-r5-composed-dev2000-added; SHORT=nxr5
export RD=docs/readiness/2026-10-09-slurp-$SLUG-v1
export PKG=slurp-$SLUG-v1
export PREREG=$RD-preregistration.md
export DEC_PATH=coordination/$PKG/root-admission-v1.json
export DEC_ID=slurp-$SLUG-admission-v1
case "${NX_KIND:-}" in
  arm)   export CELL=slurp-native-stage3-$SLUG-v1 TAG=$SHORT-arm ;;
  smoke) export CELL=slurp-native-stage3-$SLUG-smoke-4-v1 TAG=$SHORT-smoke ;;
  *) echo "NX_KIND must be arm or smoke" >&2; exit 2;;
esac
export EXP=$CELL ARM=0
export MSG=/home/chao/$SHORT-$NX_KIND-commit.txt
unset ALLOW_OUTPUT_CHANGE
exec bash "$MAIN/scripts/flights/batch/repin_cell_generic.sh"
