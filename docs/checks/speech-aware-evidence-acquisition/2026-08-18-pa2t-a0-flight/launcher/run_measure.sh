#!/usr/bin/env bash
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/a2tfly2/env.sh
cd "$REPO"
python -u "$SCRATCH/measure_split.py" "$SCRATCH/split-measurement.json" 2>&1 | tee "$SCRATCH/split-measurement.log"
exit "${PIPESTATUS[0]}"
