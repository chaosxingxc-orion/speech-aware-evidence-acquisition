#!/usr/bin/env bash
# Post-flight verification. Operational/structural fields ONLY -- never opens
# outputs.jsonl content.
# Usage: postflight.sh <attempt-id>
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri2/pfew
source "$SDIR/env.sh"

ATTEMPT="${1:?usage: postflight.sh <attempt-id>}"
RD="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pfew-180/$ATTEMPT"

exec > >(tee "$SCRATCH/postflight.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

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
    "run_id", "attempt_id", "status", "error", "config_hash", "protocol_hash",
    "split_identity_hash", "demo_binding_sha256", "skew_label", "n_samples",
    "n_requests_planned", "metered_audio_seconds_expected", "wall_seconds",
    "gpu_hours_this_attempt", "requests_flown_this_attempt",
    "requests_replayed_from_cache", "request_failures", "result_rows",
    "result_rows_by_arm", "requests_flown_by_arm",
):
    print(f"  {k}: {r.get(k)}")
print("  planned_budgets:", json.dumps(r.get("planned_budgets"), sort_keys=True))
print("  registered_ceilings:", json.dumps(r.get("registered_ceilings"), sort_keys=True))
s = r["session"]
print("  session.binary_path:", s["binary_path"])
print("  session.binary_sha256:", s["binary_sha256"])
print("  session.argv:", " ".join(s["argv"]))
for m in s["model_files"]:
    print("  session.model_file:", m["path"], m["sha256"])
c = r["close_receipt"]
print("  close_receipt.trace_manifest_hash:", c.get("trace_manifest_hash"))
print("  close_receipt.cost:", json.dumps(c.get("cost"), sort_keys=True))
b = r["demo_binding_stats"]
print("  binding FS-BAL K distribution:", json.dumps(b["fs_bal_k_distribution"], sort_keys=True))
print("  binding FS-SKEW K distribution:", json.dumps(b["fs_skew_k_distribution"], sort_keys=True))
print("  binding FS-BAL distinct-label distribution:",
      json.dumps(b["fs_bal_distinct_label_count_distribution"], sort_keys=True))
print("  binding FS-BAL distinct TRAIN donors:", b["fs_bal_distinct_train_donors"])
print("  binding FS-SKEW distinct TRAIN donors:", b["fs_skew_distinct_train_donors"])
print("  binding skew_label:", b["skew_label"])
PY

echo
echo "=== output artifact shapes (line counts only, content NEVER read) ==="
for f in responses.jsonl outputs.jsonl; do
  if [ -f "$RD/$f" ]; then echo "  $f: $(wc -l < "$RD/$f") lines, $(stat -c %s "$RD/$f") bytes"; fi
done
echo "  arm counts in outputs.jsonl (structural, jq-free):"
python - "$RD" <<'PY'
import collections
import json
import pathlib
import sys

rd = pathlib.Path(sys.argv[1])
counts = collections.Counter()
demo_counts = collections.Counter()
pairs = set()
for line in (rd / "outputs.jsonl").read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    d = json.loads(line)
    counts[d["arm"]] += 1
    demo_counts[(d["arm"], len(d.get("demos", ())))] += 1
    pairs.add((d["arm"], d["sample_id"]))
print("   ", json.dumps(dict(sorted(counts.items())), sort_keys=True))
print("    distinct (arm, sample_id) pairs:", len(pairs))
for arm in sorted({a for a, _ in demo_counts}):
    dist = {k: n for (a, k), n in sorted(demo_counts.items()) if a == arm}
    print(f"    {arm} demo-count distribution: {json.dumps(dist, sort_keys=True)}")
PY

echo
echo "=== trace manifest status (operational) ==="
python - "$RD" <<'PY'
import json
import pathlib
import sys

rd = pathlib.Path(sys.argv[1])
for p in sorted(rd.glob("*trace-manifest.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    print(" ", p.name)
    for k in ("status", "run_id", "attempt_id", "study_commit", "request_count", "closed_at"):
        if k in d:
            print(f"    {k}: {d[k]}")
PY

echo
echo "=== feature cache AFTER flight (hits are proven by an untouched cache) ==="
echo "campaign  $SAEA_FEAT_CACHE_DIR"
du -sh "$SAEA_FEAT_CACHE_DIR" 2>/dev/null
echo "  entries: $(find "$SAEA_FEAT_CACHE_DIR" -type f 2>/dev/null | wc -l)"
echo "  dir mtime: $(stat -c '%y' "$SAEA_FEAT_CACHE_DIR" 2>/dev/null)"
echo "legacy /home/chao/feat-cache/q4km (MUST NOT BE TOUCHED)"
echo "  entries: $(find /home/chao/feat-cache/q4km -type f 2>/dev/null | wc -l)"
echo "  dir mtime: $(stat -c '%y' /home/chao/feat-cache/q4km 2>/dev/null)"
echo "audio2tool cache (MUST NOT BE TOUCHED by this SLURP flight)"
echo "  entries: $(find /home/chao/feat-cache/audio2tool-q4km -type f 2>/dev/null | wc -l)"

echo
echo "=== server.log encode-line evidence (featcache hits => zero encode lines) ==="
for pat in "encoding audio" "encoding" ; do
  c=$(grep -ci -- "$pat" "$RD/SAEA-PROBE-pfew-180.server.log" 2>/dev/null || true)
  echo "  server.log lines matching '$pat': ${c:-0}"
done

echo
echo "=== GPU ==="
nvidia-smi --query-gpu=pstate,clocks.sm,clocks.max.sm,utilization.gpu,memory.used,temperature.gpu --format=csv

echo
echo "=== orphan llama-server check ==="
pgrep -a llama-server || echo "  none running"

echo
echo "=== exposure ledger row mentions (count only; consumed must stay 'no') ==="
grep -c 'SAEA-PROBE-pfew-180' "$REPO/docs/exposure-ledger.md"

echo
echo "=== git tree ==="
cd "$REPO" && git status --porcelain && echo "  (clean)" && git log --oneline -1
echo "POSTFLIGHT DONE"
