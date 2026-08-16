#!/usr/bin/env bash
# P2-resume instrumentation, RESUMABLE and READ-ONLY.
# Per arm, once: (a) exact first-MODEL_RESPONSE wall clock (phase split),
# (b) a single 60 s GPU duty-cycle window at 2 s, (c) featcache hit/miss.
# Appends to a scratch state file; safe to run in bounded chunks.
set -uo pipefail
S=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/95b8e5b0-424d-494b-9d7b-4f101bc186be/scratchpad
STATE="$S/p2r_instr.state"
touch "$STATE"
D=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs
FC=/home/chao/feat-cache/q4km
DUR="${1:-2700}"
DEADLINE=$(( $(date +%s) + DUR ))
RUNS="SAEA-P2-r1verify SAEA-P2-r2draft SAEA-P2-r0wrong SAEA-P2-r1wrong"

have () { grep -q "^$1 $2\b" "$STATE" 2>/dev/null; }

# relative server.log stamp "MMM.SS.mmm.uuu" -> seconds (float)
rel2sec () { awk -F. '{printf "%.3f", $1*60 + $2 + $3/1000}' <<< "$1"; }

newest_attempt () {
  ls -t "$D/$1" 2>/dev/null | grep '^attempt-2026081[6-9]T[1-2]' | head -1
}

while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  for run in $RUNS; do
    a=$(newest_attempt "$run"); [ -z "$a" ] && continue
    dir="$D/$run/$a"
    tr="$dir/$run.trace.jsonl"; sl="$dir/$run.server.log"
    n=$(grep -c '"MODEL_RESPONSE"' "$tr" 2>/dev/null); n=${n:-0}
    [ "$n" -eq 0 ] 2>/dev/null && continue

    # (a) first response wall clock, anchored by mapping the server.log's
    #     relative clock onto absolute time at this instant.
    if ! have FIRST_RESP "$run"; then
      now=$(date +%s)
      last=$(grep -oE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' "$sl" 2>/dev/null | tail -1)
      first=$(grep -E 'print_timing' "$sl" 2>/dev/null | grep -oE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)
      if [ -n "$last" ] && [ -n "$first" ]; then
        ls_=$(rel2sec "$last"); fs=$(rel2sec "$first")
        epoch0=$(awk -v n="$now" -v l="$ls_" 'BEGIN{printf "%d", n - l}')
        fr=$(awk -v e="$epoch0" -v f="$fs" 'BEGIN{printf "%d", e + f}')
        echo "FIRST_RESP $run $(date -u -d @"$fr" +%FT%TZ) attempt=$a server_start=$(date -u -d @"$epoch0" +%FT%TZ) at_n=$n" >> "$STATE"
      fi
    fi

    # (b) one 60 s duty-cycle window per arm, mid-arm
    if [ "$n" -ge 25 ] && ! have DUTY "$run"; then
      tot=0; zero=0; cnt=0; clk=0; pw=0
      for _ in $(seq 1 30); do
        r=$(nvidia-smi --query-gpu=utilization.gpu,clocks.sm,power.draw --format=csv,noheader,nounits 2>/dev/null | head -1)
        u=$(cut -d, -f1 <<< "$r" | tr -d ' '); c=$(cut -d, -f2 <<< "$r" | tr -d ' '); p=$(cut -d, -f3 <<< "$r" | tr -d ' ')
        case "$u" in ''|*[!0-9]*) ;; *)
          tot=$((tot+u)); cnt=$((cnt+1)); [ "$u" -eq 0 ] && zero=$((zero+1))
          clk=$((clk+${c%%.*})); pw=$(awk -v a="$pw" -v b="$p" 'BEGIN{print a+b}') ;;
        esac
        sleep 2
      done
      if [ "$cnt" -gt 0 ]; then
        echo "DUTY $run mean_util=$((tot/cnt))% zero_frac=$(awk -v z="$zero" -v c="$cnt" 'BEGIN{printf "%.2f", z/c}') mean_clk=$((clk/cnt))MHz mean_pw=$(awk -v p="$pw" -v c="$cnt" 'BEGIN{printf "%.1f", p/c}')W samples=$cnt at_n=$n" >> "$STATE"
      fi
    fi

    # (c) featcache hit/miss evidence
    if [ "$n" -ge 25 ] && ! have FCACHE "$run"; then
      enc=$(grep -ic "encoding mtmd batch" "$sl" 2>/dev/null); enc=${enc:-0}
      fcn=$(find "$FC" -type f 2>/dev/null | wc -l)
      fcnew=$(find "$FC" -type f -printf '%TY-%Tm-%TdT%TH:%TM:%TS\n' 2>/dev/null | sort -r | head -1 | cut -c1-19)
      echo "FCACHE $run encoding_lines=$enc cache_files=$fcn cache_newest_local=$fcnew at_n=$n" >> "$STATE"
    fi
  done
  sleep 20
done
echo "=== STATE $(date -u +%FT%TZ) ==="
cat "$STATE"
