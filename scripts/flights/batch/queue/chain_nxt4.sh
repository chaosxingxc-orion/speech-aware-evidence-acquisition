#!/usr/bin/env bash
# NX-T R4 chain (owner rulings 329 A and 332 A): swap to the resident np4 Thinking session (a no-op when it is resident) -> smoke-4 -> machine sign-off (marker
# /home/chao/nxt4-decode-signoff.marker, 20-minute coordinator veto window) -> the Solver decoding-policy column -> close the ledger rows. Started by the launch spec's chain
# step as the Windows task SAEA-Chain-NXT4. Install by copying this file to /home/chao/saea-queue/chain_nxt4.sh (the launch spec's chain.wrapper). For a recovery
# re-launch change `all` to `arm-only` (the sealed smoke is never re-flown).
M=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
cd "$M" || exit 1
L=/home/chao/nxt4-chain.out
echo "chain start $(date -u +%FT%TZ) flight commit $(cat /home/chao/nxt4-flight-commit.txt 2>/dev/null)" >> "$L"
# 2026-10-24: the 330 A Solver reasoning diagnostic (56 calls, < 1 GPU-h) refused in the 322 window (D3 gate: stray __pycache__) and refuses
# while a flight is open, so it runs here in the no-flight gap between the R3 seal and the R4 smoke; its failure is logged and never blocks R4.
( export SPEECHRL_DATA_DIR=/home/chao/saea-data/speechrl-data DATA=/home/chao/saea-data/speechrl-data MAIN=$M PYTHONPATH=$M/src PYTHONDONTWRITEBYTECODE=1 PY=python
  source /home/chao/.venvs/speechrl/bin/activate; find "$M/src" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null
  bash scripts/flights/diag/solver_reasoning_diag.sh >> /home/chao/diag330-chain.out 2>&1; echo "diagnostic (330 A) rc=$? $(date -u +%FT%TZ)" >> "$L" )
bash scripts/flights/nx/batch_chain_nxt_r4.sh all >> "$L" 2>&1; rc=$?
echo "CHAIN_NXT4_EXIT rc=$rc $(date -u +%FT%TZ)" >> "$L"; exit $rc
