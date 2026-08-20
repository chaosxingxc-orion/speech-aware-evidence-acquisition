#!/usr/bin/env bash
PID=$(pgrep -f launch_pemb3l_flight.py | head -1)
[ -z "$PID" ] && { echo "launcher GONE"; exit 0; }
a=$(grep '^rchar' "/proc/$PID/io" | awk '{print $2}')
sleep 60
b=$(grep '^rchar' "/proc/$PID/io" 2>/dev/null | awk '{print $2}')
[ -z "$b" ] && { echo "launcher finished during the sample"; exit 0; }
d=$((b - a))
echo "rchar start : $a"
echo "rchar end   : $b"
echo "delta/60s   : $d bytes ($((d / 1024 / 1024)) MiB/min)"
echo "total SLURP devel media bytes (for an ETA):"
du -sb /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/datasets/slurp/audio 2>/dev/null | sed 's/^/  /' || echo "  (audio dir name differs; skipping)"
