#!/usr/bin/env bash
# D1 media-identity probe for the Stage-2 headroom set (zero model contact).
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2fly2/env.sh
cd "$REPO"
python -u "$SCRATCH/probe_d1.py" 2>&1 | tee "$SCRATCH/preflight-d1-probe.log"
exit "${PIPESTATUS[0]}"
