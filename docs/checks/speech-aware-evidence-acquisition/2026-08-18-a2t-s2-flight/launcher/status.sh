#!/usr/bin/env bash
# Operational status of a Stage-2 flight attempt. Never opens outputs.jsonl content.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2fly2/env.sh
ATTEMPT="${1:?usage: status.sh <attempt-id>}"
D="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2-120/$ATTEMPT"
echo "run dir: $D"
ls -la "$D" 2>/dev/null || echo "(run dir absent)"
if [ -f "$D/responses.jsonl" ]; then
  echo "responses.jsonl rows: $(wc -l < "$D/responses.jsonl")"
  echo "rows per arm:"
  grep -o '"arm": "[^"]*"' "$D/responses.jsonl" | sort | uniq -c
fi
if [ -f "$D/outputs.jsonl" ]; then
  echo "outputs.jsonl rows: $(wc -l < "$D/outputs.jsonl")"
  echo "outputs rows per arm:"
  grep -o '"arm": "[^"]*"' "$D/outputs.jsonl" | sort | uniq -c
fi
SL="$D/SAEA-PROBE-a2t-s2-120.server.log"
if [ -f "$SL" ]; then
  echo "server log: $(wc -l < "$SL") lines; encoding lines: $(grep -ci 'encoding' "$SL" || true)"
fi
echo "featcache entries: $(ls -1 "$SAEA_FEAT_CACHE_DIR" | wc -l)  size: $(du -sh "$SAEA_FEAT_CACHE_DIR" | cut -f1)"
nvidia-smi --query-gpu=clocks.sm,temperature.gpu,power.draw,utilization.gpu,memory.used,pstate --format=csv,noheader
