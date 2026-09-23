#!/bin/bash
# Windows Scheduled Task "SAEA-Prep-Devel-Remainder-Encode" (owner decision 107): preparations 2 and 3 of the DEVEL-REMAINDER
# v2 roster -- the registered speech-query encoding SAEA-SLURP-DEVEL-REMAINDER-SPEECH-QUERY-ENCODING-V1 (6,570 pinned
# retrieval-encoder contacts on the CPU, one registered pass) and the model-free content derivative
# SAEA-SLURP-DEVEL-REMAINDER-QUERY-VECTOR-EXPORT-V1. Runs only after SAEA-SN-DEVEL-REMAINDER-PREPROCESS sealed.
export PREP_SET=devel-remainder
exec bash "$(dirname "$0")/prep_generic_encode_task_entry.sh"
