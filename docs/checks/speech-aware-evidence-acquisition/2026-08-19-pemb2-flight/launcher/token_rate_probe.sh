#!/usr/bin/env bash
# Operational feasibility probe, model-free: read the Run A embedding server's
# OWN log for per-request token counts and derive the audio token rate, so Run B
# (whose longest clip is 35.71 s) can be judged against the server's forced
# 512-token pooled budget BEFORE 552 registered contacts are spent.
#
# This reads llama-server's operational log only -- never outputs.jsonl, never a
# vector, never a result.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri2/pemb
source "$SDIR/env.sh"
SL="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb1-78/attempt-20260819T235907Z-49567c/SAEA-PROBE-pemb1-78.server.log"
exec > >(tee "$SDIR/token-rate-probe.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "source (operational server log only): $SL"
echo
echo "=== distinct log line shapes carrying a token count ==="
grep -oiE "n_tokens[ =:]+[0-9]+|n_prompt_tokens[a-z_]*[ =:]+[0-9]+|prompt eval[^|]*|[0-9]+ tokens" "$SL" 2>/dev/null | sort | uniq -c | sort -rn | sed -n '1,25p' | sed 's/^/  /'
echo
echo "=== task/slot lines (first 6) ==="
grep -iE "slot|task" "$SL" | grep -viE "not marked as outputs" | sed -n '1,6p' | sed 's/^/  /'
echo
echo "=== every numeric token figure observed, as a distribution ==="
grep -oiE "n_tokens[ =:]+[0-9]+" "$SL" 2>/dev/null | grep -oE "[0-9]+$" | sort -n | uniq -c | sed 's/^/  /'
echo "end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
