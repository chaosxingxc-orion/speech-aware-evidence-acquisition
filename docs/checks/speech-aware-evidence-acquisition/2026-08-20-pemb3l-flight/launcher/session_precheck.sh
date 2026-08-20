#!/usr/bin/env bash
# P-EMB-3L session-start environment probe. Model-free: spawns nothing, loads
# no model, embeds nothing.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pemb3l/env.sh
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
echo "  under scoring package: $(find "$REPO/src/speech_aware_evidence_acquisition/scoring" -name '__pycache__' -o -name '*.pyc' 2>/dev/null | wc -l)"
echo "=== resident llama-server (wave-2 PRECOMP holder must have yielded) ==="
pgrep -af llama-server || echo "  (none running)"
echo "=== listening ports 8080 (generation) / 8093 (this flight) ==="
ss -ltnp 2>/dev/null | grep -E ':(8080|8093)' || echo "  (neither bound)"
echo "=== GPU ==="
nvidia-smi --query-gpu=name,pstate,clocks.sm,clocks.max.sm,utilization.gpu,memory.used,memory.total,temperature.gpu,clocks_throttle_reasons.active --format=csv
echo "=== GPU compute processes ==="
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
echo "=== feature caches ==="
for d in /home/chao/feat-cache/slurp-q4km /home/chao/feat-cache/audio2tool-q4km /home/chao/feat-cache/q4km; do
  echo "  $d: $(find "$d" -type f 2>/dev/null | wc -l) entries, $(du -sh "$d" 2>/dev/null | cut -f1)"
done
echo "=== model files (ext4) ==="
ls -l /home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km/
echo "=== llama-server binary ==="
sha256sum /home/chao/llama.cpp-featcache/build/bin/llama-server
echo "=== existing run/attempt dirs for this probe (expect absent) ==="
echo "  runs/SAEA-PROBE-pemb3l-234:     $(ls -1 "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb3l-234" 2>/dev/null | tr '\n' ' ')"
echo "  attempts/SAEA-PROBE-pemb3l-234: $(ls -1 "$SPEECHRL_DATA_DIR/attempts/SAEA-PROBE-pemb3l-234" 2>/dev/null | tr '\n' ' ')"
echo "=== derived/embeddings/SAEA-PROBE-pemb3l-234 (expect absent) ==="
ls -la "$SPEECHRL_DATA_DIR/derived/embeddings/SAEA-PROBE-pemb3l-234" 2>/dev/null || echo "  (absent)"
echo "=== derived/embeddings siblings (consumed probes, must stay untouched) ==="
ls -1 "$SPEECHRL_DATA_DIR/derived/embeddings" 2>/dev/null | sed 's/^/  /'
echo "=== disk ==="
df -h /home/chao "$SPEECHRL_DATA_DIR" | sed 's/^/  /'
echo "PRECHECK DONE"
