#!/usr/bin/env bash
set -uo pipefail
date -u +%FT%TZ
echo "=== procs ==="
pgrep -af 'run_arm_sequence|llama-server' || echo "none alive"
echo "=== runs dir ==="
d=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs
for run in SAEA-P2-r0bias SAEA-P2-r1verify SAEA-P2-r2draft SAEA-P2-r0wrong SAEA-P2-r1wrong; do
  echo "--- $run ---"
  ls -1t "$d/$run" 2>/dev/null || { echo "  (no run dir)"; continue; }
done
echo "=== r0bias manifest key fields ==="
a=$(ls -1t "$d/SAEA-P2-r0bias" 2>/dev/null | head -1)
echo "attempt=$a"
m="$d/SAEA-P2-r0bias/$a/SAEA-P2-r0bias.run-manifest.json"
ls -la "$d/SAEA-P2-r0bias/$a/" 2>/dev/null
python3 - "$m" <<'PY'
import json,sys
try:
    d=json.load(open(sys.argv[1]))
except Exception as e:
    print("manifest read fail:",e); raise SystemExit
for k in ("status","attempt_id","study_commit","failure_reason","metered_model_calls","metered_speech_audio_seconds","started_at","ended_at"):
    v=d.get(k)
    if isinstance(v,str) and len(v)>300: v=v[:300]+"..."
    print(f"{k}: {v}")
PY
echo "=== detached logs ==="
ls -la /home/chao/p2-rladder-detached-*.log 2>/dev/null
ls -la /home/chao/SAEA-P2-*.log 2>/dev/null | tail -10
