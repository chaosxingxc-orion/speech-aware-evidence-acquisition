#!/usr/bin/env bash
# Carrier packets chain (owner ruling 333 B, P3.2): per carrier A2T -> E21 -> E22 one serving-swap window that encodes the Thinking speech packets on the GPU and promotes them into the
# shared Thinking packet root. Started by the packets launch spec's chain step as the Windows task SAEA-Chain-CARRIERPACKETS. Install by copying this file to
# /home/chao/saea-queue/chain_carrierpackets.sh. Set CARRIERPACKETS_SEGMENT in the task environment for one carrier (a2t | e21 | e22); the default is `all`.
M=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
cd "$M" || exit 1
L=/home/chao/carrierpackets-chain.out
SEG=${CARRIERPACKETS_SEGMENT:-all}
echo "chain start $(date -u +%FT%TZ) segment $SEG HEAD $(git rev-parse --short HEAD)" >> "$L"
bash scripts/flights/carriers/batch_chain_carrier_packets.sh "$SEG" >> "$L" 2>&1; rc=$?
echo "CHAIN_CARRIERPACKETS_EXIT rc=$rc $(date -u +%FT%TZ)" >> "$L"; exit $rc
