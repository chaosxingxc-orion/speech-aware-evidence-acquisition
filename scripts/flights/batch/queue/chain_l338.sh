#!/usr/bin/env bash
# L338 chain (owner rulings 338 and 341 A): swap to the resident np4 Thinking session (a no-op when it is resident) -> smoke-4 -> machine sign-off (marker
# /home/chao/l338-decode-signoff.marker, 20-minute coordinator veto window) -> the lever column -> close the ledger rows. Started by the launch spec's chain
# step as the Windows task SAEA-Chain-L338. Install by copying this file to /home/chao/saea-queue/chain_l338.sh (the launch spec's chain.wrapper). For a recovery
# re-launch change `all` to `arm-only` (the sealed smoke is never re-flown).
M=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
cd "$M" || exit 1
L=/home/chao/l338-chain.out
echo "chain start $(date -u +%FT%TZ) flight commit $(cat /home/chao/l338-flight-commit.txt 2>/dev/null)" >> "$L"
bash scripts/flights/nx/batch_chain_l338.sh all >> "$L" 2>&1; rc=$?
echo "CHAIN_L338_EXIT rc=$rc $(date -u +%FT%TZ)" >> "$L"; exit $rc
