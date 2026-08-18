#!/usr/bin/env bash
# P-A2T Stage-2c pre-flight -- zero model contact.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2cfly/env.sh
cd "$REPO"
LOG="$SCRATCH/preflight.log"
{
  echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "git HEAD: $(git -C "$REPO" rev-parse HEAD)"
  echo "git status: $(git -C "$REPO" status --porcelain | wc -l) dirty entries"
  echo "llama-server binary sha256 (receipt pins 097c96ec...):"
  sha256sum /home/chao/llama.cpp-featcache/build/bin/llama-server
  python -u "$SCRATCH/preflight.py"
  echo "exit: $? at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} 2>&1 | tee "$LOG"
