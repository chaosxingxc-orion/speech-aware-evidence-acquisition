#!/usr/bin/env bash
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri/env.sh
cd "$REPO"
echo "=== scoring package bytecode (D3 gate scope) ==="
find "$REPO/src/speech_aware_evidence_acquisition/scoring" -name '__pycache__' -o -name '*.pyc' | wc -l
echo "=== full suite ==="
python -m pytest -q 2>&1 | tee "$TRI/preflight-pytest.log" | tail -8
rc=${PIPESTATUS[0]}
echo "pytest exit: $rc"
exit "$rc"
