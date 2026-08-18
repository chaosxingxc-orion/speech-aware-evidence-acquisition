#!/usr/bin/env bash
# P-A2T Stage-2 supply-probe PRE-FLIGHT (zero model contact).
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2fly2/env.sh
cd "$REPO"
python -u "$SCRATCH/preflight.py" 2>&1 | tee "$SCRATCH/preflight.log"
exit "${PIPESTATUS[0]}"
