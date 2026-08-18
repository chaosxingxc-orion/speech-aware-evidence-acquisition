#!/usr/bin/env bash
# Model-free Stage-2 flight-plan measurement.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2fly2/env.sh
cd "$REPO"
python -u "$SCRATCH/measure_split.py" "$SCRATCH/preflight-split-measurement.json" 2>&1 | tee "$SCRATCH/preflight-split-measurement.log"
exit "${PIPESTATUS[0]}"
