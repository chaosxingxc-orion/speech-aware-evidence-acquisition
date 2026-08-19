#!/usr/bin/env bash
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri/env.sh
exec > >(tee "$TRI/session-precheck.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== git ==="
git -C "$REPO" rev-parse HEAD
echo "dirty entries: $(git -C "$REPO" status --porcelain | wc -l)"
echo "=== python ==="
which python && python --version
echo "=== pyc under src (D3 gate) ==="
echo "  *.pyc:       $(find "$REPO/src" -name '*.pyc' 2>/dev/null | wc -l)"
echo "  __pycache__: $(find "$REPO/src" -type d -name '__pycache__' 2>/dev/null | wc -l)"
echo "=== orphan llama-server ==="
pgrep -af llama-server || echo "  (none running)"
echo "=== GPU ==="
nvidia-smi --query-gpu=name,pstate,clocks.sm,clocks.max.sm,utilization.gpu,memory.used,temperature.gpu,clocks_throttle_reasons.active --format=csv
echo "=== feature caches ==="
for d in /home/chao/feat-cache/slurp-q4km /home/chao/feat-cache/audio2tool-q4km /home/chao/feat-cache/q4km; do
  echo "  $d: $(find "$d" -type f 2>/dev/null | wc -l) entries, $(du -sh "$d" 2>/dev/null | cut -f1)"
done
echo "=== model files ==="
ls -l /home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km/
echo "=== consumed source attempts ==="
ls -la "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/attempt-20260818T010218Z-4c97cb/" | head -20
echo "=== existing run dirs for the three probes (expect absent) ==="
for r in SAEA-PROBE-ptrap-120 SAEA-PROBE-a2t-abst-44 SAEA-PROBE-a2t-pop-194; do
  echo "  runs/$r: $(ls -1 "$SPEECHRL_DATA_DIR/runs/$r" 2>/dev/null | tr '\n' ' ')${_:-}"
  echo "  attempts/$r: $(ls -1 "$SPEECHRL_DATA_DIR/attempts/$r" 2>/dev/null | tr '\n' ' ')"
done
echo "=== disk ==="
df -h /home/chao "$SPEECHRL_DATA_DIR" | sed 's/^/  /'
echo "PRECHECK DONE"
