#!/usr/bin/env bash
# Post-flight verification. Operational fields ONLY -- never opens outputs.jsonl content.
# Usage: postflight.sh <attempt-id>
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pkey2fly/env.sh

RD="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338/$1"

echo "=== run dir ==="
ls -la "$RD"

echo
echo "=== flight receipt (operational fields) ==="
python - "$RD" <<'PY'
import json, sys, pathlib
rd = pathlib.Path(sys.argv[1])
r = json.loads((rd / "flight-receipt.json").read_text(encoding="utf-8"))
for k in ("run_id","attempt_id","status","error","config_hash","protocol_hash",
          "split_identity_hash","wall_seconds","requests_flown_this_attempt",
          "requests_replayed_from_cache","request_failures","result_rows"):
    print(f"  {k}: {r.get(k)}")
s = r["session"]
print("  session.binary_path:", s["binary_path"])
print("  session.binary_sha256:", s["binary_sha256"])
print("  session.argv:", " ".join(s["argv"]))
for m in s["model_files"]:
    print("  session.model_file:", m["path"], m["sha256"])
c = r["close_receipt"]
print("  close_receipt.trace_manifest_hash:", c.get("trace_manifest_hash"))
print("  close_receipt.cost:", json.dumps(c.get("cost"), sort_keys=True))
print("  silence_swap entries:", len(r.get("silence_swap", {})))
PY

echo
echo "=== output artifact shapes (line counts only, content NEVER read) ==="
for f in responses.jsonl outputs.jsonl; do
  if [ -f "$RD/$f" ]; then echo "  $f: $(wc -l < "$RD/$f") lines, $(stat -c %s "$RD/$f") bytes"; fi
done
if [ -f "$RD/transcript-registry.json" ]; then
  echo "  transcript-registry.json: $(stat -c %s "$RD/transcript-registry.json") bytes, entries: $(python -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$RD/transcript-registry.json")"
fi

echo
echo "=== trace manifest status (operational) ==="
python - "$RD" <<'PY'
import json, sys, pathlib
rd = pathlib.Path(sys.argv[1])
for p in sorted(rd.glob("*trace-manifest.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    print(" ", p.name)
    for k in ("status","run_id","attempt_id","study_commit","request_count","closed_at"):
        if k in d:
            print(f"    {k}: {d[k]}")
PY

echo
echo "=== feature cache AFTER flight ==="
echo "campaign  $SAEA_FEAT_CACHE_DIR"
du -sh "$SAEA_FEAT_CACHE_DIR" 2>/dev/null
echo "  entries: $(find "$SAEA_FEAT_CACHE_DIR" -type f 2>/dev/null | wc -l)"
echo "  dir mtime: $(stat -c '%y' "$SAEA_FEAT_CACHE_DIR" 2>/dev/null)"
echo "legacy /home/chao/feat-cache/q4km"
echo "  entries: $(find /home/chao/feat-cache/q4km -type f 2>/dev/null | wc -l)"
echo "  dir mtime: $(stat -c '%y' /home/chao/feat-cache/q4km 2>/dev/null)"

echo
echo "=== server.log encode-line evidence (featcache hits are proven by ABSENT encode lines) ==="
for pat in "encoding audio" "feat_cache MISS" "feat_cache HIT" "cache save" "encode"; do
  c=$(grep -ci -- "$pat" "$RD/SAEA-PROBE-pkey2-338.server.log" 2>/dev/null || true)
  echo "  server.log lines matching '$pat': ${c:-0}"
done

echo
echo "=== orphan llama-server check ==="
pgrep -a llama-server || echo "  none running"

echo
echo "=== exposure ledger row mentions (count only) ==="
grep -o 'SAEA-PROBE-pkey2-338' "$REPO/docs/exposure-ledger.md" | wc -l

echo
echo "=== git tree ==="
cd "$REPO" && git status --porcelain && echo "  (clean)" && git log --oneline -1
