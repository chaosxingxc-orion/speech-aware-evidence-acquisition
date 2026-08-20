#!/usr/bin/env bash
echo "=== preflight python processes ==="
ps -eo pid,etime,pcpu,pmem,stat,cmd --sort=-pcpu | grep -E "preflight|[p]ython -u" | grep -v grep
echo
echo "=== load ==="
cat /proc/loadavg
echo
echo "=== other repos' python (competing sessions) ==="
ps -eo pid,etime,pcpu,cmd --sort=-pcpu | sed -n '2,12p'
echo
echo "=== /mnt/e io check (time a small read) ==="
time ls /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/datasets/slurp >/dev/null
