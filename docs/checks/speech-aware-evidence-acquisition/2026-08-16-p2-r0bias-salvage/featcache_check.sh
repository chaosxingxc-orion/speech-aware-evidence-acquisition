#!/usr/bin/env bash
set -uo pipefail
date -u +%FT%TZ
echo "=== featcache build: where does it put the cache? ==="
grep -rioE '(featcache|feat_cache|FEATURE_CACHE)[A-Za-z_]*' /home/chao/llama.cpp-featcache/tools/mtmd/*.cpp /home/chao/llama.cpp-featcache/tools/server/*.cpp 2>/dev/null | sort | uniq -c | sort -rn | head -12
echo "--- env var names in the patch ---"
grep -rhoE 'getenv\("[A-Z_]+"\)' /home/chao/llama.cpp-featcache/tools 2>/dev/null | sort -u | head -12
echo
echo "=== candidate cache dirs ==="
for p in /home/chao/featcache /home/chao/.cache/llama-featcache /home/chao/llama.cpp-featcache/featcache /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/cache /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/derived/featcache; do
  [ -e "$p" ] && { echo "FOUND $p"; ls -la "$p" | head -8; du -sh "$p" 2>/dev/null; }
done
echo "--- any dir named *featcache* / *feat-cache* under home and data ---"
find /home/chao -maxdepth 3 -iname '*featcache*' -o -maxdepth 3 -iname '*feat_cache*' 2>/dev/null | head
find /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data -maxdepth 3 -iname '*featcache*' 2>/dev/null | head
echo
echo "=== 'encoding' lines: current arm vs the aborted r0bias arm ==="
R=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs
for f in "$R/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59/SAEA-P2-r0bias.server.log" "$R/SAEA-P2-r1verify/attempt-20260816T105836Z-b06529/SAEA-P2-r1verify.server.log"; do
  [ -f "$f" ] || { echo "MISSING $f"; continue; }
  n=$(grep -ci 'encoding' "$f" 2>/dev/null || echo 0)
  m=$(grep -ci 'mtmd\|audio\|whisper' "$f" 2>/dev/null || echo 0)
  echo "$(basename $(dirname $f)) : encoding_lines=$n audio_lines=$m size=$(stat -c %s "$f")"
  grep -i 'encoding' "$f" 2>/dev/null | head -3
done
echo
echo "=== server launch flags (cache-related) ==="
tr '\0' ' ' < /proc/906/cmdline 2>/dev/null; echo
echo "=== server env (cache-related) ==="
tr '\0' '\n' < /proc/906/environ 2>/dev/null | grep -iE 'cache|feat|SPEECHRL' | head
