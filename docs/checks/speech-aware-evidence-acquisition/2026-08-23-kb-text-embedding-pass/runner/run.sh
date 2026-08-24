#!/usr/bin/env bash
# The ONE-SHOT execution of SAEA-SN-TOOL-KB-TEXT-EMB-PASS. No retry wrapper by design.
source "$(dirname "$0")/env.sh"

python "$SCRATCH/run_kb_text_embedding_pass.py"
status=$?
echo "RUNNER EXIT STATUS: $status"
exit $status
