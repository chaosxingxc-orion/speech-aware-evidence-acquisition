#!/usr/bin/env bash
# NX-T R2b chain (owner rulings 325 A / 327 A): swap to the raised-cap Thinking session -> smoke-4 -> machine sign-off (marker /home/chao/nxt2b-decode-signoff.marker,
# 20-minute coordinator veto window) -> the Solver reasoning-budget column -> close the ledger rows. Started by the launch spec's chain step as the Windows task
# SAEA-Chain-NXT2B. Install by copying this file to /home/chao/saea-queue/chain_nxt2b.sh (the launch spec's chain.wrapper).
M=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
cd "$M" || exit 1
L=/home/chao/nxt2b-chain.out
echo "chain start $(date -u +%FT%TZ) flight commit $(cat /home/chao/nxt2b-flight-commit.txt 2>/dev/null)" >> "$L"
bash scripts/flights/nx/batch_chain_nxt_r2b.sh all >> "$L" 2>&1; rc=$?
echo "CHAIN_NXT2B_EXIT rc=$rc $(date -u +%FT%TZ)" >> "$L"; exit $rc
