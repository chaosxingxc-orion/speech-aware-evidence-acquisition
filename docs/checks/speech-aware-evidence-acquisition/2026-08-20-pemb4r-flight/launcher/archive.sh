#!/usr/bin/env bash
# Land the P-EMB-4R flight evidence under docs/checks/. Copies RECEIPTS, LOGS
# and hashed SUMMARIES only -- never a vector, never a retrieval-plan body,
# never a C-DECODE response. Every file that carries raw embedding components
# (vectors-*.jsonl, gate-c-*-vector.json, *-jitter-vectors.json, every .npy
# under the data root), the retrieval plan itself, and every C-DECODE response
# stays on the data root, exactly where the registration puts it: "vectors/bank
# manifests on the data root, hashes only in Git".
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"

ATTEMPT="$1"
DEST="$REPO/docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb4r-flight"
RUN_DIR="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb4r-4100/$ATTEMPT"

rm -rf "$DEST"
mkdir -p "$DEST/launcher"

cp "$RUN_DIR/flight-receipt.json"                        "$DEST/flight-receipt.json"
cp "$RUN_DIR/flight-state.json"                          "$DEST/flight-state.json"
cp "$RUN_DIR/SAEA-PROBE-pemb4r-4100.plan.json"           "$DEST/execution-plan.json"
cp "$RUN_DIR/SAEA-PROBE-pemb4r-4100.config-values.json"  "$DEST/config-values.json"
cp "$SPEECHRL_DATA_DIR/attempts/SAEA-PROBE-pemb4r-4100/$ATTEMPT.json" "$DEST/attempt-state.json"
cp "$RUN_DIR/c-decode-determinism-resend.json"           "$DEST/c-decode-determinism-resend.json" 2>/dev/null || true
for f in "$RUN_DIR"/*.session-*.receipt.json; do
  [ -e "$f" ] && cp "$f" "$DEST/$(basename "$f" | sed 's/^SAEA-PROBE-pemb4r-4100\.//')"
done
for f in "$RUN_DIR"/*.server.log; do
  [ -e "$f" ] && cp "$f" "$DEST/$(basename "$f" | sed 's/^SAEA-PROBE-pemb4r-4100\.//')"
done
cp "$SCRATCH/flight.log"                 "$DEST/flight.log"
cp "$SCRATCH/pytest.log"                 "$DEST/preflight-pytest.log" 2>/dev/null || true
cp "$SCRATCH/takeoff-state.log"          "$DEST/takeoff-state.log" 2>/dev/null || true
cp "$SCRATCH/bank-binding-check.log"     "$DEST/preflight-bank-binding-check.log" 2>/dev/null || true
cp "$SCRATCH/syntax-check.log"           "$DEST/preflight-syntax-check.log" 2>/dev/null || true
cp "$SCRATCH/rehearsal.log"              "$DEST/preflight-rehearsal.log" 2>/dev/null || true
cp "$SCRATCH/postflight.log"             "$DEST/postflight.log" 2>/dev/null || true
cp "$SCRATCH/cdecode-budget.log"         "$DEST/c-decode-ceiling-arithmetic.log" 2>/dev/null || true

# The C-DECODE determinism resend carries the RESEND's own response body, which
# is a raw model response like every other C-DECODE row: strip it, keep the
# hashes and the byte-identity verdict.
python - "$DEST" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1]) / "c-decode-determinism-resend.json"
if path.is_file():
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.pop("response_b_text", None)
    doc["response_body_note"] = (
        "the resent response body stays on the data root with every other C-DECODE response; "
        "only its sha256, its length and the byte-identity verdict are landed in Git"
    )
    path.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print("c-decode-determinism-resend.json: response body stripped")
PY

# Launcher sources (the archived, auditable instrument).
for f in env.sh flight_identity.py glap_loader.py launch_pemb4r_flight.py run_chain.sh \
         takeoff_state.sh run_pytest.sh syntax_check.sh rehearsal.sh bank_binding_check.sh \
         probe_dims.sh postflight.sh archive.sh wait_for.sh peek.sh land_ruling.sh \
         land_blocker.sh cdecode_budget.sh update_ledger.py render_readme.py; do
  [ -e "$f" ] && cp "$f" "$DEST/launcher/$f"
done

# Hashed SUMMARIES: per-model bank-vector and per-arm query-vector manifests
# (counts + dims + per-vector sha256, never a component), plus the retrieval
# plan's own hash and per-sample candidate-set SIZE distribution (construction
# metadata: how many distinct labels each retrieved set carries -- never which
# label is right, never a gold comparison), plus C-DECODE row/format counts.
python - "$DEST" "$RUN_DIR" <<'PY'
import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, ".")
from speech_aware_evidence_acquisition.data.lock import data_root
from speech_aware_evidence_acquisition.rails.probes import pemb4r_flight as F

root = data_root()
dest, run_dir = Path(sys.argv[1]), Path(sys.argv[2])

summary = {"bank_vectors_by_model": {}, "query_vectors_by_arm": {}}
for model in F.MODELS:
    path = root / "derived" / "embeddings" / F.PROBE_ID / "bank-vectors" / model / "manifest.json"
    if not path.is_file():
        summary["bank_vectors_by_model"][model] = {"present": False}
        continue
    doc = json.loads(path.read_text(encoding="utf-8"))
    entries = doc.get("entries", [])
    summary["bank_vectors_by_model"][model] = {
        "present": True, "schema": doc.get("schema"), "owner": doc.get("owner"), "dims": doc.get("dims"),
        "count": doc.get("count"), "distinct_vector_sha256": len({e.get("sha256") for e in entries}),
        "manifest_path_on_data_root": str(path),
        "entries": [{"contact_id": e["contact_id"], "dims": e["dims"], "sha256": e["sha256"]} for e in entries],
    }
for arm_id in F.ARM_IDS:
    path = root / "derived" / "embeddings" / F.arm_run_id(arm_id) / "query" / "manifest.json"
    if not path.is_file():
        summary["query_vectors_by_arm"][arm_id] = {"present": False}
        continue
    doc = json.loads(path.read_text(encoding="utf-8"))
    entries = doc.get("entries", [])
    summary["query_vectors_by_arm"][arm_id] = {
        "present": True, "schema": doc.get("schema"), "owner": doc.get("owner"), "dims": doc.get("dims"),
        "count": doc.get("count"), "distinct_vector_sha256": len({e.get("sha256") for e in entries}),
        "manifest_path_on_data_root": str(path),
        "entries": [{"contact_id": e["contact_id"], "dims": e["dims"], "sha256": e["sha256"]} for e in entries],
    }
(dest / "vector-manifest-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
print("vector-manifest-summary.json written")

plan_path = root / "derived" / "embeddings" / F.PROBE_ID / "retrieval-plan" / "retrieval_plan.json"
if plan_path.is_file():
    doc = json.loads(plan_path.read_text(encoding="utf-8"))
    out = {
        "schema": doc["schema"],
        "k_primary": doc["k_primary"],
        "winner_arm_id": doc["winner_arm_id"],
        "winner_selection_rule": doc["winner_selection_rule"],
        "retrieval_plan_sha256": F.retrieval_plan_document_sha256(doc),
        "plan_path_on_data_root": str(plan_path),
        "per_arm": {},
        "note": (
            "CONSTRUCTION METADATA ONLY. Candidate-set SIZE distributions record how many DISTINCT "
            "TRAIN-split labels each per-sample retrieved set carries -- never which label is right, "
            "never any comparison against devel gold. The per-sample label sets themselves and every "
            "cosine stay in the plan on the data root; analysis.pemb4r_read re-derives them."
        ),
    }
    for arm_id, block in sorted(doc["arms"].items()):
        rows = block["per_sample"]
        out["per_arm"][arm_id] = {
            "mean_top1_cosine": block["mean_top1_cosine"],
            "n_samples": len(rows),
            "candidate_set_size_distribution_k5": {
                str(k): v for k, v in sorted(Counter(len(r["dedup_labels_k5"]) for r in rows.values()).items())
            },
            "candidate_set_size_distribution_k3": {
                str(k): v for k, v in sorted(Counter(len(r["dedup_labels_k3"]) for r in rows.values()).items())
            },
            "candidate_set_size_distribution_k1": {
                str(k): v for k, v in sorted(Counter(len(r["dedup_labels_k1"]) for r in rows.values()).items())
            },
        }
    (dest / "retrieval-plan-summary.json").write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print("retrieval-plan-summary.json written")

outputs = run_dir / "c-decode-outputs.jsonl"
if outputs.is_file():
    rows = [json.loads(line) for line in outputs.read_text(encoding="utf-8").splitlines() if line.strip()]
    doc = {
        "n_rows": len(rows),
        "outputs_path_on_data_root": str(outputs),
        "winner_arm_id": rows[0]["winner_arm_id"] if rows else None,
        "c_decode_query_kind": rows[0]["c_decode_query_kind"] if rows else None,
        "candidate_set_size_distribution": {
            str(k): v for k, v in sorted(Counter(len(r["candidate_labels"]) for r in rows).items())
        },
        "response_char_length": {
            "min": min((len(r["response_text"]) for r in rows), default=None),
            "max": max((len(r["response_text"]) for r in rows), default=None),
            "mean": (sum(len(r["response_text"]) for r in rows) / len(rows)) if rows else None,
        },
        "closed_set_mapping_outcome_counts": {
            str(k): v for k, v in sorted(Counter(r["closed_set_mapping"]["outcome"] for r in rows).items())
        },
        "closed_set_mapping_fallback_count": sum(1 for r in rows if r["closed_set_mapping"]["fallback"]),
        "note": (
            "FORMAT/PARSE HEALTH ONLY, never accuracy. closed_set_mapping compares the core's own "
            "emitted label against ITS OWN SUPPLIED candidate set (map_predicted_scenario_to_canonical); "
            "no devel gold is involved anywhere in this file. Every response body and every per-sample "
            "row stays on the data root for analysis.pemb4r_read."
        ),
    }
    (dest / "c-decode-summary.json").write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    print("c-decode-summary.json written")
PY

# LEAK GUARD: nothing vector-bearing or response-bearing may have reached Git.
echo "--- leak guard ---"
LEAK=$(find "$DEST" \( -name '*.npy' -o -name 'vectors-*.jsonl' -o -name '*jitter-vectors*' \
        -o -name 'retrieval_plan.json' -o -name 'c-decode-outputs.jsonl' -o -name 'c-decode-responses.jsonl' \
        -o -name 'gate-c-*-vector.json' \) || true)
if [ -n "$LEAK" ]; then echo "LEAK GUARD FAILED (vector/response file in the archive):"; echo "$LEAK"; exit 3; fi
python - "$DEST" <<'PY'
import json, sys
from pathlib import Path
dest = Path(sys.argv[1])
bad = []
for path in sorted(dest.rglob("*.json")):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        continue
    # A raw vector is a long run of floats; the summaries only ever carry
    # sha256 strings, integers and a handful of scalars. Flag any JSON array of
    # more than 64 numbers anywhere in the landed evidence.
    def walk(node, where):
        if isinstance(node, list):
            if len(node) > 64 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in node):
                bad.append(f"{path.name}:{where} -- numeric array of length {len(node)}")
            for i, v in enumerate(node):
                walk(v, f"{where}[{i}]")
        elif isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{where}.{k}")
    try:
        walk(json.loads(text), "")
    except Exception:
        continue
if bad:
    print("LEAK GUARD FAILED (raw numeric vector in landed JSON):")
    for line in bad[:20]:
        print("  ", line)
    sys.exit(3)
print("leak guard PASS: no .npy, no vectors-*.jsonl, no retrieval plan body, no C-DECODE response file,")
print("                 and no numeric array longer than 64 anywhere in the landed JSON")
PY

# READ GUARD: no computed-result key may appear anywhere in the landed evidence.
echo "--- read guard ---"
python - "$DEST" <<'PY'
import re, sys
from pathlib import Path
dest = Path(sys.argv[1])
# Keys a READ would produce and a FLIGHT must never produce. Matched as JSON
# KEYS (quoted, followed by a colon), so prose in a note/README that merely
# NAMES the concept ("no accuracy was computed") never trips the guard.
FORBIDDEN = (
    "accuracy", "vote_accuracy", "recall", "recall_at_1", "recall_at_3", "recall_at_5",
    "n_correct", "correct", "is_correct", "gold_label", "gold_scenario", "verdict",
    "predicted_correct", "hit", "precision", "f1", "argmax_stability", "cross_arm_agreement",
)
pattern = re.compile(r'"(' + "|".join(re.escape(k) for k in FORBIDDEN) + r')"\s*:')
hits = []
for path in sorted(dest.rglob("*")):
    if not path.is_file() or path.suffix not in (".json", ".jsonl"):
        continue
    for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for m in pattern.finditer(line):
            hits.append(f"{path.relative_to(dest)}:{n}: {m.group(1)}")
if hits:
    print("READ GUARD FAILED (computed-result key in landed evidence):")
    for line in hits[:30]:
        print("  ", line)
    sys.exit(4)
print(f"read guard PASS: zero computed-result keys ({len(FORBIDDEN)} patterns) in any landed JSON")
PY

# MANIFEST.sha256 over everything landed.
cd "$DEST"
find . -type f ! -name MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256
echo "MANIFEST.sha256: $(wc -l < MANIFEST.sha256) files"
ls -la "$DEST"
