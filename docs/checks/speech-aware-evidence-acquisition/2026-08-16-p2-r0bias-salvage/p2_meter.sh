#!/usr/bin/env bash
set -uo pipefail
L=/home/chao/SAEA-P2-r0bias-20260816T002101Z.log
echo "=== last 40 lines of driver log ==="
tail -40 "$L"
echo
echo "=== grep meter-ish ==="
grep -inE "meter|budget|30959|395|405|audio" "$L" | tail -30
