#!/usr/bin/env bash
# Post-flight verification. Operational/structural fields ONLY -- never opens
# outputs.jsonl content beyond arm/sample_id/k (construction metadata).
# Usage: postflight.sh <attempt-id>
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf
source "$SDIR/env.sh"

ATTEMPT="${1:?usage: postflight.sh <attempt-id>}"
RD="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pcorrf-240/$ATTEMPT"

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
    "config_protocol_hash",
    "binding_config_sha256", "split_identity_hash", "corrective_binding_hash",
    "corrective_binding_document_hash", "carried_from_attempt_id", "carried_arms",
    "carried_row_count", "n_samples", "n_cells_total", "n_requests_planned_this_attempt",
    "metered_audio_seconds_expected", "wall_seconds", "gpu_hours_this_attempt",
    "requests_flown_this_attempt", "requests_replayed_from_cache", "request_failures",
    "result_rows", "result_rows_by_arm", "requests_flown_by_arm",
    "corrective_entries_flown_by_arm",
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
b = r["corrective_binding_stats"]
for arm in b["arms"]:
    blk = b["per_arm"][arm]
    print(f"  binding {arm} K distribution:", json.dumps(blk["k_distribution"], sort_keys=True),
          "| total", blk["k_total"], "mean", blk["k_mean"], "max", blk["k_max"],
          "| K=0", blk["k_zero_sample_count"])
PY

echo
echo "=== output artifact shapes (line counts + construction K only; response text NEVER read) ==="
for f in responses.jsonl outputs.jsonl; do
  if [ -f "$RD/$f" ]; then echo "  $f: $(wc -l < "$RD/$f") lines, $(stat -c %s "$RD/$f") bytes"; fi
done
python - "$RD" <<'PY'
import collections
import json
import pathlib
import sys

rd = pathlib.Path(sys.argv[1])
counts = collections.Counter()
ks = collections.Counter()
k_total = collections.Counter()
pairs = set()
for line in (rd / "outputs.jsonl").read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    d = json.loads(line)
    counts[d["arm"]] += 1
    ks[(d["arm"], int(d["k"]))] += 1
    k_total[d["arm"]] += int(d["k"])
    pairs.add((d["arm"], d["sample_id"]))
print("  arm row counts:", json.dumps(dict(sorted(counts.items())), sort_keys=True))
print("  distinct (arm, sample_id) pairs:", len(pairs))
for arm in sorted({a for a, _ in ks}):
    dist = {k: n for (a, k), n in sorted(ks.items()) if a == arm}
    print(f"  {arm} K distribution: {json.dumps(dist, sort_keys=True)} | corrective entries flown: {k_total[arm]}")
PY

echo
echo "=== read guard: zero computed-result keys may be reported here ==="
echo "  (this script prints arm / sample_id / k only; metrics and response_text are never opened)"

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
echo "  dir mtime: $(stat -c '%y' /home/chao/feat-cache/audio2tool-q4km 2>/dev/null)"

echo
echo "=== server.log encode-line evidence (featcache hits => zero encode lines) ==="
for pat in "encoding audio" "encoding" ; do
  c=$(grep -ci -- "$pat" "$RD/SAEA-PROBE-pcorrf-240.server.log" 2>/dev/null || true)
  echo "  server.log lines matching '$pat': ${c:-0}"
done

echo
echo "=== D3 gate: bytecode under the frozen scoring package ==="
find "$REPO/src/speech_aware_evidence_acquisition/scoring" -name '__pycache__' -o -name '*.pyc' | wc -l

echo
echo "=== GPU ==="
nvidia-smi --query-gpu=pstate,clocks.sm,clocks.max.sm,utilization.gpu,memory.used,temperature.gpu,clocks_throttle_reasons.active --format=csv

echo
echo "=== orphan llama-server check / ports ==="
pgrep -a llama-server || echo "  none running"
(ss -ltnp 2>/dev/null | grep -E ':(8080|8081)\b') || echo "  ports 8080/8081 free"

echo
echo "=== exposure ledger row mentions (count only; consumed must stay 'no') ==="
grep -c 'SAEA-PROBE-pcorrf-240' "$REPO/docs/exposure-ledger.md"

echo
echo "=== git tree ==="
cd "$REPO" && git status --porcelain && echo "  (clean)" && git log --oneline -1
echo "POSTFLIGHT DONE"
