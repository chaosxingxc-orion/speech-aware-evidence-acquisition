#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The model-free proof of the HELD Earnings-22 all-off cells (2026-10-11): the execution-unit roster, the knowledge-snapshot
# requirement and the 4-row / full wire check, each run in a private mount namespace with an overlay over the data directory
# so that nothing it writes survives (the upper layer lives in /tmp and is deleted). NO model, encoder, server, network or
# lease. The expected result today: units ok (4 and 451), snapshot REFUSED (FlightRuntime._load_knowledge_snapshot), wire
# REFUSED at core.driver.run.load_window_packet_binding (the Earnings-22 window feature packets do not exist yet).
#   bash scripts/flights/module/module_alloff_e220_proof.sh   (from the worktree, venv active, PYTHONDONTWRITEBYTECODE=1)
HERE=$(cd "$(dirname "$0")" && pwd)
DATA=$SAEA_DATA_ROOT
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1
T=$(mktemp -d /tmp/e22ov.XXXXXX)
mkdir -p "$T/up" "$T/wk"
trap 'rm -rf "$T"' EXIT
for step in units snapshot wire; do
  for cell in earnings22-native-stage3-module-alloff-smoke-4-v1 earnings22-native-stage3-module-alloff-v1; do
    echo "--- $step $cell"
    unshare -rm sh -c "mount -t overlay overlay -o lowerdir=$DATA,upperdir=$T/up,workdir=$T/wk $DATA && exec \"\$@\"" -- \
      python -B "$HERE/module_alloff_e220_proof_steps.py" "$cell" "$step" 2>&1 | tail -6
  done
done
echo "overlay files written (all discarded): $(find "$T/up" -type f | wc -l)"
