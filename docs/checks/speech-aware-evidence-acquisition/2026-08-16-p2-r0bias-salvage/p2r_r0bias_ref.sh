#!/usr/bin/env bash
# Read-only reference numbers from the sealed r0bias attempt: its own phase
# split and encoding count, as the cold/warm baseline for the resume arms.
set -uo pipefail
A=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59
SL="$A/SAEA-P2-r0bias.server.log"
rel2sec () { awk -F. '{printf "%.1f", $1*60 + $2 + $3/1000}' <<< "$1"; }
first=$(grep -E 'print_timing' "$SL" | grep -oE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)
last=$(grep -oE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' "$SL" | tail -1)
echo "r0bias server.log first print_timing rel: $first  -> $(rel2sec "$first") s"
echo "r0bias server.log last line       rel: $last   -> $(rel2sec "$last") s"
echo -n "encoding mtmd batch lines: "; grep -ic "encoding mtmd batch" "$SL"
echo -n "print_timing lines:        "; grep -c "print_timing" "$SL"
echo -n "MODEL_RESPONSE records:    "; grep -c '"MODEL_RESPONSE"' "$A/SAEA-P2-r0bias.trace.jsonl"
echo
echo "arm-start line from the 00:21Z detached log:"
grep -E "=====" /home/chao/p2-rladder-detached-20260816T002101Z.log 2>/dev/null | head -4
echo
echo "exit/elapsed lines:"
grep -E "exit=|elapsed" /home/chao/p2-rladder-detached-20260816T002101Z.log 2>/dev/null | head -4
