#!/usr/bin/env bash
# Operational latency comparison ONLY (index + seconds). No response content.
S=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad

stats() {
  awk -v lo="$2" -v hi="$3" '
    / req [0-9]{4} ok /{
      idx = $3 + 0
      lat = $5 + 0
      if (idx >= lo && idx <= hi) { n++; s += lat }
    }
    END { if (n) printf "  n=%3d  mean=%.2fs\n", n, s/n; else print "  (no rows)" }
  ' "$1"
}

echo "T0 pass (reqs 1-60):"
echo -n "  predecessor:"; stats "$S/pkeyfly/flight.log" 1 60
echo -n "  pkey2      :"; stats "$S/pkey2fly/flight.log" 1 60
echo
echo "AUD-NOSUP pass (reqs 61-120):"
echo -n "  predecessor:"; stats "$S/pkeyfly/flight.log" 61 120
echo -n "  pkey2      :"; stats "$S/pkey2fly/flight.log" 61 120
echo
echo "AUD-SUP pass so far (reqs 121-183):"
echo -n "  predecessor:"; stats "$S/pkeyfly/flight.log" 121 183
echo -n "  pkey2      :"; stats "$S/pkey2fly/flight.log" 121 183
echo
echo "pkey2 progress: $(grep -cE ' req [0-9]{4} ok ' "$S/pkey2fly/flight.log") requests ok, $(grep -cE ' req [0-9]{4} FAILED' "$S/pkey2fly/flight.log") failed"
nvidia-smi --query-gpu=pstate,clocks.sm,utilization.gpu,power.draw,clocks_throttle_reasons.active --format=csv,noheader
