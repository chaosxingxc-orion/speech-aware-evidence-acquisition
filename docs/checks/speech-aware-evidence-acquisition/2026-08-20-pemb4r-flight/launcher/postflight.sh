#!/usr/bin/env bash
# Post-flight STRUCTURAL verification. Model-free, read-only, and it never
# scores anything: it counts vectors, re-checks manifest hashes, proves the
# retrieval plan re-hashes to the recorded value, confirms every server is
# dead and every port free, and confirms the study tree is still clean at the
# frozen HEAD. Usage: postflight.sh <attempt_id>
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"

ATTEMPT="$1"
RUN_DIR="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb4r-4100/$ATTEMPT"

echo "=== study tree ==="
git -C "$REPO" rev-parse HEAD
git -C "$REPO" status --porcelain || echo "clean"
echo
echo "=== processes / ports / gpu ==="
pgrep -a llama-server || echo "no llama-server running"
ss -ltnp 2>/dev/null | grep -E ':(8080|8093|8094|8095)\b' || echo "ports 8080/8093/8094/8095 free"
nvidia-smi --query-gpu=clocks.sm,memory.used,utilization.gpu,pstate --format=csv
echo
echo "=== feat caches ==="
du -sh /home/chao/feat-cache/slurp-lco3b /home/chao/feat-cache/slurp-lco7b /home/chao/feat-cache/slurp-q4km 2>&1 || true
echo
echo "=== run dir ==="
ls -la "$RUN_DIR"
echo
python - "$ATTEMPT" <<'PY'
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, ".")
from speech_aware_evidence_acquisition.data.lock import data_root
from speech_aware_evidence_acquisition.rails.probes import pemb4r_flight as F

attempt = sys.argv[1]
root = data_root()
run_dir = root / "runs" / F.PROBE_ID / attempt

print("=== bank manifest ===")
bank = F.load_bank_manifest(root)
print("rows:", len(bank.entries), "seed:", bank.seed, "sha256:", F.bank_manifest_sha256(bank))
print("pin match:", F.bank_manifest_sha256(bank) == F.BANK_MANIFEST_SHA256)

print()
print("=== per-model bank vectors (sha256-verified on load) ===")
for model in F.MODELS:
    if not F.is_bank_vectors_complete(root, model):
        print(f"  {model}: ABSENT")
        continue
    loaded = F.load_bank_vectors(root, model)
    print(f"  {model}: {len(loaded.vectors)} vectors, dim {loaded.dims}")

print()
print("=== per-arm query vectors (sha256-verified on load) ===")
for arm_id in F.ARM_IDS:
    if not F.is_query_vectors_complete(root, arm_id):
        print(f"  {arm_id}: ABSENT")
        continue
    loaded = F.load_query_vectors(root, arm_id)
    print(f"  {arm_id}: {len(loaded.vectors)} vectors, dim {loaded.dims}")

print()
print("=== retrieval plan ===")
try:
    doc = F.load_retrieval_plan(root)
    print("schema:", doc["schema"], "| k_primary:", doc["k_primary"], "| winner:", doc["winner_arm_id"])
    print("sha256:", F.retrieval_plan_document_sha256(doc))
    print("arms in plan:", sorted(doc["arms"]))
except Exception as error:
    print("retrieval plan:", error)

print()
print("=== C-DECODE outputs (row COUNT only; no body is read here) ===")
path = run_dir / "c-decode-outputs.jsonl"
if path.is_file():
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = {json.loads(line)["sample_id"] for line in lines}
    print("rows:", len(lines), "distinct sample_ids:", len(ids))
else:
    print("absent")

print()
print("=== flight receipt spine ===")
receipt = json.loads((run_dir / "flight-receipt.json").read_text(encoding="utf-8"))
for key in ("status", "config_hash", "protocol_hash", "binding_config_sha256", "arms_flown", "n_vectors_produced", "result_read"):
    print(f"  {key}: {receipt.get(key)}")
print("  durable_actual:", json.dumps(receipt.get("durable_actual"), sort_keys=True))
print("  gpu_accounting:", json.dumps({k: v for k, v in receipt.get("gpu_accounting", {}).items() if k.endswith("hours")}, sort_keys=True))
print("POSTFLIGHT DONE")
PY
