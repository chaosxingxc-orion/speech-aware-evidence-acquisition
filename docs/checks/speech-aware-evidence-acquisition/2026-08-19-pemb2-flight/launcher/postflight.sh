#!/usr/bin/env bash
# Post-flight verification. Operational/structural fields ONLY -- never reads a
# vector component, never compares two vectors.
# Usage: postflight.sh <A|B> <attempt-id>
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri2/pemb
source "$SDIR/env.sh"

RUN="${1:?usage: postflight.sh <A|B> <attempt-id>}"
ATTEMPT="${2:?usage: postflight.sh <A|B> <attempt-id>}"
case "$RUN" in
  A) RUN_ID=SAEA-PROBE-pemb1-78;  export SAEA_FEAT_CACHE_DIR=/home/chao/feat-cache/slurp-q4km ;;
  B) RUN_ID=SAEA-PROBE-pemb2-552; export SAEA_FEAT_CACHE_DIR=/home/chao/feat-cache/audio2tool-q4km ;;
  *) echo "unknown run $RUN"; exit 2 ;;
esac
RD="$SPEECHRL_DATA_DIR/runs/$RUN_ID/$ATTEMPT"

exec > >(tee "$SCRATCH/postflight-run$RUN.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "run: $RUN ($RUN_ID) attempt: $ATTEMPT"

echo
echo "=== run dir ==="
ls -la "$RD"

echo
echo "=== flight receipt (operational fields) ==="
python - "$RD" <<'PY'
import json
import sys
import pathlib

rd = pathlib.Path(sys.argv[1])
r = json.loads((rd / "flight-receipt.json").read_text(encoding="utf-8"))
for k in (
    "run_id", "run_key", "attempt_id", "status", "error", "config_hash", "protocol_hash",
    "split_identity_hash", "umbrella_lock_sha256", "tier", "embedding_dim",
    "n_audio_contacts_expected", "n_text_contacts_expected", "n_contacts_planned",
    "n_audio_vectors", "n_text_vectors", "embedding_manifest_path",
    "metered_audio_seconds_expected", "text_contact_audio_seconds_sentinel",
    "wall_seconds", "gpu_hours_this_attempt", "contacts_flown_this_attempt",
    "contacts_replayed_from_cache", "contact_failures", "contacts_flown_by_kind",
    "durable_actual", "prior_durable_spend_before_this_attempt",
):
    print(f"  {k}: {json.dumps(r.get(k), sort_keys=True) if isinstance(r.get(k), (dict, list)) else r.get(k)}")
print("  planned_budgets:", json.dumps(r.get("planned_budgets"), sort_keys=True))
print("  registered_ceilings:", json.dumps(r.get("registered_ceilings"), sort_keys=True))
print("  latency_seconds_by_kind:", json.dumps(r.get("latency_seconds_by_kind"), sort_keys=True))
s = r.get("session")
if s:
    print("  session.binary_path:", s["binary_path"])
    print("  session.binary_sha256:", s["binary_sha256"])
    print("  session.argv:", " ".join(s["argv"]))
    for m in s["model_files"]:
        print("  session.model_file:", m["path"], m["sha256"])
PY

echo
echo "=== durable attempt file (state machine + actual spend) ==="
python - "$SPEECHRL_DATA_DIR" "$RUN_ID" "$ATTEMPT" <<'PY'
import json
import pathlib
import sys

p = pathlib.Path(sys.argv[1]) / "attempts" / sys.argv[2] / f"{sys.argv[3]}.json"
d = json.loads(p.read_text(encoding="utf-8"))
print(" ", p)
for k in ("schema", "run_id", "attempt_id", "carrier_lock_key", "state", "reserved", "actual", "gpu_seconds", "aborted_reason"):
    if k in d:
        print(f"    {k}: {json.dumps(d[k], sort_keys=True) if isinstance(d[k], dict) else d[k]}")
PY

echo
echo "=== embedding manifest (STRUCTURAL: counts, dims, hash presence -- no vector is read) ==="
python - "$SPEECHRL_DATA_DIR" "$RUN_ID" <<'PY'
import collections
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
run_id = sys.argv[2]
mp = root / "derived" / "embeddings" / run_id / "manifest.json"
if not mp.is_file():
    print("  manifest MISSING:", mp)
    raise SystemExit(0)
d = json.loads(mp.read_text(encoding="utf-8"))
print("  path:", mp)
for k in ("schema", "run_id", "dims", "audio_count", "text_count"):
    print(f"    {k}: {d.get(k)}")
entries = d.get("entries", [])
kinds = collections.Counter(e["kind"] for e in entries)
dims = collections.Counter(e["dims"] for e in entries)
print(f"    entries: {len(entries)}; by kind {json.dumps(dict(sorted(kinds.items())), sort_keys=True)}")
print(f"    dim distribution: {json.dumps(dict(sorted(dims.items())), sort_keys=True)}")
print(f"    distinct contact_id: {len({(e['kind'], e['contact_id']) for e in entries})}")
print(f"    distinct sha256: {len({e['sha256'] for e in entries})} (all-identical vectors would collapse this)")
missing = [e["relpath"] for e in entries if not (root / e["relpath"]).is_file()]
print(f"    .npy files present: {len(entries) - len(missing)}/{len(entries)}")
if missing:
    print("    MISSING:", missing[:5])
sizes = {(root / e["relpath"]).stat().st_size for e in entries if (root / e["relpath"]).is_file()}
print(f"    .npy byte sizes observed: {sorted(sizes)}")
PY

echo
echo "=== attempt artifact shapes (line/byte counts only; no vector component printed) ==="
for f in vectors.jsonl contacts.json; do
  if [ -f "$RD/$f" ]; then echo "  $f: $(wc -l < "$RD/$f") lines, $(stat -c %s "$RD/$f") bytes"; fi
done

echo
echo "=== feature cache AFTER the run ==="
echo "campaign  $SAEA_FEAT_CACHE_DIR"
du -sh "$SAEA_FEAT_CACHE_DIR" 2>/dev/null
echo "  entries: $(find "$SAEA_FEAT_CACHE_DIR" -type f 2>/dev/null | wc -l)"
echo "legacy /home/chao/feat-cache/q4km (MUST NOT BE TOUCHED)"
echo "  entries: $(find /home/chao/feat-cache/q4km -type f 2>/dev/null | wc -l)"
echo "other campaign caches"
for d in /home/chao/feat-cache/slurp-q4km /home/chao/feat-cache/audio2tool-q4km; do
  echo "  $d: $(find "$d" -type f 2>/dev/null | wc -l) entries"
done

echo
echo "=== server.log embedding-mode evidence ==="
SL="$RD/$RUN_ID.server.log"
if [ -f "$SL" ]; then
  echo "  lines: $(wc -l < "$SL")"
  # sed -n '1,20p' rather than `head -20`: head closes the pipe early and the
  # upstream grep dies of SIGPIPE, which propagates out of this script as 141.
  grep -iE "n_batch|n_ubatch|pooling_type|n_ctx_seq|embeddings enabled|new slot" "$SL" \
    | sed -n '1,20p' | sed 's/^/    /'
  echo "  'embeddings required but some input tokens were not marked as outputs' lines: $(grep -c 'not marked as outputs' "$SL" || true)"
else
  echo "  (server log missing)"
fi

echo
echo "=== GPU ==="
nvidia-smi --query-gpu=pstate,clocks.sm,clocks.max.sm,utilization.gpu,memory.used,temperature.gpu --format=csv

echo
echo "=== resident llama-server check ==="
pgrep -a llama-server || echo "  none running"

echo
echo "=== exposure ledger row mentions (count only; consumed must stay 'no') ==="
grep -c "$RUN_ID" "$REPO/docs/exposure-ledger.md"

echo
echo "=== git tree ==="
cd "$REPO" && git status --porcelain && echo "  (clean)" && git log --oneline -1
echo "POSTFLIGHT DONE"
