#!/bin/bash
# Windows Scheduled Task "SAEA-Prep-Devel-Remainder" (owner decision 107): the registered packet promotion
# SAEA-SN-DEVEL-REMAINDER-PREPROCESS (6,570 label-free encoder calls on the -np 8 CPU sidecar, 0 GPU-h) beside the
# resident GPU session. Launch ONLY after SAEA-SN-DEVEL-REMAINDER-NP8-EQUIVALENCE-4-V1 returned EQUIVALENT.
export PREP_ROSTER=devel-remainder PREP_WORKERS=8 PREP_PROMOTE_WORKERS=8
exec bash "$(dirname "$0")/prep_generic_task_entry.sh"
