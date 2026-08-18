#!/usr/bin/env bash
# Operational health only: request progress, GPU clocks, feature-cache entry count.
# Never prints response text.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2cfly/env.sh
echo "=== gpu ==="
bash "$SCRATCH/gpu_health.sh"
echo "=== feat cache ==="
echo "entries: $(ls -1 "$SAEA_FEAT_CACHE_DIR" 2>/dev/null | wc -l)"
echo "=== flight tail (health lines only) ==="
tail -n 6 "$SCRATCH/flight.log" 2>/dev/null || echo "(no flight log yet)"
