#!/usr/bin/env bash
# What survived attempt 1? Structural only -- counts, dims, hash presence.
# No vector component is ever printed and no two vectors are compared.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pemb3l/env.sh
RUN_ID=SAEA-PROBE-pemb3l-234
exec > >(tee "$SCRATCH/partial-state.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=== resident servers / ports / GPU ==="
pgrep -af llama-server || echo "  (none resident)"
ss -ltn 2>/dev/null | grep -E ':(8080|8093)' || echo "  (neither 8080 nor 8093 bound)"
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
echo
echo "=== attempt files ==="
for f in "$SPEECHRL_DATA_DIR/attempts/$RUN_ID"/*.json; do
  [ -f "$f" ] || continue
  echo "  $(basename "$f")"
  python - "$f" <<'PY'
import json, sys
d = json.loads(open(sys.argv[1], encoding="utf-8").read())
for k in ("state", "reserved", "actual", "failure_reason"):
    v = d.get(k)
    print(f"    {k}: {json.dumps(v, sort_keys=True) if isinstance(v, dict) else v}")
PY
done
echo
echo "=== prior durable spend for the run (every state counts) ==="
python - <<'PY'
import os, pathlib, sys
sys.path.insert(0, os.environ["REPO"] + "/src")
from speech_aware_evidence_acquisition.core.attempts import AttemptStore
from speech_aware_evidence_acquisition.data.lock import data_root
root = data_root()
store = AttemptStore(attempts_root=root / "attempts")
calls, audio = store.prior_actual_usage("SAEA-PROBE-pemb3l-234", exclude_attempt_id=None)
print(f"  prior calls={calls} audio_seconds={audio:.3f}")
print(f"  a fresh attempt flying ONLY l3 (78 / 182.259) would total "
      f"{calls + 78} calls / {audio + 182.259:.3f} audio-s")
print(f"  plan ceiling 234 / 600 ; registered ceiling 260 / 600")
PY
echo
echo "=== arm manifests on the data root (structural) ==="
python - "$SPEECHRL_DATA_DIR" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
base = root / "derived" / "embeddings" / "SAEA-PROBE-pemb3l-234"
if not base.is_dir():
    print("  (sweep root absent)"); raise SystemExit(0)
for arm in ("l1-last-bare", "l2-last-instruct", "l3-mean-instruct"):
    mp = base / arm / "manifest.json"
    if not mp.is_file():
        print(f"  {arm}: MANIFEST ABSENT (not yet flown)"); continue
    d = json.loads(mp.read_text(encoding="utf-8"))
    e = d.get("entries", [])
    kinds = {}
    for x in e:
        kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
    present = sum(1 for x in e if (root / x["relpath"]).is_file())
    print(f"  {arm}: run_id={d.get('run_id')!r} entries={len(e)} by_kind={kinds} "
          f"dims={d.get('dims')} npy_present={present}/{len(e)} "
          f"distinct_sha256={len({x['sha256'] for x in e})}")
PY
echo
echo "=== attempt-1 run dir (vector caches available for replay) ==="
for d in "$SPEECHRL_DATA_DIR/runs/$RUN_ID"/*/; do
  echo "  $d"
  ls -la "$d" | sed 's/^/    /'
done
echo "PARTIAL-STATE DONE"
