#!/bin/bash
# Entry point for the Windows Scheduled Task SAEA-Packets-THINK-GPU when started with `direct_fb_packets_gpu.sh --task --stage test-sample-3010` (successor 3): it owns
# the test-sample Thinking speech-packet GPU window independently of any Claude Code process or interactive wsl.exe session. It adds nothing to the chain:
# every guard and the serving-swap window (stop Instruct, encode the 3,010 sample rows, promote additively, start think-budget-np4, restore on failure) is
# direct_fb_packets_gpu.sh --run --stage test-sample-3010, logged to /home/chao/direct-fb-packets-gpu-test-sample-3010-<UTC>.log. Agents never run this.
REPO=${PACKETS_REPO:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
LOG=/home/chao/direct-fb-packets-gpu-test-sample-3010-$(date -u +%Y%m%dT%H%M%SZ).log
exec > "$LOG" 2>&1
echo "task entry $(date -u +%FT%TZ) HEAD $(git -C "$REPO" rev-parse --short HEAD)"
bash "$REPO/scripts/flights/direct/direct_fb_packets_gpu.sh" --run --stage test-sample-3010
RC=$?
echo "task entry exit $RC $(date -u +%FT%TZ)"
exit $RC
