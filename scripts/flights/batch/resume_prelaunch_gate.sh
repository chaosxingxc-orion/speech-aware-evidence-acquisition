#!/bin/bash
# Resume prelaunch gate (coordinator, after the COMP-1 resume attempt 3 seal abort): a four-row
# smoke cannot see seal-time checks on kept rows, so EVERY resume launch first passes the OFFLINE
# full-trace replay check. Thin wrapper: scripts/checks/resume_prelaunch_gate_check.py does the
# actual work (reads the named cell's resume_from, verifies every predecessor trace hashes to its
# declared identity, then runs scripts/analysis/replay_seal_consistency.py over every predecessor
# under the CURRENT code) and this script is kept as a plain command-line entry point so
# scripts/flights/batch/batch_driver.sh and scripts/flights/comp1/batch_chain_comp1_resume.sh call
# it exactly like every other prelaunch gate in this family. Zero model, server or GPU contact.
#
# Usage: resume_prelaunch_gate.sh --repo-root REPO --data-root DATA --experiment EXP --cell CELL
# Exit 0: not a resume cell, or every predecessor replays clean. 1: the replay found a failing row
# or a row sealed twice. 2: the cell, its resume_from, a predecessor trace, or the checker itself
# cannot be read or trusted.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PY=${PY:-/home/chao/.venvs/speechrl/bin/python}
exec "$PY" -B "$HERE/../../checks/resume_prelaunch_gate_check.py" "$@"
