#!/usr/bin/env bash
# P-CORR-F session-start environment probe. Model-free.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf
sed -i 's/\r$//' "$SDIR"/*.sh "$SDIR"/*.py 2>/dev/null || true
source "$SDIR/env.sh"
exec > >(tee "$SCRATCH/session-precheck.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== git ==="
git -C "$REPO" rev-parse HEAD
echo "dirty entries: $(git -C "$REPO" status --porcelain | wc -l)"
git -C "$REPO" log --oneline -1
echo "=== python ==="
which python && python --version
echo "=== pyc under src (D3 gate) ==="
echo "  *.pyc:       $(find "$REPO/src" -name '*.pyc' 2>/dev/null | wc -l)"
echo "  __pycache__: $(find "$REPO/src" -type d -name '__pycache__' 2>/dev/null | wc -l)"
echo "  scoring pkg: $(find "$REPO/src/speech_aware_evidence_acquisition/scoring" -name '__pycache__' -o -name '*.pyc' 2>/dev/null | wc -l)"
echo "=== orphan llama-server ==="
pgrep -af llama-server || echo "  (none running)"
echo "=== ports 8080/8081 ==="
(ss -ltnp 2>/dev/null | grep -E ':(8080|8081)\b') || echo "  (free)"
echo "=== GPU ==="
nvidia-smi --query-gpu=name,pstate,clocks.sm,clocks.max.sm,utilization.gpu,memory.used,temperature.gpu,clocks_throttle_reasons.active --format=csv
echo "=== feature caches ==="
for d in /home/chao/feat-cache/slurp-q4km /home/chao/feat-cache/audio2tool-q4km /home/chao/feat-cache/q4km; do
  echo "  $d: $(find "$d" -type f 2>/dev/null | wc -l) entries, $(du -sh "$d" 2>/dev/null | cut -f1), mtime $(stat -c '%y' "$d" 2>/dev/null)"
done
echo "=== model files ==="
ls -l /home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km/
echo "=== consumed P-SLU A0 source attempt ==="
ls -la "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/attempt-20260818T010218Z-4c97cb/" | head -20
echo "=== existing P-CORR-F run/attempt dirs (expect ABSENT) ==="
echo "  runs/SAEA-PROBE-pcorrf-240: $(ls -1 "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pcorrf-240" 2>/dev/null | tr '\n' ' ')"
echo "  attempts/SAEA-PROBE-pcorrf-240: $(ls -1 "$SPEECHRL_DATA_DIR/attempts/SAEA-PROBE-pcorrf-240" 2>/dev/null | tr '\n' ' ')"
echo "=== disk ==="
df -h /home/chao "$SPEECHRL_DATA_DIR" | sed 's/^/  /'
echo "PRECHECK DONE"
