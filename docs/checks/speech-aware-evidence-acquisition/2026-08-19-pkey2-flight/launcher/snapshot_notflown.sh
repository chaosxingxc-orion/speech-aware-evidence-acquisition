#!/usr/bin/env bash
# Attempt-2 NOT-FLOWN evidence snapshot. Model-free; touches only the scratchpad.
set -euo pipefail
S=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pkey2fly

cp "$S/preflight.log" "$S/attempt2-preflight-NOT-FLOWN.log"
cp "$S/preflight-pytest.log" "$S/attempt2-preflight-pytest.log"
ls -la "$S"/attempt2-*

echo "--- runs dir (must still hold ONLY attempt-1) ---"
ls /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-PROBE-pkey2-338/
echo "--- attempt store (must still hold ONLY attempt-1) ---"
ls /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/attempts/SAEA-PROBE-pkey2-338/
echo "--- llama-server ---"
pgrep -a llama-server || echo "none running (zero model contact this session)"
