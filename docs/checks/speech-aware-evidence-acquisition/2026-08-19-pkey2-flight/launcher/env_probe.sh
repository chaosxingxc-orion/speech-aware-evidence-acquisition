#!/usr/bin/env bash
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pkey2fly/env.sh

echo "=== feature caches ==="
echo "campaign  SAEA_FEAT_CACHE_DIR=$SAEA_FEAT_CACHE_DIR (WARM expected: 63 entries from the P-SLU flights)"
du -sh "$SAEA_FEAT_CACHE_DIR" 2>/dev/null || echo "  (absent)"
echo "  entries: $(find "$SAEA_FEAT_CACHE_DIR" -type f 2>/dev/null | wc -l)"
echo "  dir mtime: $(stat -c '%y' "$SAEA_FEAT_CACHE_DIR" 2>/dev/null)"
echo "legacy /home/chao/feat-cache/q4km (MUST NOT BE TOUCHED)"
du -sh /home/chao/feat-cache/q4km 2>/dev/null || echo "  (absent)"
echo "  entries: $(find /home/chao/feat-cache/q4km -type f 2>/dev/null | wc -l)"
echo "  dir mtime: $(stat -c '%y' /home/chao/feat-cache/q4km 2>/dev/null)"

echo
echo "=== model files (ext4 copies) ==="
ls -l /home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km/

echo
echo "=== orphan llama-server check ==="
pgrep -a llama-server || echo "  none running"

echo
echo "=== existing attempt dirs for this run ==="
ls -1 "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338/" 2>/dev/null || echo "  (no run dir yet)"

echo
echo "=== disk headroom ==="
df -h /home/chao "$SPEECHRL_DATA_DIR" | sed 's/^/  /'
