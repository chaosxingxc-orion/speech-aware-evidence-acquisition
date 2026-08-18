#!/usr/bin/env bash
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pslus2fly/env.sh
cd "$REPO"
python -m pytest -q 2>&1 | tee "$SCRATCH/preflight-pytest.log" | tail -5
rc=${PIPESTATUS[0]}
echo "pytest exit: $rc"
exit "$rc"
