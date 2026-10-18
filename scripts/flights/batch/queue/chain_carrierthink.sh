#!/usr/bin/env bash
# Carrier base chain (owner rulings 302 A / 306 A / 333 B): for the carriers A2T -> E21 -> E22, on the SLURP lock's resident Thinking session (swapped to when it is not
# resident): four-unit smoke -> machine sign-off (marker /home/chao/carrierthink-<carrier>-decode-signoff.marker, 20-minute coordinator veto window) -> the all-off arm -> the
# direct arm -> close the ledger rows. Started by the launch spec's chain step (or the queue hook) as the Windows task SAEA-Chain-CARRIERTHINK. Install by copying this file
# to /home/chao/saea-queue/chain_carrierthink.sh (the launch spec's chain.wrapper). The segment defaults to `all`; set CARRIERTHINK_SEGMENT in the task environment for a
# single carrier or a recovery segment (a2t | e21 | e22 | <carrier>:smoke | <carrier>:arms | <carrier>:arms-only).
M=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
cd "$M" || exit 1
L=/home/chao/carrierthink-chain.out
SEG=${CARRIERTHINK_SEGMENT:-all}
echo "chain start $(date -u +%FT%TZ) segment $SEG flight commit $(cat /home/chao/carrierthink-flight-commit.txt 2>/dev/null)" >> "$L"
bash scripts/flights/carriers/batch_chain_carrier_think.sh "$SEG" >> "$L" 2>&1; rc=$?
echo "CHAIN_CARRIERTHINK_EXIT rc=$rc $(date -u +%FT%TZ)" >> "$L"; exit $rc
