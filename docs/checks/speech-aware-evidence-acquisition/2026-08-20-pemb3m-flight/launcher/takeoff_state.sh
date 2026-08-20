#!/usr/bin/env bash
# Takeoff state check: prove NOTHING from a predecessor attempt exists.
source "$(dirname "$0")/env.sh"

echo "=== python/venv ==="
which python; python -V
echo
echo "=== data root ==="
ls -la "$SPEECHRL_DATA_DIR" | head -20
echo
echo "=== pemb3m run dir (expect ABSENT) ==="
ls -la "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb3m-388" 2>&1 || true
echo
echo "=== pemb3m derived embeddings (expect ABSENT) ==="
ls -la "$SPEECHRL_DATA_DIR/derived/embeddings/SAEA-PROBE-pemb3m-388" 2>&1 || true
echo
echo "=== pemb3m attempts (expect ABSENT) ==="
ls -la "$SPEECHRL_DATA_DIR/attempts/SAEA-PROBE-pemb3m-388" 2>&1 || true
echo
echo "=== any pemb3m trace anywhere under data root (find, maxdepth 6) ==="
find "$SPEECHRL_DATA_DIR" -maxdepth 6 -name '*pemb3m*' 2>/dev/null || true
echo
echo "=== models dir ==="
ls -la "$SPEECHRL_DATA_DIR/models" 2>&1 | head -40
echo
echo "=== LCO files ==="
ls -la "$SPEECHRL_DATA_DIR/models"/lco* 2>&1 || true
echo
echo "=== qwen3-embedding files ==="
ls -la "$SPEECHRL_DATA_DIR/models"/qwen3-embedding* 2>&1 || true
echo
echo "=== glap / clsp ==="
ls -la "$SPEECHRL_DATA_DIR/models"/glap 2>&1 | head -20 || true
ls -la "$SPEECHRL_DATA_DIR/models"/clsp 2>&1 | head -20 || true
echo
echo "=== pkey2-338 transcript registry ==="
ls -la "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338/attempt-20260819T111032Z-3109e8/transcript-registry.json" 2>&1 || true
sha256sum "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338/attempt-20260819T111032Z-3109e8/transcript-registry.json" 2>&1 || true
echo
echo "=== llama.cpp runtime ==="
ls -la /home/chao/llama.cpp-featcache/build/bin/llama-server 2>&1 || true
echo
echo "=== ports 8093 8094 8080 ==="
ss -ltnp 2>/dev/null | grep -E ':(8080|8093|8094)\b' || echo "none listening"
echo
echo "=== llama-server processes ==="
pgrep -a llama-server || echo "no llama-server running"
echo
echo "=== feat-cache dirs ==="
ls -la /home/chao/feat-cache/ 2>&1 || true
echo
echo "=== nvidia-smi ==="
nvidia-smi --query-gpu=clocks.sm,clocks.max.sm,memory.used,utilization.gpu,pstate --format=csv 2>&1 || true
