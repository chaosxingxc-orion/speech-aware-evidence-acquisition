#!/usr/bin/env bash
# Structural audit of the 11 registered silence-swap slices, and the reason the
# server log shows 10 encodes rather than 11. Model-free; opens no response.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri/abst
source "$SDIR/env.sh"
exec > >(tee "$SCRATCH/slice-audit.log") 2>&1

RD="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-abst-44/attempt-20260819T160757Z-9425ce"
SLICE_ROOT="$SPEECHRL_DATA_DIR/derived/obs-slices/SAEA-PROBE-a2t-abst-44"

echo "=== slice tree ==="
if [ -d "$SLICE_ROOT" ]; then
  echo "  root: $SLICE_ROOT"
  echo "  files: $(find "$SLICE_ROOT" -type f | wc -l)"
  echo "  bytes: $(du -sh "$SLICE_ROOT" | cut -f1)"
else
  echo "  MISSING: $SLICE_ROOT"
fi

echo
echo "=== per-swap structure: duration, byte size, sha256 (silent WAVs of equal duration are byte-identical) ==="
python - "$RD" "$SLICE_ROOT" <<'PY'
import collections
import hashlib
import json
import pathlib
import sys

rd = pathlib.Path(sys.argv[1])
root = pathlib.Path(sys.argv[2])
data_root = pathlib.Path("/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data")
r = json.loads((rd / "flight-receipt.json").read_text(encoding="utf-8"))
swaps = r["silence_swap"]
plan = json.loads((rd / "SAEA-PROBE-a2t-abst-44.cell-plan.json").read_text(encoding="utf-8"))
measurement = json.loads(
    (pathlib.Path(sys.argv[0]).parent / "split-measurement.json").read_text(encoding="utf-8")
) if False else None

digests = collections.Counter()
sizes = collections.Counter()
print(f"  {len(swaps)} registered swaps")
for sample_id, relpath in sorted(swaps.items()):
    p = data_root / relpath
    blob = p.read_bytes()
    d = hashlib.sha256(blob).hexdigest()
    digests[d] += 1
    sizes[len(blob)] += 1
    print(f"    {sample_id:34s} {len(blob):>9d} bytes  sha256 {d[:16]}...")
print()
print(f"  distinct slice byte-sizes:  {len(sizes)}")
print(f"  distinct slice sha256:      {len(digests)}")
dupes = {d: n for d, n in digests.items() if n > 1}
print(f"  byte-identical slice groups: {len(dupes)} (sizes {sorted(n for n in dupes.values())})")
print(
    "  => the feature cache encodes one entry per DISTINCT slice, so "
    f"{len(digests)} encode(s) for {len(swaps)} swaps is the expected count"
)
PY

echo
echo "=== server log encode lines (count only, no content) ==="
grep -ci "encoding" "$RD/SAEA-PROBE-a2t-abst-44.server.log" || true

echo
echo "=== feature cache entry delta ==="
echo "  audio2tool-q4km entries now: $(find /home/chao/feat-cache/audio2tool-q4km -type f | wc -l) (480 before this flight)"
echo "SLICE AUDIT DONE"
