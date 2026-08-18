#!/usr/bin/env bash
# Model-free, read-only: which of the two governed SLURP path authorities
# actually holds the flown devel audio? Touches no project data.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pslufly3/env.sh

set +e
D="$SPEECHRL_DATA_DIR"
FILE=audio-1495375974.flac   # the media of request 1, which the rail refused

echo "=== lock local_subdir root: repos/slurp/scripts/audio ==="
ls -ld "$D/repos/slurp/scripts/audio" 2>&1
echo "  subdirs:"; ls -1 "$D/repos/slurp/scripts/audio" 2>&1 | head -10
echo "  is the request-1 file there (slurp_real)?"
ls -l "$D/repos/slurp/scripts/audio/slurp_real/$FILE" 2>&1
echo "  is it there flat?"
ls -l "$D/repos/slurp/scripts/audio/$FILE" 2>&1

echo
echo "=== loader root (annotations.governed_copy parent): datasets/slurp ==="
ls -ld "$D/datasets/slurp" 2>&1
echo "  subdirs:"; ls -1 "$D/datasets/slurp" 2>&1 | head -10
echo "  request-1 file:"
ls -l "$D/datasets/slurp/slurp_real/$FILE" 2>&1

echo
echo "=== symlink / same-inode question ==="
echo "readlink -f datasets/slurp        : $(readlink -f "$D/datasets/slurp")"
echo "readlink -f repos/slurp/scripts/audio: $(readlink -f "$D/repos/slurp/scripts/audio")"

echo
echo "=== counts ==="
echo "datasets/slurp/slurp_real       : $(ls -1 "$D/datasets/slurp/slurp_real" 2>/dev/null | wc -l)"
echo "repos/slurp/scripts/audio/slurp_real: $(ls -1 "$D/repos/slurp/scripts/audio/slurp_real" 2>/dev/null | wc -l)"

echo
echo "=== comparison carrier: earnings21-original (a carrier that flies today) ==="
python - <<'PY'
import json, pathlib
from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path, lock_entry
lock = load_lock(umbrella_lock_path())
for key in ("slurp", "earnings21-original", "conec"):
    try:
        e = lock_entry(lock, key)
    except Exception as exc:
        print(f"{key}: <{exc}>"); continue
    ann = e.get("annotations") if isinstance(e.get("annotations"), dict) else {}
    print(f"{key}: local_subdir={e.get('local_subdir')!r} governed_copy={ann.get('governed_copy')!r}")
PY

echo
echo "=== post-abort state ==="
echo "orphan llama-server:"; pgrep -a llama-server || echo "  none"
echo "campaign featcache entries: $(find "$SAEA_FEAT_CACHE_DIR" -type f 2>/dev/null | wc -l)  size: $(du -sh "$SAEA_FEAT_CACHE_DIR" 2>/dev/null | cut -f1)"
echo "legacy q4km size: $(du -sh /home/chao/feat-cache/q4km 2>/dev/null | cut -f1)  entries: $(find /home/chao/feat-cache/q4km -type f 2>/dev/null | wc -l)  mtime: $(stat -c '%y' /home/chao/feat-cache/q4km)"
echo "attempt dir:"; ls -l "$D/runs/SAEA-PROBE-pslu-n60/attempt-20260818T004057Z-7edb9c/"
echo "obs-slices written:"; find "$D/derived/obs-slices/SAEA-PROBE-pslu-n60" -type f 2>/dev/null | sed 's/^/  /'
