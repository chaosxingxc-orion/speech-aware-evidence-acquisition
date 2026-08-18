#!/usr/bin/env bash
# Post-flight evidence: server down, featcache untouched, zero encode lines,
# run-dir inventory, tree still clean. No response content is opened.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2cfly
sed -i 's/\r$//' "$SDIR"/postcheck.sh 2>/dev/null || true
source "$SDIR/env.sh"

exec > >(tee "$SCRATCH/postcheck.log") 2>&1
ATTEMPT=attempt-20260818T175018Z-0d3363
RUN_DIR="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2c-120/$ATTEMPT"

echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== llama-server processes (must be none) ==="
pgrep -af llama-server || echo "(none)"
echo "=== feat cache after flight ==="
echo "entries: $(ls -1 "$SAEA_FEAT_CACHE_DIR" | wc -l)"
du -sh "$SAEA_FEAT_CACHE_DIR"
stat -c '%y %n' "$SAEA_FEAT_CACHE_DIR" | tail -1
echo "newest entry mtime:"
newest=$(ls -t "$SAEA_FEAT_CACHE_DIR" | sed -n 1p)
stat -c '%y %n' "$SAEA_FEAT_CACHE_DIR/$newest"
echo "=== encode lines in the server log (expect 0) ==="
grep -ci "encoding" "$RUN_DIR/SAEA-PROBE-a2t-s2c-120.server.log" || true
echo "=== run dir inventory ==="
ls -la "$RUN_DIR"
echo "=== outputs.jsonl row count (wc only, content never opened) ==="
wc -l "$RUN_DIR/outputs.jsonl"
wc -l "$RUN_DIR/responses.jsonl"
echo "=== git tree (must be clean) ==="
dirty=$(git -C "$REPO" status --porcelain | wc -l)
echo "dirty entries: $dirty"
git -C "$REPO" rev-parse HEAD
echo "POSTCHECK DONE"
