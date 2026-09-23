#!/bin/bash
# Windows Scheduled Task "SAEA-Prep-NP8-Equivalence" (owner decision 107): the registered four-row geometry-equivalence
# preflight SAEA-SN-DEVEL-REMAINDER-NP8-EQUIVALENCE-4-V1 (4 encoder calls into a SCRATCH cache; promotes nothing).
# Decision rule (ledger row): EQUIVALENT on 4 / 4 rows admits -np 8 for SAEA-SN-DEVEL-REMAINDER-PREPROCESS.
export PREP_ROSTER=devel-remainder-np8-equivalence-4 PREP_WORKERS=4 PREP_PROMOTE_WORKERS=8
exec bash "$(dirname "$0")/prep_generic_task_entry.sh"
