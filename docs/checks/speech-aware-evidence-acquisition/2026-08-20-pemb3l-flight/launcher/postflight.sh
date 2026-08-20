#!/usr/bin/env bash
# Post-flight verification. Operational/structural fields ONLY -- never reads a
# vector component, never compares two vectors, never computes an accuracy.
# Usage: postflight.sh <attempt-id>
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pemb3l
source "$SDIR/env.sh"

ATTEMPT="${1:?usage: postflight.sh <attempt-id>}"
RUN_ID=SAEA-PROBE-pemb3l-234
RD="$SPEECHRL_DATA_DIR/runs/$RUN_ID/$ATTEMPT"

exec > >(tee "$SCRATCH/postflight.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "run: $RUN_ID attempt: $ATTEMPT"

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
    "run_id", "probe", "attempt_id", "status", "error", "config_hash", "protocol_hash",
    "split_identity_hash", "binding_config_sha256", "umbrella_lock_sha256", "tier",
    "embedding_dim", "arm_order", "n_audio_contacts_expected_per_arm",
    "n_text_contacts_expected_per_arm", "n_contacts_expected_per_arm", "n_contacts_planned",
    "n_contacts_produced", "sweep_total_invariant_pass",
    "metered_audio_seconds_expected_one_pass", "metered_audio_seconds_expected_sweep",
    "text_contact_audio_seconds_sentinel", "wall_seconds", "gpu_occupied_seconds_this_attempt",
    "gpu_hours_this_attempt", "contacts_flown_this_attempt", "contacts_replayed_from_cache",
    "contact_failures", "contacts_flown_by_kind", "durable_actual",
    "prior_durable_spend_before_this_attempt",
):
    v = r.get(k)
    print(f"  {k}: {json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v}")
print("  planned_budgets:", json.dumps(r.get("planned_budgets"), sort_keys=True))
print("  registered_ceilings:", json.dumps(r.get("registered_ceilings"), sort_keys=True))
print("  latency_seconds_by_kind:", json.dumps(r.get("latency_seconds_by_kind"), sort_keys=True))
print()
print("  === per arm ===")
for arm_id, a in sorted(r.get("arms", {}).items()):
    print(f"  {arm_id}:")
    for k in ("manifest_run_id", "pooling_mode", "audio_prefix", "text_prefix", "session_key",
              "n_audio_vectors", "n_text_vectors", "n_contacts", "contacts_flown",
              "contacts_replayed", "wall_seconds", "embedding_manifest_path"):
        print(f"    {k}: {a.get(k)!r}" if isinstance(a.get(k), str) else f"    {k}: {a.get(k)}")
    print(f"    flown_by_kind: {json.dumps(a.get('flown_by_kind'), sort_keys=True)}")
    print(f"    contact_failures: {json.dumps(a.get('contact_failures'), sort_keys=True)}")
print()
print("  === per session ===")
for s in r.get("sessions", []):
    print(f"  session {s['session_key']!r} (pooling {s['pooling_mode']!r}) arms {s['arm_ids']}")
    if not s.get("spawned", True):
        print("    NOT SPAWNED: every arm in this session was already complete on the data root "
              "(carried from an earlier attempt) -- no GPU, no contacts")
        continue
    print(f"    pid {s['pid']} port {s['port']} spawn {s['spawn_seconds']:.1f}s resident {s['resident_seconds']:.1f}s")
    print(f"    binary {s['binary_path']} {s['binary_sha256']}")
    print(f"    argv: {' '.join(s['argv'])}")
    for m in s["model_files"]:
        print(f"    model file: {m['path']} {m['sha256']}")
    print(f"    teardown: {json.dumps(s['teardown'], sort_keys=True, default=str)}")
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
echo "=== embedding manifests, ONE PER ARM (STRUCTURAL: counts, dims, hash presence -- no vector is read) ==="
python - "$SPEECHRL_DATA_DIR" "$RUN_ID" <<'PY'
import collections
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
run_id = sys.argv[2]
base = root / "derived" / "embeddings" / run_id
if not base.is_dir():
    print("  sweep manifest root MISSING:", base)
    raise SystemExit(0)
print("  sweep manifest root:", base)
all_hashes = {}
for arm_dir in sorted(p for p in base.iterdir() if p.is_dir()):
    mp = arm_dir / "manifest.json"
    print(f"  --- arm {arm_dir.name} ---")
    if not mp.is_file():
        print("    manifest MISSING:", mp)
        continue
    d = json.loads(mp.read_text(encoding="utf-8"))
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
    all_hashes[arm_dir.name] = {e["sha256"] for e in entries}

print()
print("  === cross-arm separation (STRUCTURAL ONLY: byte identity, never a comparison of values) ===")
names = sorted(all_hashes)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        shared = len(all_hashes[a] & all_hashes[b])
        print(f"    {a} vs {b}: {shared} byte-identical vector(s) shared "
              f"(a construction that changed nothing would share all 78)")
PY

echo
echo "=== attempt artifact shapes (line/byte counts only; no vector component printed) ==="
for f in "$RD"/vectors-*.jsonl "$RD"/contacts.json; do
  if [ -f "$f" ]; then echo "  $(basename "$f"): $(wc -l < "$f") lines, $(stat -c %s "$f") bytes"; fi
done

echo
echo "=== feature cache AFTER the run ==="
echo "campaign  $SAEA_FEAT_CACHE_DIR"
du -sh "$SAEA_FEAT_CACHE_DIR" 2>/dev/null
echo "  entries: $(find "$SAEA_FEAT_CACHE_DIR" -type f 2>/dev/null | wc -l)"
echo "legacy /home/chao/feat-cache/q4km (MUST NOT BE TOUCHED)"
echo "  entries: $(find /home/chao/feat-cache/q4km -type f 2>/dev/null | wc -l)"
echo "other campaign caches"
echo "  /home/chao/feat-cache/audio2tool-q4km: $(find /home/chao/feat-cache/audio2tool-q4km -type f 2>/dev/null | wc -l) entries"

echo
echo "=== server.log embedding-mode evidence, per session ==="
for SL in "$RD"/$RUN_ID.session-*.server.log; do
  [ -f "$SL" ] || continue
  echo "  --- $(basename "$SL") ---"
  echo "    lines: $(wc -l < "$SL")"
  # sed -n '1,20p' rather than `head -20`: head closes the pipe early and the
  # upstream grep dies of SIGPIPE, which propagates out of this script as 141.
  grep -iE "n_batch|n_ubatch|pooling_type|n_ctx_seq|embeddings enabled|new slot" "$SL" \
    | sed -n '1,20p' | sed 's/^/      /'
  echo "    'not marked as outputs' lines: $(grep -c 'not marked as outputs' "$SL" || true)"
done

echo
echo "=== GPU ==="
nvidia-smi --query-gpu=pstate,clocks.sm,clocks.max.sm,utilization.gpu,memory.used,temperature.gpu --format=csv

echo
echo "=== resident llama-server check (both sessions must be gone) ==="
pgrep -a llama-server || echo "  none running"
echo "ports 8080/8093:"
ss -ltn 2>/dev/null | grep -E ':(8080|8093)' || echo "  (neither bound)"

echo
echo "=== exposure ledger row mentions (count only; consumed must stay 'no') ==="
grep -c "$RUN_ID" "$REPO/docs/exposure-ledger.md"

echo
echo "=== git tree ==="
cd "$REPO" && git status --porcelain && echo "  (clean)" && git log --oneline -1
echo "POSTFLIGHT DONE"
