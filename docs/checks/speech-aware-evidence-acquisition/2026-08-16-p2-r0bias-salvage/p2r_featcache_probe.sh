#!/usr/bin/env bash
# Read-only: is the running server the featcache build, is a cache dir armed,
# and what does the cache look like right now?
set -uo pipefail
echo "=== llama-server cmdline ==="
for p in $(pgrep -f llama-server 2>/dev/null); do
  echo "pid $p:"; tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null; echo
  echo "  exe -> $(readlink -f /proc/$p/exe 2>/dev/null)"
done
echo
echo "=== /home/chao/feat-cache ==="
ls -laR /home/chao/feat-cache 2>/dev/null | head -30
echo -n "file count: "; find /home/chao/feat-cache -type f 2>/dev/null | wc -l
echo -n "total size: "; du -sh /home/chao/feat-cache 2>/dev/null | cut -f1
echo "newest 5 by mtime:"
find /home/chao/feat-cache -type f -printf '%TY-%Tm-%Td %TH:%TM:%TS %p\n' 2>/dev/null | sort -r | head -5
echo
echo "=== featcache-related env / server args in the model fragment ==="
grep -rniE "feat.?cache|cache.dir|mmproj" /mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/configs/model/q4km-evid-v3.json 2>/dev/null | head -20
echo
echo "=== current arm server.log: encoding lines so far ==="
d=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r1verify
a=$(ls -t "$d" 2>/dev/null | head -1)
echo "attempt: $a"
echo -n "encoding lines: "; grep -ic "encoding mtmd batch" "$d/$a/SAEA-P2-r1verify.server.log" 2>/dev/null || echo 0
echo -n "MODEL_RESPONSE:  "; grep -c '"MODEL_RESPONSE"' "$d/$a/SAEA-P2-r1verify.trace.jsonl" 2>/dev/null || echo 0
