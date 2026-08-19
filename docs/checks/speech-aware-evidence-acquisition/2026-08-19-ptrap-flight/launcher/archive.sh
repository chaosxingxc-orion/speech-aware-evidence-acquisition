#!/usr/bin/env bash
# Archive the P-TRAP self-percept trap flight into the study's check surface.
# Run ONLY after client.close() has returned.
#   archive.sh <attempt-id>
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri/ptrap
source "$SDIR/env.sh"

ATTEMPT="${1:?usage: archive.sh <attempt-id>}"
RUN_DIR="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-ptrap-120/$ATTEMPT"
DEST="$REPO/docs/checks/speech-aware-evidence-acquisition/2026-08-19-ptrap-flight"
TRI="$SDIR/.."

mkdir -p "$DEST/launcher"

# 1. the launcher chain (every file that produced the flight)
for f in env.sh binding.py flight_identity.py launch_ptrap_flight.py preflight.py \
         gguf_verify.sh postflight.sh archive.sh \
         run_binding.sh run_preflight.sh run_flight.sh; do
  cp "$SCRATCH/$f" "$DEST/launcher/$f"
done
# the session-level env + preflight wrappers shared by all three probes this session
cp "$TRI/env.sh"              "$DEST/launcher/session-env.sh"
cp "$TRI/session_precheck.sh" "$DEST/launcher/session_precheck.sh"
cp "$TRI/run_pytest.sh"       "$DEST/launcher/session_run_pytest.sh"

# the flight receipt narrative
cp "$SCRATCH/README.md" "$DEST/README.md"

# 2. health logs (operational/structural only -- no response text, no metric value)
cp "$TRI/session-precheck.log"          "$DEST/session-precheck.log"
cp "$TRI/preflight-pytest.log"          "$DEST/preflight-pytest.log"
cp "$SCRATCH/binding.log"               "$DEST/binding.log"
cp "$SCRATCH/trap-binding-stats.json"   "$DEST/trap-binding-stats.json"
cp "$SCRATCH/preflight.log"             "$DEST/preflight.log"
cp "$SCRATCH/gguf-verify.log"           "$DEST/gguf-verify.log"
cp "$SCRATCH/flight.log"                "$DEST/flight.log"
cp "$SCRATCH/postflight.log"            "$DEST/postflight.log"

# 3. run receipts (identity + cost + per-arm counts; never response content)
cp "$RUN_DIR/flight-receipt.json"                       "$DEST/flight-receipt.json"
cp "$RUN_DIR/SAEA-PROBE-ptrap-120.plan.json"            "$DEST/execution-plan.json"
cp "$RUN_DIR/SAEA-PROBE-ptrap-120.config-values.json"   "$DEST/config-values.json"
cp "$RUN_DIR/SAEA-PROBE-ptrap-120.session-receipt.json" "$DEST/session-receipt.json"

# 4. manifest over everything above
cd "$DEST"
rm -f MANIFEST.sha256
find . -type f ! -name MANIFEST.sha256 | sort | xargs sha256sum -b > MANIFEST.sha256
echo "archived $(wc -l < MANIFEST.sha256) files to $DEST"
ls -la "$DEST"
echo
echo "=== leak guard: no response text may enter the archive ==="
echo "  files containing 'response_text': $(grep -rl 'response_text' "$DEST" | grep -v launcher/ | wc -l) (outside launcher/, expect 0)"
