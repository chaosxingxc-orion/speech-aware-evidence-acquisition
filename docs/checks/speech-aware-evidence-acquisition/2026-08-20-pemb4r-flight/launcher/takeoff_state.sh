#!/usr/bin/env bash
# Takeoff state check: prove NOTHING from a predecessor attempt exists, and that
# every asset this flight needs is present. Zero model contact.
source "$(dirname "$0")/env.sh"

echo "=== python/venv ==="
which python; python -V
echo
echo "=== study HEAD ==="
git -C "$REPO" rev-parse HEAD
git -C "$REPO" status --porcelain || true
echo
echo "=== pemb4r run dir (expect ABSENT) ==="
ls -la "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb4r-4100" 2>&1 || true
echo
echo "=== pemb4r derived embeddings (expect ABSENT) ==="
ls -la "$SPEECHRL_DATA_DIR/derived/embeddings/SAEA-PROBE-pemb4r-4100" 2>&1 || true
echo
echo "=== pemb4r attempts (expect ABSENT) ==="
ls -la "$SPEECHRL_DATA_DIR/attempts/SAEA-PROBE-pemb4r-4100" 2>&1 || true
echo
echo "=== any pemb4r trace anywhere under data root (find, maxdepth 6) ==="
find "$SPEECHRL_DATA_DIR" -maxdepth 6 -name '*pemb4r*' 2>/dev/null || true
echo
echo "=== models dir ==="
ls -la "$SPEECHRL_DATA_DIR/models" 2>&1 | head -50
echo
echo "=== LCO-3B files ==="
ls -la "$SPEECHRL_DATA_DIR/models/lco-embedding-omni-3b-gguf" 2>&1 || true
echo
echo "=== LCO-7B files ==="
ls -la "$SPEECHRL_DATA_DIR/models/lco-embedding-omni-7b-gguf" 2>&1 || true
echo
echo "=== qwen3-embedding files ==="
ls -la "$SPEECHRL_DATA_DIR/models/qwen3-embedding-0.6b-gguf" 2>&1 || true
echo
echo "=== glap ==="
ls -la "$SPEECHRL_DATA_DIR/models/glap" 2>&1 | head -25 || true
echo
echo "=== q4km core (C-DECODE) ==="
ls -la "$SPEECHRL_DATA_DIR/models"/qwen3-omni-30b-a3b-instruct-gguf* 2>&1 | head -20 || true
echo
echo "=== pkey2-338 transcript registry ==="
ls -la "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338/attempt-20260819T111032Z-3109e8/transcript-registry.json" 2>&1 || true
sha256sum "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338/attempt-20260819T111032Z-3109e8/transcript-registry.json" 2>&1 || true
echo
echo "=== llama.cpp runtime ==="
ls -la /home/chao/llama.cpp-featcache/build/bin/llama-server 2>&1 || true
echo
echo "=== ports 8080 8093 8094 8095 ==="
ss -ltnp 2>/dev/null | grep -E ':(8080|8093|8094|8095)\b' || echo "none listening"
echo
echo "=== llama-server processes ==="
pgrep -a llama-server || echo "no llama-server running"
echo
echo "=== feat-cache dirs ==="
ls -la /home/chao/feat-cache/ 2>&1 || true
du -sh /home/chao/feat-cache/slurp-lco3b 2>&1 || true
echo
echo "=== disk free ==="
df -h /home/chao "$SPEECHRL_DATA_DIR" 2>&1 || true
echo
echo "=== nvidia-smi ==="
nvidia-smi --query-gpu=clocks.sm,clocks.max.sm,memory.used,memory.total,utilization.gpu,pstate,temperature.gpu --format=csv 2>&1 || true
nvidia-smi 2>&1 | tail -15 || true
