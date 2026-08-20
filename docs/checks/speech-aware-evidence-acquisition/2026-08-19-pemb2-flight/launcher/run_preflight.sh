#!/usr/bin/env bash
# P-EMB pre-flight -- zero model contact, zero server spawn.
# Usage: run_preflight.sh <A|B>
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri2/pemb
source "$SDIR/env.sh"
RUN="${1:?usage: run_preflight.sh <A|B>}"
case "$RUN" in
  A) export SAEA_FEAT_CACHE_DIR=/home/chao/feat-cache/slurp-q4km ;;
  B) export SAEA_FEAT_CACHE_DIR=/home/chao/feat-cache/audio2tool-q4km ;;
  *) echo "unknown run $RUN"; exit 2 ;;
esac
mkdir -p "$SAEA_FEAT_CACHE_DIR"
cd "$REPO"
LOG="$SCRATCH/preflight-run$RUN.log"
{
  echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "run: $RUN"
  echo "git HEAD: $(git -C "$REPO" rev-parse HEAD)"
  echo "git status: $(git -C "$REPO" status --porcelain | wc -l) dirty entries"
  echo "bytecode under the frozen scoring package (D3 gate): $(find "$REPO/src/speech_aware_evidence_acquisition/scoring" -name '__pycache__' -o -name '*.pyc' | wc -l)"
  echo "feat cache: $SAEA_FEAT_CACHE_DIR"
  echo "orphan llama-server:"
  pgrep -af llama-server || echo "  (none)"
  echo "llama-server binary sha256 (receipt pins 097c96ec...):"
  sha256sum /home/chao/llama.cpp-featcache/build/bin/llama-server
  python -u "$SCRATCH/preflight.py" --run "$RUN"
  echo "preflight exit: $?"
  echo "end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} 2>&1 | tee "$LOG"
grep -q "PRE-FLIGHT CLEAN" "$LOG"
