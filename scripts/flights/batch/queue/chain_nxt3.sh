#!/usr/bin/env bash
# NX-T R3 chain (owner ruling 326 A): swap to the resident np4 Thinking session (a no-op when it is resident) -> smoke-4 -> machine sign-off (marker
# /home/chao/nxt3-decode-signoff.marker, 20-minute coordinator veto window) -> the Solver template column -> close the ledger rows. Started by the launch spec's chain
# step as the Windows task SAEA-Chain-NXT3. Install by copying this file to /home/chao/saea-queue/chain_nxt3.sh (the launch spec's chain.wrapper). For a recovery
# re-launch change `all` to `arm-only` (the sealed smoke is never re-flown).
M=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
cd "$M" || exit 1
L=/home/chao/nxt3-chain.out
echo "chain start $(date -u +%FT%TZ) flight commit $(cat /home/chao/nxt3-flight-commit.txt 2>/dev/null)" >> "$L"
bash scripts/flights/nx/batch_chain_nxt_r3.sh all >> "$L" 2>&1; rc=$?
echo "CHAIN_NXT3_EXIT rc=$rc $(date -u +%FT%TZ)" >> "$L"; exit $rc
