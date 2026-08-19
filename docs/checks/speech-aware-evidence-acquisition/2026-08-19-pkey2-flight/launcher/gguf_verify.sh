#!/usr/bin/env bash
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pkey2fly/env.sh

echo "=== runtime receipt pins (schema saea-runtime-receipt-v2) ==="
python - <<'PY'
import json, pathlib, hashlib
receipt = json.loads(pathlib.Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/docs/receipts/runtime-q4km-featcache.json"
).read_text(encoding="utf-8"))
lc = receipt["llama_cpp"]
print("llama.cpp build commit:", lc["build_commit"], "|", lc["reported_build"])
print("binary pin:", lc["binary_path"], lc["binary_sha256"])

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()

runtime_root = pathlib.Path("/home/chao")
print()
print("=== binary sha256 verification (ext4 copy vs receipt pin + s2-precedent pin) ===")
binary = runtime_root / lc["binary_path"]
got = sha256_of(binary)
print(f"binary {binary}")
print(f"  sha256 {got}")
print(f"  == receipt pin? {got == lc['binary_sha256']}")
print(f"  == s2-precedent pin 097c96ec...? {got == '097c96ec5a3f576f378d4d5e103928bf070647fdcc1f015eacb839503e121c68'}")
print()
print("=== per-file GGUF sha256 verification (ext4 copies vs receipt pins) ===")
ok = got == lc["binary_sha256"]
for f in receipt["gguf_files"]:
    p = runtime_root / f["path"]
    got = sha256_of(p)
    match = got == f["sha256"]
    ok = ok and match
    print(f"{p}")
    print(f"  bytes {p.stat().st_size} (pin {f['bytes']}, match={p.stat().st_size == f['bytes']})")
    print(f"  sha256 {got}")
    print(f"  == receipt pin? {match}")
print()
print("BINARY+GGUF VERIFICATION:", "PASS" if ok else "FAIL")
PY
