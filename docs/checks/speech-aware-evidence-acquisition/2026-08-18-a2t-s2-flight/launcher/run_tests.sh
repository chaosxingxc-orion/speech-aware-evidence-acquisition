#!/usr/bin/env bash
# Suite sanity for the Stage-2 supply-arm flight machinery.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2fly2/env.sh
cd "$REPO"
python -m pytest tests/unit/test_a2t_s2_flight.py tests/unit/test_a2t_s2_flight_config.py -q 2>&1 | tee "$SCRATCH/preflight-tests.log"
exit "${PIPESTATUS[0]}"
