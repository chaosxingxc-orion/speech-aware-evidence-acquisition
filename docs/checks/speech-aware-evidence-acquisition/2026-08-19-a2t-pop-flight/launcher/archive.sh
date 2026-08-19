#!/usr/bin/env bash
# Archive the P-A2T whole-population regression flight into the study's check surface.
# Run ONLY after client.close() has returned.
#   archive.sh <attempt-id>
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri/pop
source "$SDIR/env.sh"

ATTEMPT="${1:?usage: archive.sh <attempt-id>}"
RUN_DIR="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-pop-194/$ATTEMPT"
DEST="$REPO/docs/checks/speech-aware-evidence-acquisition/2026-08-19-a2t-pop-flight"

mkdir -p "$DEST/launcher"

# 1. the launcher chain (every file that produced the flight)
for f in env.sh flight_identity.py flight_plan.py measure.py launch_a2t_pop.py preflight.py \
         postflight.sh archive.sh \
         run_measure.sh run_preflight.sh run_flight.sh; do
  cp "$SCRATCH/$f" "$DEST/launcher/$f"
done

# the flight receipt narrative
cp "$SCRATCH/README.md" "$DEST/README.md"

# 2. health logs (operational/structural only -- no response text, no metric value)
cp "$SCRATCH/measure.log"             "$DEST/measure.log"
cp "$SCRATCH/split-measurement.json"  "$DEST/split-measurement.json"
cp "$SCRATCH/preflight.log"           "$DEST/preflight.log"
cp "$SCRATCH/flight.log"              "$DEST/flight.log"
cp "$SCRATCH/postflight.log"          "$DEST/postflight.log"

# 3. run receipts (identity + cost + per-arm counts; never response content)
cp "$RUN_DIR/flight-receipt.json"                        "$DEST/flight-receipt.json"
cp "$RUN_DIR/SAEA-PROBE-a2t-pop-194.plan.json"           "$DEST/execution-plan.json"
cp "$RUN_DIR/SAEA-PROBE-a2t-pop-194.config-values.json"  "$DEST/config-values.json"
cp "$RUN_DIR/SAEA-PROBE-a2t-pop-194.session-receipt.json" "$DEST/session-receipt.json"
cp "$RUN_DIR/SAEA-PROBE-a2t-pop-194.arm-plan.json"       "$DEST/arm-plan.json"

# 4. manifest over everything above
cd "$DEST"
rm -f MANIFEST.sha256
find . -type f ! -name MANIFEST.sha256 | sort | xargs sha256sum -b > MANIFEST.sha256
echo "archived $(wc -l < MANIFEST.sha256) files to $DEST"
ls -la "$DEST"
echo
echo "=== leak guard: no response text may enter the archive ==="
echo "  files containing 'response_text' outside launcher/: $(grep -rl 'response_text' "$DEST" | grep -v launcher/ | wc -l) (expect 0)"
echo "  files containing '\"response\"' outside launcher/: $(grep -rl '\"response\"' "$DEST" | grep -v launcher/ | wc -l) (expect 0)"
