#!/bin/bash
# Re-pin the REV-TFRL-1 arm (the AGREE arm with the Reviewer instruction moved to the contrastive form selected offline; its minted supply must carry the sealed AGREE output digest eab5c61e...). ARM=1: records the flight commit, prints the check summary and runs the results-ledger gate through the generic flip. Model-free; attaches to nothing.
# No ALLOW_OUTPUT_CHANGE: no cell carries a committed prepared_phase_supply pin, so the flip mints this
# cell's own supply under its own run id (item E16) beside the kept agreement-table requirement.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-reviewer-tfrl-v1 CELL=slurp-native-stage3-revtfrl-fold-a-v1 PKG=slurp-stage3-revtfrl-fold-a-v1 PREREG=docs/readiness/2026-09-27-slurp-stage3-reviewer-tfrl-v1-preregistration.md DEC_PATH=coordination/slurp-stage3-revtfrl-fold-a-v1/root-admission-v1.json DEC_ID=slurp-stage3-revtfrl-fold-a-admission-v1 TAG=revtfrl-arm ARM=1 MSG=/home/chao/revtfrl-arm-commit.txt bash $SP/repin_cell_generic.sh
