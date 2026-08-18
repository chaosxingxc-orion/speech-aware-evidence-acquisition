#!/usr/bin/env bash
# Pinned suite sanity for the Stage-2b flight machinery (28 flight tests).
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2bfly/env.sh
cd "$REPO"
LOG="$SCRATCH/preflight-tests.log"
{
  echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python -m pytest tests/unit/test_a2t_s2b_flight.py -q
  echo "--- config suite ---"
  python -m pytest tests/unit/test_a2t_s2b_flight_config.py -q
  echo "exit: $? at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} 2>&1 | tee "$LOG"
