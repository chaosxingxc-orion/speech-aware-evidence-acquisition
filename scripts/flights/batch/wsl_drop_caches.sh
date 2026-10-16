#!/usr/bin/env bash
# Drop the WSL VM's CLEAN page cache so Windows gets its memory back during long flights (coordinator, 2026-10-16).
# Why: `.wslconfig` autoMemoryReclaim=dropcache only reclaims when the VM idles; a 20-30 h flight never idles, so the GGUF mmap
# (about 17 GB), packets, traces and checkpoints fill the 44 GB VM cap, Windows compresses vmmem pages (10 GB observed) and the
# flight stalls (successor-3: 0 rows from 05:15Z to 06:40Z on 2026-10-16). The model weights live in VRAM, packets are re-read per
# row, so dropping clean cache costs only some disk re-reads. Registered as the repeating Windows task SAEA-WSL-DropCache
# (saea_task.ps1 -RepeatMinutes 30), which runs this script as root inside the distro. Dirty pages are synced first; nothing is killed.
set -u
LOG=/home/chao/wsl-drop-caches.log
before=$(awk '/^MemAvailable/ {printf "%.1f", $2/1048576}' /proc/meminfo); cached=$(awk '/^Cached:/ {printf "%.1f", $2/1048576}' /proc/meminfo)
sync; echo 1 > /proc/sys/vm/drop_caches || { echo "$(date -u +%FT%TZ) drop refused (not root?)" >> "$LOG"; exit 1; }
after=$(awk '/^MemAvailable/ {printf "%.1f", $2/1048576}' /proc/meminfo)
echo "$(date -u +%FT%TZ) dropped clean cache: cached ${cached} GiB; MemAvailable ${before} -> ${after} GiB" >> "$LOG"
tail -n 1 "$LOG"
