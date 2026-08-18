#!/usr/bin/env bash
# Archive the P-A2T Stage-2 supply-probe flight into the study's check surface.
# Run ONLY after client.close() has returned (a dirty tree during a run refuses
# the COMPLETED manifest at finalize).
#   archive.sh <attempt-id>
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/s2fly2/env.sh

ATTEMPT="${1:?usage: archive.sh <attempt-id>}"
RUN_DIR="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2-120/$ATTEMPT"
DEST="$REPO/docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-s2-flight"

mkdir -p "$DEST/launcher"

# 1. the launcher chain (every file that produced the flight)
for f in env.sh flight_identity.py flight_plan.py gpu_health.sh gpu_sample.sh \
         launch_pa2t_s2.py measure_split.py preflight.py probe_d1.py \
         archive.sh status.sh \
         run_flight.sh run_measure.sh run_preflight.sh run_probe_d1.sh run_tests.sh; do
  cp "$SCRATCH/$f" "$DEST/launcher/$f"
done

# the flight receipt narrative
cp "$SCRATCH/README.md" "$DEST/README.md"

# 2. health logs (operational only -- no response text, no metric value)
cp "$SCRATCH/preflight-split-measurement.json" "$DEST/preflight-split-measurement.json"
cp "$SCRATCH/preflight-split-measurement.log"  "$DEST/preflight-split-measurement.log"
cp "$SCRATCH/preflight-d1-probe.log"           "$DEST/preflight-d1-probe.log"
cp "$SCRATCH/preflight-tests.log"              "$DEST/preflight-tests.log"
cp "$SCRATCH/preflight.log"                    "$DEST/preflight.log"
cp "$SCRATCH/gpu-health.log"                   "$DEST/gpu-health.log"
cp "$SCRATCH/flight.log"                       "$DEST/flight.log"

# 3. run receipts (identity + cost + per-arm counts; never response content)
cp "$RUN_DIR/flight-receipt.json"                        "$DEST/flight-receipt.json"
cp "$RUN_DIR/SAEA-PROBE-a2t-s2-120.plan.json"            "$DEST/execution-plan.json"
cp "$RUN_DIR/SAEA-PROBE-a2t-s2-120.config-values.json"   "$DEST/config-values.json"
cp "$RUN_DIR/SAEA-PROBE-a2t-s2-120.session-receipt.json" "$DEST/session-receipt.json"

# 4. manifest over everything above
cd "$DEST"
rm -f MANIFEST.sha256
find . -type f ! -name MANIFEST.sha256 | sort | xargs sha256sum -b > MANIFEST.sha256
echo "archived $(wc -l < MANIFEST.sha256) files to $DEST"
ls -la "$DEST"
