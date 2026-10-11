#!/bin/bash
# Entry point for the Windows Scheduled Task SAEA-Packets-THINK-GPU (started by `direct_fb_packets_gpu.sh --task` through
# scripts/flights/batch/saea_task.ps1): it owns the Thinking speech-packet GPU window independently of any Claude Code process or
# interactive wsl.exe session (a detached WSL job dies with its session; a scheduled task does not). It adds nothing to the chain: every
# guard, the serving-swap window (stop Instruct, 4-row smoke, Fold B, start Thinking, restore on failure) is
# direct_fb_packets_gpu.sh --run --stage all, logged to /home/chao/direct-fb-packets-gpu-<UTC>.log. Agents never run this.
REPO=${PACKETS_REPO:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
LOG=/home/chao/direct-fb-packets-gpu-$(date -u +%Y%m%dT%H%M%SZ).log
exec > "$LOG" 2>&1
echo "task entry $(date -u +%FT%TZ) HEAD $(git -C "$REPO" rev-parse --short HEAD)"
bash "$REPO/scripts/flights/direct/direct_fb_packets_gpu.sh" --run --stage all
RC=$?
echo "task entry exit $RC $(date -u +%FT%TZ)"
exit $RC
