#!/usr/bin/env bash
# P-TRAP pre-flight -- zero model contact.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri/ptrap
sed -i 's/\r$//' "$SDIR"/*.sh "$SDIR"/*.py 2>/dev/null || true
source "$SDIR/env.sh"
cd "$REPO"
LOG="$SCRATCH/preflight.log"
{
  echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "git HEAD: $(git -C "$REPO" rev-parse HEAD)"
  echo "git status: $(git -C "$REPO" status --porcelain | wc -l) dirty entries"
  echo "bytecode under the frozen scoring package (D3 gate): $(find "$REPO/src/speech_aware_evidence_acquisition/scoring" -name '__pycache__' -o -name '*.pyc' | wc -l)"
  echo "orphan llama-server:"
  pgrep -af llama-server || echo "  (none)"
  echo "llama-server binary sha256 (receipt pins 097c96ec...):"
  sha256sum /home/chao/llama.cpp-featcache/build/bin/llama-server
  python -u "$SCRATCH/preflight.py"
  echo "preflight exit: $?"
  echo "end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} 2>&1 | tee "$LOG"
grep -q "PRE-FLIGHT CLEAN" "$LOG"
