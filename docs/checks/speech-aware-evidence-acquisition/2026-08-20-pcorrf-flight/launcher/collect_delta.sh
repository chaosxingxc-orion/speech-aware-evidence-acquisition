#!/usr/bin/env bash
# Preflight checksum reconciliation ONLY: the mission brief cites "3354 passed /
# 9 skipped at 5c3e0fa" but this quiet-machine run at HEAD 1faccd8 reports 3355.
# 1faccd8 adds ONE readiness .md and no test code, so this compares COLLECTION
# COUNTS at both commits from read-only git-archive extracts. Zero model
# contact, zero writes to the study working tree.
set -uo pipefail
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf
source "$SDIR/env.sh"
set +e
exec > >(tee "$SDIR/collect-delta.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

WORK=/tmp/pcorrf-collect-delta
rm -rf "$WORK"
mkdir -p "$WORK/at-5c3e0fa" "$WORK/at-1faccd8"

for pair in "5c3e0fa:at-5c3e0fa" "1faccd8:at-1faccd8"; do
  commit="${pair%%:*}"; dest="${pair##*:}"
  git -C "$REPO" archive "$commit" | tar -x -C "$WORK/$dest"
  n=$(cd "$WORK/$dest" && PYTHONPATH="$WORK/$dest/src" python -m pytest -q --collect-only 2>/dev/null | tail -3 | grep -oE '[0-9]+ tests? collected' | head -1)
  echo "$commit collected: ${n:-<unparsed>}"
done

echo "=== diff between the two trees (should be the readiness doc only) ==="
git -C "$REPO" diff --stat 5c3e0fa 1faccd8
rm -rf "$WORK"
echo "COLLECT DELTA DONE"
