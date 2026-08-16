#!/usr/bin/env bash
set -uo pipefail
date -u +%FT%TZ
d=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r1verify
a=$(ls -t "$d" | head -1); echo "attempt=$a"
echo "=== server.log tail ==="
tail -15 "$d/$a/SAEA-P2-r1verify.server.log" 2>/dev/null
echo "=== arm log tail ==="
tail -15 /home/chao/SAEA-P2-r1verify-20260816T105824Z.log 2>/dev/null
echo "=== python driver: what is it doing ==="
pid=$(pgrep -f "python.*run_experiment|python -m speech_aware" | head -1)
echo "driver pid=$pid"
[ -n "${pid:-}" ] && cat /proc/$pid/status 2>/dev/null | grep -E '^(Threads|VmRSS|State)' 
[ -n "${pid:-}" ] && ls -l /proc/$pid/cwd 2>/dev/null
[ -n "${pid:-}" ] && head -3 /proc/$pid/wchan 2>/dev/null; echo
echo "=== open files of driver (top 8 real paths) ==="
[ -n "${pid:-}" ] && ls -l /proc/$pid/fd 2>/dev/null | grep -oE '/(mnt|home)/[^ ]*' | sort -u | head -8
echo "=== all python procs ==="
ps -eo pid,pcpu,etime,args --sort=-pcpu | grep -i python | grep -v grep | head -5
echo "=== curl the server health/slots ==="
curl -s -m 5 http://127.0.0.1:8080/health || echo "no health"
echo
curl -s -m 5 http://127.0.0.1:8080/slots 2>/dev/null | head -c 400 || echo "no slots ep"
echo
echo "=== disk io on E: (9p/drvfs) ==="
cat /proc/loadavg
