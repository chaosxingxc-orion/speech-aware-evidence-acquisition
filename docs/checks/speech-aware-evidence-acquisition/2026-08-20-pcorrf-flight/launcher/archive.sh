#!/usr/bin/env bash
# Archive the P-CORR-F type-corrective supply flight into the study's check
# surface. Run ONLY after client.close() has returned.
#   archive.sh <attempt-id>
#
# Archive conventions follow the P-TRAP/P-SLU precedent EXACTLY:
#   * launcher/ carries every file that produced the flight;
#   * logs carry operational/structural fields only;
#   * the STRUCTURAL binding stats are committable, the FULL corrective binding
#     table (which carries percept-selected supply text) is NOT and stays in the
#     attempt dir under SPEECHRL_DATA_DIR;
#   * no response text, no metric value, no verdict anywhere.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf
source "$SDIR/env.sh"

ATTEMPT="${1:?usage: archive.sh <attempt-id>}"
RUN_DIR="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pcorrf-240/$ATTEMPT"
DEST="$REPO/docs/checks/speech-aware-evidence-acquisition/2026-08-20-pcorrf-flight"

mkdir -p "$DEST/launcher"

# 1. the launcher chain (every file that produced the flight)
for f in env.sh binding.py flight_identity.py launch_pcorrf_flight.py preflight.py \
         gguf_verify.sh postflight.sh gpu_accounting.sh archive.sh update_ledger.py \
         run_binding.sh run_preflight.sh run_flight.sh \
         session_precheck.sh run_pytest.sh syntax_check.sh collect_delta.sh \
         wait_for_session.sh wait_for_land.sh; do
  cp "$SCRATCH/$f" "$DEST/launcher/$f"
done

# the flight receipt narrative
cp "$SCRATCH/README.md" "$DEST/README.md"

# 2. health logs (operational/structural only -- no response text, no metric value)
cp "$SCRATCH/session-precheck.log"            "$DEST/session-precheck.log"
cp "$SCRATCH/preflight-pytest.log"            "$DEST/preflight-pytest.log"
cp "$SCRATCH/collect-delta.log"               "$DEST/collect-delta.log"
cp "$SCRATCH/binding.log"                     "$DEST/binding.log"
cp "$SCRATCH/corrective-binding-stats.json"   "$DEST/corrective-binding-stats.json"
cp "$SCRATCH/preflight.log"                   "$DEST/preflight.log"
cp "$SCRATCH/gguf-verify.log"                 "$DEST/gguf-verify.log"
cp "$SCRATCH/flight.log"                      "$DEST/flight.log"
cp "$SCRATCH/postflight.log"                  "$DEST/postflight.log"
cp "$SCRATCH/gpu-accounting.log"              "$DEST/gpu-accounting.log"

# 3. run receipts (identity + cost + per-arm counts; never response content)
cp "$RUN_DIR/flight-receipt.json"                        "$DEST/flight-receipt.json"
cp "$RUN_DIR/SAEA-PROBE-pcorrf-240.plan.json"            "$DEST/execution-plan.json"
cp "$RUN_DIR/SAEA-PROBE-pcorrf-240.config-values.json"   "$DEST/config-values.json"
cp "$RUN_DIR/SAEA-PROBE-pcorrf-240.session-receipt.json" "$DEST/session-receipt.json"

# 4. manifest over everything above
cd "$DEST"
rm -f MANIFEST.sha256
find . -type f ! -name MANIFEST.sha256 | sort | xargs sha256sum -b > MANIFEST.sha256
echo "archived $(wc -l < MANIFEST.sha256) files to $DEST"
ls -la "$DEST"

# Guards run with errexit/pipefail OFF: a grep that legitimately finds nothing
# exits 1, which must NOT abort the guard report.
set +e
set +o pipefail

# The guards look for the JSON KEY FORM ("key":), never a bare substring: this
# receipt and the post-flight log both legitimately NAME these fields in prose
# to state that they were never opened, and a bare-substring guard would flag
# its own promise as a violation.
hits() { grep -rlE -- "$1" "$DEST" 2>/dev/null | grep -v '/launcher/' | wc -l; }

echo
echo "=== LEAK GUARD: no response text and no supply content may enter the archive ==="
echo "  files carrying a \"response_text\": JSON field (expect 0): $(hits '"response_text"[[:space:]]*:')"
echo "  files carrying a \"corrective_entries\": JSON field (expect 0): $(hits '"corrective_entries"[[:space:]]*:')"
echo "  files named corrective-binding.json (the FULL supply table; expect 0): $(find "$DEST" -name 'corrective-binding.json' | wc -l)"
echo "  outputs.jsonl / responses.jsonl copies (expect 0): $(find "$DEST" \( -name 'outputs.jsonl' -o -name 'responses.jsonl' \) | wc -l)"
echo "  (prose mentions of those field names, which are expected and benign:"
echo "     $(grep -rl 'response_text' "$DEST" 2>/dev/null | grep -v '/launcher/' | tr '\n' ' '))"

echo
echo "=== READ GUARD: zero computed-result keys anywhere in the archive ==="
for key in '"slu_f1"[[:space:]]*:' '"slot_f1_exact"[[:space:]]*:' '"metrics"[[:space:]]*:' '"recovery' '"contamination' 'CORRECTIVE-PERCEPT' 'CORRECTIVE-INERT' 'INCONCLUSIVE-CORR' 'DOSE-EFFICIENT' 'DOSE-INSUFFICIENT' 'INCONCLUSIVE-DOSE'; do
  echo "  files carrying $key (expect 0): $(hits "$key")"
done
echo "ARCHIVE DONE"
