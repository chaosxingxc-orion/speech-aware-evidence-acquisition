#!/usr/bin/env bash
# Model-free environment precheck for the Stage-2c flight. No core contact.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2cfly
sed -i 's/\r$//' "$SDIR"/*.sh "$SDIR"/*.py 2>/dev/null || true
source "$SDIR/env.sh"

exec > >(tee "$SCRATCH/precheck.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== llama-server processes ==="
pgrep -af llama-server || echo "(none)"
echo "=== s2c run dir ==="
ls -la "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2c-120" 2>/dev/null || echo "(absent -- fresh start confirmed)"
echo "=== stage2 arm plan ==="
AP="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2-120/attempt-20260818T124955Z-84b944/SAEA-PROBE-a2t-s2-120.arm-plan.json"
ls -la "$AP" && sha256sum "$AP"
echo "=== server binary hash (receipt pins 097c96ec...) ==="
sha256sum /home/chao/llama.cpp-featcache/build/bin/llama-server
echo "=== GGUF hashes per the s2b session receipt ==="
sha256sum /home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km/Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf &
P1=$!
sha256sum /home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km/mmproj-Qwen3-Omni-30B-A3B-Instruct-bf16.gguf
wait $P1
echo "=== feat cache ==="
echo "entries: $(ls -1 "$SAEA_FEAT_CACHE_DIR" | wc -l)"
du -sh "$SAEA_FEAT_CACHE_DIR"
stat -c '%y %n' "$SAEA_FEAT_CACHE_DIR" | tail -1
echo "=== python ==="
which python && python --version
echo "=== git (via WSL view) ==="
git -C "$REPO" status --porcelain | head -5
git -C "$REPO" rev-parse HEAD
echo "=== pyc under src ==="
find "$REPO/src" -name '*.pyc' | wc -l
echo "PRECHECK DONE"
