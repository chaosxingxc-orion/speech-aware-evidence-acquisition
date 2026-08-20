#!/usr/bin/env bash
# Full-suite pre-flight gate on a quiet machine. Zero model contact.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf
sed -i 's/\r$//' "$SDIR"/*.sh "$SDIR"/*.py 2>/dev/null || true
source "$SDIR/env.sh"
cd "$REPO"
echo "=== scoring package bytecode BEFORE (D3 gate scope) ==="
find "$REPO/src/speech_aware_evidence_acquisition/scoring" -name '__pycache__' -o -name '*.pyc' | wc -l
echo "=== full suite ==="
python -m pytest -q 2>&1 | tee "$SCRATCH/preflight-pytest.log" | tail -12
rc=${PIPESTATUS[0]}
echo "=== scoring package bytecode AFTER (D3 gate scope) ==="
find "$REPO/src/speech_aware_evidence_acquisition/scoring" -name '__pycache__' -o -name '*.pyc' | wc -l
echo "pytest exit: $rc"
echo "=== pcorrf test counts ==="
grep -c . /dev/null || true
exit "$rc"
