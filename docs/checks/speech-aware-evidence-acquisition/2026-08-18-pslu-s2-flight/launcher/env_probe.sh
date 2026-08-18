#!/usr/bin/env bash
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pslus2fly/env.sh

echo "=== feature caches ==="
echo "campaign  SAEA_FEAT_CACHE_DIR=$SAEA_FEAT_CACHE_DIR (WARM expected: 63 entries from the parent flight)"
du -sh "$SAEA_FEAT_CACHE_DIR" 2>/dev/null || echo "  (absent)"
echo "  entries: $(find "$SAEA_FEAT_CACHE_DIR" -type f 2>/dev/null | wc -l)"
echo "  dir mtime: $(stat -c '%y' "$SAEA_FEAT_CACHE_DIR" 2>/dev/null)"
echo "legacy /home/chao/feat-cache/q4km (MUST NOT BE TOUCHED)"
du -sh /home/chao/feat-cache/q4km 2>/dev/null || echo "  (absent)"
echo "  entries: $(find /home/chao/feat-cache/q4km -type f 2>/dev/null | wc -l)"
echo "  dir mtime: $(stat -c '%y' /home/chao/feat-cache/q4km 2>/dev/null)"

echo
echo "=== model files (ext4 copies) ==="
ls -l /home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km/

echo
echo "=== runtime receipt pins ==="
python - <<'PY'
import json, pathlib
p = pathlib.Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/docs/receipts/runtime-q4km-featcache.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("build commit:", d.get("llama_cpp_build_commit") or d.get("build_commit"))
for f in d.get("model_files", d.get("files", [])):
    print("  ", f.get("path"), f.get("sha256"))
PY

echo
echo "=== binary + GGUF sha256 verification against the parent attempt-4 pins ==="
python - <<'PY'
import hashlib, json, pathlib
def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()
receipt = json.loads(pathlib.Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/docs/receipts/runtime-q4km-featcache.json"
).read_text(encoding="utf-8"))
parent_binary_sha = "097c96ec5a3f576f378d4d5e103928bf070647fdcc1f015eacb839503e121c68"
binary = "/home/chao/llama.cpp-featcache/build/bin/llama-server"
got = sha256_of(binary)
print(f"binary {binary}")
print(f"  sha256 {got}")
print(f"  == parent attempt-4 pin? {got == parent_binary_sha}")
for f in receipt.get("model_files", receipt.get("files", [])):
    p = f.get("path"); pinned = f.get("sha256")
    if p and pathlib.Path(p).is_file():
        got = sha256_of(p)
        print(f"model {p}")
        print(f"  sha256 {got}")
        print(f"  == receipt pin? {got == pinned}")
PY

echo
echo "=== orphan llama-server check ==="
pgrep -a llama-server || echo "  none running"

echo
echo "=== existing attempt dirs for this run ==="
ls -1 "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-s2-183/" 2>/dev/null || echo "  (no run dir yet)"

echo
echo "=== disk headroom ==="
df -h /home/chao "$SPEECHRL_DATA_DIR" | sed 's/^/  /'
