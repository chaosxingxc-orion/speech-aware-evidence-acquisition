#!/usr/bin/env bash
# P-A2T whole-population split measurement -- model-free, zero core contact.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri/pop
sed -i 's/\r$//' "$SDIR"/*.sh "$SDIR"/*.py 2>/dev/null || true
source "$SDIR/env.sh"
cd "$REPO"
python -u "$SCRATCH/measure.py" 2>&1 | tee "$SCRATCH/measure.log"
exit "${PIPESTATUS[0]}"
