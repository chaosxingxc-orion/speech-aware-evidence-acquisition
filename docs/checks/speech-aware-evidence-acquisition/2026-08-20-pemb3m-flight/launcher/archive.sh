#!/usr/bin/env bash
# Land the P-EMB-3M flight evidence under docs/checks/. Copies RECEIPTS, LOGS
# and MANIFEST SUMMARIES only -- never a vector. Every file that carries raw
# embedding components (vectors-*.jsonl, gate-a-*-vector.json,
# lco-jitter-vectors.json, and every .npy under the data root) stays on the data
# root, exactly where the registration puts it: "vectors on the data root,
# hashed manifests only in Git".
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"

ATTEMPT="$1"
ABORTED="$2"
DEST="$REPO/docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb3m-flight"
RUN_DIR="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb3m-388/$ATTEMPT"

rm -rf "$DEST"
mkdir -p "$DEST/launcher"

cp "$RUN_DIR/flight-receipt.json"                        "$DEST/flight-receipt.json"
cp "$RUN_DIR/flight-state.json"                          "$DEST/flight-state.json"
cp "$RUN_DIR/SAEA-PROBE-pemb3m-388.plan.json"            "$DEST/execution-plan.json"
cp "$RUN_DIR/SAEA-PROBE-pemb3m-388.config-values.json"   "$DEST/config-values.json"
cp "$SPEECHRL_DATA_DIR/attempts/SAEA-PROBE-pemb3m-388/$ATTEMPT.json" "$DEST/attempt-state.json"
for f in "$RUN_DIR"/*.session-*.receipt.json; do
  [ -e "$f" ] && cp "$f" "$DEST/$(basename "$f" | sed 's/^SAEA-PROBE-pemb3m-388\.//')"
done
for f in "$RUN_DIR"/*.server.log; do
  [ -e "$f" ] && cp "$f" "$DEST/$(basename "$f" | sed 's/^SAEA-PROBE-pemb3m-388\.//')"
done
cp "$SCRATCH/flight.log"    "$DEST/flight.log"
cp "$SCRATCH/pytest.log"    "$DEST/preflight-pytest.log" 2>/dev/null || true

# The aborted first attempt (protocol amendment), per the P-EMB-3L precedent.
if [ -n "$ABORTED" ] && [ -d "$SCRATCH/aborted-$ABORTED" ]; then
  for f in "$SCRATCH/aborted-$ABORTED"/*; do
    cp "$f" "$DEST/attempt1-aborted-$(basename "$f" | sed 's/^SAEA-PROBE-pemb3m-388\.//')"
  done
fi

# Launcher sources (the archived, auditable instrument).
for f in env.sh flight_identity.py control_loaders.py launch_pemb3m_flight.py \
         run_stage.sh run_chain.sh abort_attempt.sh syntax_check.sh \
         dep_inventory.sh takeoff_state.sh run_pytest.sh archive.sh; do
  [ -e "$f" ] && cp "$f" "$DEST/launcher/$f"
done

# Per-arm manifest SUMMARY (counts + dims + per-vector sha256), never a vector.
python - "$DEST" <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, ".")
from speech_aware_evidence_acquisition.data.lock import data_root
from speech_aware_evidence_acquisition.rails.probes.pemb3m_flight import ARM_IDS, arm_run_id

root = data_root()
dest = Path(sys.argv[1])
summary = {}
for arm_id in ARM_IDS:
    path = root / "derived" / "embeddings" / arm_run_id(arm_id) / "manifest.json"
    if not path.is_file():
        summary[arm_id] = {"present": False}
        continue
    doc = json.loads(path.read_text(encoding="utf-8"))
    entries = doc.get("entries", [])
    summary[arm_id] = {
        "present": True,
        "schema": doc.get("schema"),
        "run_id": doc.get("run_id"),
        "dims": doc.get("dims"),
        "query_count": doc.get("query_count"),
        "label_count": doc.get("label_count"),
        "jitter_count": doc.get("jitter_count"),
        "entry_count": len(entries),
        "distinct_vector_sha256": len({e.get("sha256") for e in entries}),
        "manifest_path_on_data_root": str(path),
        "entries": [
            {"contact_id": e["contact_id"], "side": e["side"], "dims": e["dims"], "sha256": e["sha256"]}
            for e in entries
        ],
    }
(dest / "embedding-manifest-summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
)
print("embedding-manifest-summary.json written")
PY

# LEAK GUARD: nothing vector-bearing may have reached the archive.
echo "--- leak guard ---"
LEAK=$(find "$DEST" \( -name '*.npy' -o -name 'vectors-*.jsonl' -o -name '*-vector*.json' \) | grep -v 'embedding-manifest-summary' || true)
if [ -n "$LEAK" ]; then echo "LEAK GUARD FAILED:"; echo "$LEAK"; exit 3; fi
echo "leak guard PASS: no .npy, no vectors-*.jsonl, no raw vector file in the archive"

# MANIFEST.sha256 over everything landed.
cd "$DEST"
find . -type f ! -name MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256
echo "MANIFEST.sha256: $(wc -l < MANIFEST.sha256) files"
ls -la "$DEST"
