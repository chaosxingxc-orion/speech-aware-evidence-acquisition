#!/bin/bash
# SUPERSEDED (CPU chain; the live one is direct_fb_packets_gpu_task_entry.sh).
# Entry point for the Windows Scheduled Task SAEA-Packets-THINK (started by `direct_fb_packets.sh --task` through
# scripts/flights/batch/saea_task.ps1): it owns the Thinking speech-packet preparation chain independently of any Claude Code process
# or interactive wsl.exe session (a detached WSL job dies with its session; a scheduled task does not). It adds nothing to the chain:
# every guard, both attempts and the sidecar-gone wait are direct_fb_packets.sh --run --stage all, logged to
# /home/chao/direct-fb-packets-<UTC>.log. Agents never run this.
REPO=${PACKETS_REPO:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
LOG=/home/chao/direct-fb-packets-$(date -u +%Y%m%dT%H%M%SZ).log
exec > "$LOG" 2>&1
echo "task entry $(date -u +%FT%TZ) HEAD $(git -C "$REPO" rev-parse --short HEAD)"
bash "$REPO/scripts/flights/direct/direct_fb_packets.sh" --allow-cpu --run --stage all
RC=$?
echo "task entry exit $RC $(date -u +%FT%TZ)"
exit $RC
