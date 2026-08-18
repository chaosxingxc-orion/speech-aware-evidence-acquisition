#!/usr/bin/env bash
# Pre-flight suite sanity: the FULL pytest suite, then the Stage-2c machinery
# suites called out explicitly (their counts go into the flight receipt).
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2cfly/env.sh
cd "$REPO"
LOG="$SCRATCH/preflight-tests.log"
{
  echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "--- full suite ---"
  python -m pytest -q
  echo "full-suite exit: $?"
  echo "--- s2c flight machinery suite ---"
  python -m pytest tests/unit/test_a2t_s2c_flight.py -q
  echo "--- s2c config suite ---"
  python -m pytest tests/unit/test_a2t_s2c_flight_config.py -q
  echo "exit: $? at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} 2>&1 | tee "$LOG"
