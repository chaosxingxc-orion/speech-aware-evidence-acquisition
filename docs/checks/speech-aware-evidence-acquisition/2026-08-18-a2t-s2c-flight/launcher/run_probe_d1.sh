#!/usr/bin/env bash
# D1 audio2tool media-identity probe -- zero model contact.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2cfly/env.sh
cd "$REPO"
LOG="$SCRATCH/preflight-d1-probe.log"
{
  echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python -u "$SCRATCH/probe_d1.py"
  echo "exit: $? at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} 2>&1 | tee "$LOG"
