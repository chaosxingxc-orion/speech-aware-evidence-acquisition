#!/usr/bin/env bash
# Archive one P-EMB embedding-tier run into the study's check surface.
# Run ONLY after the launcher has written its flight receipt.
#   archive.sh <A|B> <attempt-id>
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri2/pemb
source "$SDIR/env.sh"

RUN="${1:?usage: archive.sh <A|B> <attempt-id>}"
ATTEMPT="${2:?usage: archive.sh <A|B> <attempt-id>}"
case "$RUN" in
  A) RUN_ID=SAEA-PROBE-pemb1-78;  SLUG=2026-08-19-pemb1-flight ;;
  B) RUN_ID=SAEA-PROBE-pemb2-552; SLUG=2026-08-19-pemb2-flight ;;
  *) echo "unknown run $RUN"; exit 2 ;;
esac
RUN_DIR="$SPEECHRL_DATA_DIR/runs/$RUN_ID/$ATTEMPT"
DEST="$REPO/docs/checks/speech-aware-evidence-acquisition/$SLUG"
TRI="$SDIR/.."

mkdir -p "$DEST/launcher"

# 1. the launcher chain (every file that produced the run)
for f in env.sh flight_identity.py launch_pemb_flight.py preflight.py \
         gguf_verify.sh postflight.sh archive.sh identity_check.sh \
         run_preflight.sh run_flight.sh; do
  cp "$SCRATCH/$f" "$DEST/launcher/$f"
done
# the session-level env + precheck + teardown wrappers shared this session
cp "$TRI/env.sh"              "$DEST/launcher/session-env.sh"
cp "$TRI/session_precheck.sh" "$DEST/launcher/session_precheck.sh"
cp "$TRI/run_pytest.sh"       "$DEST/launcher/session_run_pytest.sh"
cp "$TRI/teardown_server.sh"  "$DEST/launcher/session_teardown_server.sh"
cp "$TRI/probe_marker.sh"     "$DEST/launcher/session_probe_marker.sh"

# the flight receipt narrative
cp "$SCRATCH/README-run$RUN.md" "$DEST/README.md"

# 2. health logs (operational/structural only -- never a vector component)
cp "$TRI/session-precheck.log"      "$DEST/session-precheck.log"
cp "$TRI/preflight-pytest.log"      "$DEST/preflight-pytest.log"
cp "$TRI/marker-probe.log"          "$DEST/marker-probe.log"
cp "$TRI/teardown.log"              "$DEST/session-teardown.log"
cp "$SCRATCH/preflight-run$RUN.log" "$DEST/preflight.log"
cp "$SCRATCH/gguf-verify.log"       "$DEST/gguf-verify.log"
cp "$SCRATCH/flight-run$RUN.log"    "$DEST/flight.log"
cp "$SCRATCH/postflight-run$RUN.log" "$DEST/postflight.log"
cp "$SCRATCH/identity-check.log"    "$DEST/identity-check.log"

# Run B only: the pooled-sequence feasibility probes that settled whether the
# 35.71 s longest clip fits the embedding server's forced 512-token budget
# BEFORE 552 registered contacts were spent. Operational server log + durations
# only -- no vector, no output row.
if [ "$RUN" = "B" ]; then
  cp "$SCRATCH/token_rate_probe.sh" "$DEST/launcher/token_rate_probe.sh"
  cp "$SCRATCH/token_fit.sh"        "$DEST/launcher/token_fit.sh"
  cp "$SCRATCH/token-rate-probe.log" "$DEST/token-rate-probe.log"
  cp "$SCRATCH/token-fit.log"        "$DEST/token-fit.log"
fi

# 3. run receipts (identity + cost + contact counts; never a vector)
cp "$RUN_DIR/flight-receipt.json"          "$DEST/flight-receipt.json"
cp "$RUN_DIR/$RUN_ID.plan.json"            "$DEST/execution-plan.json"
cp "$RUN_DIR/$RUN_ID.config-values.json"   "$DEST/config-values.json"
cp "$RUN_DIR/$RUN_ID.session-receipt.json" "$DEST/session-receipt.json"
cp "$RUN_DIR/contacts.json"                "$DEST/contacts.json"
cp "$SPEECHRL_DATA_DIR/attempts/$RUN_ID/$ATTEMPT.json" "$DEST/attempt-state.json"

# 4. the embedding manifest's own STRUCTURAL summary (counts + per-entry
#    sha256/relpath/dims -- the vectors themselves stay on the data root)
python - "$SPEECHRL_DATA_DIR" "$RUN_ID" "$DEST" <<'PY'
import collections
import json
import pathlib
import sys

root, run_id, dest = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
mp = root / "derived" / "embeddings" / run_id / "manifest.json"
d = json.loads(mp.read_text(encoding="utf-8"))
entries = d.get("entries", [])
summary = {
    "schema": "saea-pemb-embedding-manifest-summary-v1",
    "source_manifest": str(mp),
    "manifest_sha256": __import__("hashlib").sha256(mp.read_bytes()).hexdigest(),
    "run_id": d.get("run_id"),
    "dims": d.get("dims"),
    "audio_count": d.get("audio_count"),
    "text_count": d.get("text_count"),
    "entry_count": len(entries),
    "entries_by_kind": dict(sorted(collections.Counter(e["kind"] for e in entries).items())),
    "distinct_vector_sha256": len({e["sha256"] for e in entries}),
    "dim_distribution": dict(sorted(collections.Counter(e["dims"] for e in entries).items())),
    "entries": [
        {"contact_id": e["contact_id"], "kind": e["kind"], "relpath": e["relpath"],
         "dims": e["dims"], "sha256": e["sha256"]}
        for e in sorted(entries, key=lambda e: (e["kind"], e["contact_id"]))
    ],
}
(dest / "embedding-manifest-summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
)
print("embedding manifest summary:", summary["entry_count"], "entries,",
      summary["distinct_vector_sha256"], "distinct vector hashes")
PY

# 5. manifest over everything above
cd "$DEST"
rm -f MANIFEST.sha256
find . -type f ! -name MANIFEST.sha256 | sort | xargs sha256sum -b > MANIFEST.sha256
echo "archived $(wc -l < MANIFEST.sha256) files to $DEST"
ls -la "$DEST"
echo
echo "=== leak guard: no vector component and no response text may enter the archive ==="
# A vector would appear as a JSON ARRAY under a "values" key. The bare token
# "values" is deliberately NOT the guard: config-values.json legitimately
# carries a "values" OBJECT (the hashed config bundle, ~2 KB), and launcher/
# files name the field in code and inside this guard's own search strings.
echo "  files carrying a vector ARRAY ('\"values\": ['): $(grep -rl '\"values\": \[' "$DEST" | grep -v '/launcher/' | wc -l) (expect 0)"
echo "  files carrying 'response_text': $(grep -rl 'response_text' "$DEST" | grep -v '/launcher/' | wc -l) (outside launcher/, expect 0)"
echo "  .npy files under the archive: $(find "$DEST" -name '*.npy' | wc -l) (expect 0)"
echo "  vectors.jsonl under the archive: $(find "$DEST" -name 'vectors.jsonl' | wc -l) (expect 0)"
echo "  largest archived file: $(find "$DEST" -type f -printf '%s %p\n' | sort -rn | sed -n 1p)"
