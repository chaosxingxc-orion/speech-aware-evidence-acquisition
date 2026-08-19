#!/usr/bin/env bash
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pkey2fly/env.sh

echo "=== git tree (must be clean at 4e8b948 for the whole flight) ==="
cd "$REPO"
git log --oneline -1
git status --porcelain && echo "  (clean)"

echo
echo "=== bytecode hygiene (D3 gate) ==="
echo "PYTHONDONTWRITEBYTECODE=$PYTHONDONTWRITEBYTECODE"
echo "  *.pyc under src/:        $(find "$REPO/src" -name '*.pyc' 2>/dev/null | wc -l)"
echo "  __pycache__ under src/:  $(find "$REPO/src" -type d -name '__pycache__' 2>/dev/null | wc -l)"

echo
echo "=== GPU health ==="
nvidia-smi --query-gpu=name,pstate,clocks.sm,clocks.max.sm,utilization.gpu,memory.used,temperature.gpu,clocks_throttle_reasons.active --format=csv

echo
bash "$SCRATCH/env_probe.sh"
