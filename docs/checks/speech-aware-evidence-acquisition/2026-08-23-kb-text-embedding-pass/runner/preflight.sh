#!/usr/bin/env bash
source "$(dirname "$0")/env.sh"

echo "=== takeoff state ==="
echo "-- ports 8080 / 8082 --"
ss -ltnp 2>/dev/null | grep -E ':(8080|8082)\b' || echo "none listening"
echo "-- llama-server processes --"
pgrep -a llama-server || echo "no llama-server running"
echo "-- prior attempts for this run id (expect ABSENT) --"
ls -la "$SPEECHRL_DATA_DIR/runs/SAEA-SN-TOOL-KB-TEXT-EMB-PASS" 2>&1 || true
echo "-- existing vectors in the snapshot dir (expect ABSENT) --"
ls -la "$SPEECHRL_DATA_DIR/knowledge/slurp/saea-kb-distmodel-v1/size-full/"
echo "-- host --"
nproc; uptime; free -g | head -2
echo "-- gpu --"
nvidia-smi --query-gpu=clocks.sm,memory.used,utilization.gpu --format=csv 2>&1 || true

echo
echo "=== preflight (zero tool contacts) ==="
python "$SCRATCH/run_kb_text_embedding_pass.py" --preflight-only
rm -rf "$SCRATCH/__pycache__"
