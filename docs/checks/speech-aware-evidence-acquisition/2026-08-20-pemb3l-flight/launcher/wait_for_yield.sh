#!/usr/bin/env bash
# Wait for the PRECOMP wave-2 generation server (port 8080, meeting repo) to
# yield its GPU. The coordinator set that wave's stop-file; this script only
# OBSERVES -- it never signals, kills, or touches the stop-file.
PORT=8080
for i in $(seq 1 90); do
  if pgrep -af llama-server | grep -q "port $PORT"; then
    if [ $((i % 6)) -eq 1 ]; then
      echo "poll $i: still resident -- $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader)"
    fi
    sleep 10
  else
    echo "port $PORT holder GONE after $i poll(s)"
    break
  fi
done
echo "--- final ---"
pgrep -af llama-server || echo "  (no llama-server resident)"
echo "listening sockets of interest:"
ss -ltn 2>/dev/null | grep -E ":(8080|8093)" || echo "  neither 8080 nor 8093 bound"
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,clocks.sm,pstate --format=csv,noheader
