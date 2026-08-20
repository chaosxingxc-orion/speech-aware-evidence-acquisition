#!/usr/bin/env bash
# Tear down every resident llama-server and prove the GPU is released.
# An embedding-mode server can never coexist with a generation-mode one
# (rails.embedding_client.GENERATION_COEXISTENCE_NOTE), so this runs between
# the P-FEW generation flight and the two P-EMB embedding flights, and again
# at the end of the session.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri2/env.sh
LOG="${1:-$TRI/teardown.log}"
exec > >(tee -a "$LOG") 2>&1
echo "=== teardown start: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "resident before:"
pgrep -af llama-server || echo "  (none)"
pkill -TERM -f 'llama.cpp-featcache/build/bin/llama-server' || true
for i in $(seq 1 30); do
  if ! pgrep -f 'llama.cpp-featcache/build/bin/llama-server' >/dev/null; then break; fi
  sleep 1
done
if pgrep -f 'llama.cpp-featcache/build/bin/llama-server' >/dev/null; then
  echo "still resident after SIGTERM; escalating to SIGKILL"
  pkill -KILL -f 'llama.cpp-featcache/build/bin/llama-server' || true
  sleep 3
fi
echo "resident after:"
pgrep -af llama-server || echo "  (none)"
echo "ports 8080/8091:"
ss -ltnp 2>/dev/null | grep -E ':(8080|8091)' || echo "  (neither bound)"
echo "GPU:"
nvidia-smi --query-gpu=pstate,clocks.sm,utilization.gpu,memory.used,temperature.gpu --format=csv
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
echo "=== teardown end: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
