#!/usr/bin/env bash
set -uo pipefail
date -u +%FT%TZ
C=/home/chao/feat-cache/q4km
echo "=== cache dir $C ==="
ls -la "$C" 2>/dev/null | head -5
echo "file count: $(find "$C" -type f 2>/dev/null | wc -l)"
echo "total size: $(du -sh "$C" 2>/dev/null | cut -f1)"
echo "--- newest 8 by mtime ---"
find "$C" -type f -printf '%T+ %s %p\n' 2>/dev/null | sort -r | head -8
echo "--- oldest 3 ---"
find "$C" -type f -printf '%T+ %s %p\n' 2>/dev/null | sort | head -3
echo "--- files written in the last 20 min (= MISSES being populated) ---"
find "$C" -type f -mmin -20 2>/dev/null | wc -l
echo "--- files written in the last 3 min ---"
find "$C" -type f -mmin -3 2>/dev/null | wc -l
echo
echo "=== current arm server.log: encode vs cache activity ==="
f=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r1verify/attempt-20260816T105836Z-b06529/SAEA-P2-r1verify.server.log
echo "size=$(stat -c %s $f) encoding=$(grep -ci 'encoding' $f) tasks=$(grep -c 'task ' $f)"
tail -6 "$f"
echo
echo "=== r0bias (completed arm) accounting ==="
g=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59/SAEA-P2-r0bias.server.log
echo "encoding_lines=$(grep -ci 'encoding' $g)  n_past/prompt_eval lines=$(grep -c 'prompt eval' $g)"
echo "--- distinct tasks that encoded ---"
grep -oE 'task [0-9]+ \| encoding' "$g" | sort -u | wc -l
echo "--- first + last encoding timestamps ---"
grep -i 'encoding' "$g" | head -1
grep -i 'encoding' "$g" | tail -1
echo
echo "=== driver state right now ==="
pid=$(pgrep -f 'core.driver smoke' | head -1); echo "pid=$pid"
[ -n "${pid:-}" ] && { grep -E '^State' /proc/$pid/status; cat /proc/$pid/wchan; echo; ls -l /proc/$pid/fd 2>/dev/null | grep -oE '/mnt/[^ ]*' | sort -u | head -4; }
nvidia-smi --query-gpu=utilization.gpu,clocks.sm,power.draw --format=csv,noheader
