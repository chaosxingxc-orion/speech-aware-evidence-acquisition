#!/usr/bin/env bash
# Compile + dry-import every launcher module. Zero model contact: --help exits
# in argparse, long before any server spawn.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf
sed -i 's/\r$//' "$SDIR"/*.sh "$SDIR"/*.py 2>/dev/null || true
source "$SDIR/env.sh"
cd "$REPO"
echo "=== py_compile ==="
python -m py_compile "$SCRATCH"/binding.py "$SCRATCH"/flight_identity.py "$SCRATCH"/preflight.py "$SCRATCH"/launch_pcorrf_flight.py && echo "  compile OK"
echo "=== bash -n ==="
for f in "$SDIR"/*.sh; do bash -n "$f" || echo "  SYNTAX ERROR in $f"; done
echo "  bash OK"
echo "=== launcher dry import (--help; argparse exits before any spawn) ==="
python -u "$SCRATCH/launch_pcorrf_flight.py" --help > /dev/null && echo "  import + argparse OK"
echo "=== D3 gate after compile checks ==="
echo "  scoring pkg bytecode: $(find "$REPO/src/speech_aware_evidence_acquisition/scoring" -name '__pycache__' -o -name '*.pyc' | wc -l)"
echo "SYNTAX CHECK DONE"
