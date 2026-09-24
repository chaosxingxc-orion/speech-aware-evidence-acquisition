#!/bin/bash
# GPU warm-up (NOT a model contact): loops the 9-s fp16 matmul ramp test (gpu_ramp_test.sh) up to six times until the card
# reports >= 30 TFLOP/s, so a launch that follows an idle gap does not trip the driver's preflight (memory gpu-pstate-stuck-wsl:
# after ~10 min idle the first load sits at ~7 W / 100 % "util" / ~10 TFLOP/s and clears itself on the next burst). Recreated
# 2026-09-24 in the repo after the scratchpad copy was lost (the GEPA chain STOPPED cold at 9.8 TFLOP/s between two steps).
# Prints the last measured throughput; exit 0 when the threshold was reached, 3 otherwise.
SP=$(cd "$(dirname "$0")" && pwd)
for i in 1 2 3 4 5 6; do
  ramp=$(bash "$SP/gpu_ramp_test.sh" 2>/dev/null | grep -o "[0-9.]* TFLOP/s" | grep -o "^[0-9.]*")
  echo "gpu warm pass $i: ${ramp:-none} TFLOP/s"
  [ -n "$ramp" ] && [ "$(/home/chao/.venvs/speechrl/bin/python -c "print(int(float('$ramp') >= 30))")" = "1" ] && exit 0
  sleep 5
done
exit 3
