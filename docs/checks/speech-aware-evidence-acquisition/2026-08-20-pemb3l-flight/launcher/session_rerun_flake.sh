#!/usr/bin/env bash
# Isolated re-run of the ONE test that failed in the full-suite pass, to
# separate a load-induced timing flake from a real regression. The test spawns
# a FAKE binary that is a shell script whose whole lifetime is `sleep 5`; the
# readiness wait fails closed if that child is already gone, so a machine busy
# enough to delay the check past 5 s fails it for reasons unrelated to any
# code path this flight touches.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pemb3l/env.sh
cd "$REPO"
{
  echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "load average: $(cat /proc/loadavg)"
  echo "=== the failing test, 5 consecutive isolated runs ==="
  for i in 1 2 3 4 5; do
    echo "--- run $i ---"
    python -m pytest -q -p no:cacheprovider \
      "tests/unit/test_session.py::TestStartSessionSpawn::test_spawn_writes_a_session_receipt_bound_to_the_real_process"
    echo "run $i exit: $?"
  done
  echo "=== the whole spawn class ==="
  python -m pytest -q -p no:cacheprovider "tests/unit/test_session.py::TestStartSessionSpawn"
  echo "class exit: $?"
  echo "=== the whole session module ==="
  python -m pytest -q -p no:cacheprovider tests/unit/test_session.py
  echo "module exit: $?"
  echo "=== the machinery this flight actually drives ==="
  python -m pytest -q -p no:cacheprovider \
    tests/unit/test_pemb3l_flight.py tests/unit/test_pemb_flight.py tests/unit/test_rails_embedding_client.py
  echo "machinery exit: $?"
  echo "end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} 2>&1 | tee "$SCRATCH/preflight-pytest-rerun.log"
