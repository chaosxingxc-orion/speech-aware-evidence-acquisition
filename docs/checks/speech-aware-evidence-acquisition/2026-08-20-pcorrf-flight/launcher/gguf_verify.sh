#!/usr/bin/env bash
# Runtime-receipt pin verification: llama.cpp build commit + binary sha256 +
# per-file GGUF sha256, PLUS an umbrella-lock cross-check (mission instruction:
# "verify GGUF/binary pins via the umbrella lock"). Model-free: hashes bytes on
# disk and reads two JSON files; spawns nothing.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf
source "$SDIR/env.sh"

python - <<'PY' 2>&1 | tee "$SDIR/gguf-verify.log"
import hashlib
import json
import pathlib
import sys

sys.path.insert(
    0,
    "/mnt/c/Users/35686/AppData/Local/Temp/claude/"
    "D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/"
    "6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pcorrf",
)

REPO = pathlib.Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
receipt = json.loads((REPO / "docs/receipts/runtime-q4km-featcache.json").read_text(encoding="utf-8"))
lc = receipt["llama_cpp"]
print("=== runtime receipt pins (schema saea-runtime-receipt-v2) ===")
print("study:", receipt["study"], "| model_lock_key:", receipt["model_lock_key"])
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
print("=== binary sha256 verification (ext4 copy vs receipt pin) ===")
binary = runtime_root / lc["binary_path"]
got = sha256_of(binary)
print(f"binary {binary}")
print(f"  sha256 {got}")
print(f"  == receipt pin? {got == lc['binary_sha256']}")
ok = got == lc["binary_sha256"]

print()
print("=== per-file GGUF sha256 verification (ext4 copies vs receipt pins) ===")
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
print("=== umbrella lock cross-check (docs/datasets.lock.json is the single live source of model identity) ===")
from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path  # noqa: E402

lock_path = umbrella_lock_path()
lock = load_lock(lock_path)
print("lock path:", lock_path)
entries = [m for m in lock["models"] if m.get("name") == receipt["model_lock_key"]]
if len(entries) != 1:
    print(f"  LOCK ENTRY RESOLUTION FAILED: {len(entries)} entries named {receipt['model_lock_key']!r}")
    ok = False
else:
    entry = entries[0]
    blob = json.dumps(entry)
    print(f"  lock entry: name={entry['name']} status={entry['status']} files={entry['files']} "
          f"size_bytes={entry['size_bytes']}")
    print(f"  lock revision: {entry['revision']}")
    print(f"  lock local_subdir: {entry['local_subdir']}")
    for f in receipt["gguf_files"]:
        present = f["sha256"] in blob
        ok = ok and present
        print(f"  receipt GGUF sha256 {f['sha256'][:16]}... recorded in the lock entry? {present}")
    # The receipt's own model_lock_key must be the key the flight's gate will
    # demand (core.config.model_lock_key of the composed values).
    from speech_aware_evidence_acquisition.core.config import model_lock_key  # noqa: E402
    from flight_identity import build_values  # noqa: E402
    demanded = model_lock_key(build_values(REPO))
    same = demanded == receipt["model_lock_key"]
    ok = ok and same
    print(f"  flight-composed model_lock_key: {demanded} == receipt key? {same}")

print()
print("BINARY+GGUF VERIFICATION:", "PASS" if ok else "FAIL")
PY
grep -q "BINARY+GGUF VERIFICATION: PASS" "$SDIR/gguf-verify.log"
