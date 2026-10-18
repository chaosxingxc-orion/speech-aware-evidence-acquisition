#!/bin/bash
# Prints the first `rc=<N>` of a CHAIN_NXT2_EXIT line in /home/chao/nxt2-chain.out stamped after $1 (nothing when there is none yet).
# Used by window_322_orchestrator.ps1 (owner rulings 322 A / 331 A, 2026-10-18).
awk -v s="${1:?stamp}" '$1 == "CHAIN_NXT2_EXIT" && $3 > s { print $2; exit }' /home/chao/nxt2-chain.out 2>/dev/null
