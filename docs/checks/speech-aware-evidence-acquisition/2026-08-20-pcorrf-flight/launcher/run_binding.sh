#!/usr/bin/env bash
# P-CORR-F binding phase -- OFFLINE, zero model calls, zero gold.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf
sed -i 's/\r$//' "$SDIR"/*.sh "$SDIR"/*.py 2>/dev/null || true
source "$SDIR/env.sh"
cd "$REPO"
python -u "$SCRATCH/binding.py" --out-dir "$SCRATCH" 2>&1 | tee "$SCRATCH/binding.log"
exit "${PIPESTATUS[0]}"
