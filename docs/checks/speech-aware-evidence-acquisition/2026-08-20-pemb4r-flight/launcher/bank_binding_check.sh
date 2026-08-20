#!/usr/bin/env bash
# Model-free preflight proof: bank DOUBLE-DERIVATION bit-identity against the
# pinned sha256, binding-config hash stability + pin, T0 registry pin, ledger
# ceilings. Zero model contact, zero GPU.
source "$(dirname "$0")/env.sh"
cd "$REPO"
python - <<'PY'
import hashlib, json, time
from pathlib import Path

from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path
from speech_aware_evidence_acquisition.rails.probes import pemb4r_flight as F
from speech_aware_evidence_acquisition.rails.probes.pfew_flight import load_train_demo_pool
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import canonical_scenario_labels

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
lock = load_lock(umbrella_lock_path())
root = data_root()

print("== binding config ==")
a = F.binding_config_sha256(lock)
b = F.binding_config_sha256(lock)
print("computed :", a)
print("stable   :", a == b)
print("pinned   :", F.BINDING_CONFIG_SHA256)
print("MATCH    :", a == F.BINDING_CONFIG_SHA256)
F.assert_binding_config_sha256(lock)

print()
print("== model bindings resolved from the umbrella lock ==")
for model in F.MODELS:
    binding = F.resolve_model_binding(lock, F.MODEL_LOCK_KEY[model])
    print(f"  {model:5s} {F.MODEL_LOCK_KEY[model]:32s} lifecycle={binding['lifecycle']!r} "
          f"files={binding['files_count']} size={binding['size_bytes']} "
          f"per_file_sha256={'yes' if binding['file_hashes'] else 'no'}")

print()
print("== bank double derivation ==")
rosters = load_pslu_rosters(REPO / "configs/probes/g0-binding/pslu-rosters-train-only.json")
labels = canonical_scenario_labels(rosters)
print("canonical labels:", len(labels))
t0 = time.time()
pool = load_train_demo_pool(lock, root)
print(f"train pool loaded in {time.time()-t0:.1f}s: {len(pool)} scenarios, "
      f"{sum(len(v) for v in pool.values())} candidates")
counts = {label: len(pool.get(label, ())) for label in labels}
print("min per-label candidates:", min(counts.items(), key=lambda kv: kv[1]))
bank_a = F.build_bank_table(pool, labels)
bank_b = F.build_bank_table(pool, labels)
F.validate_bank_table(bank_a)
F.validate_bank_table(bank_b)
sha_a = F.bank_manifest_sha256(bank_a)
sha_b = F.bank_manifest_sha256(bank_b)
print("derivation A sha256:", sha_a)
print("derivation B sha256:", sha_b)
print("BIT-IDENTICAL      :", sha_a == sha_b)
print("pinned             :", F.BANK_MANIFEST_SHA256)
print("MATCH              :", sha_a == F.BANK_MANIFEST_SHA256)
F.assert_bank_manifest_sha256(bank_a)
print("rows:", len(bank_a.entries), "seed:", bank_a.seed, "per_scenario:", bank_a.per_scenario_n)
print("sample row (text only, no label ever embedded):", bank_a.entries[0].bank_id,
      repr(bank_a.entries[0].text[:60]))

print()
print("== T0 registry pin ==")
reg = root / F.PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH
print("relpath:", F.PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH)
print("exists :", reg.is_file())
print("sha256 :", hashlib.sha256(reg.read_bytes()).hexdigest())
print("pinned :", F.PKEY2_338_TRANSCRIPT_REGISTRY_SHA256)

print()
print("== ledger row ==")
ledger_text = (REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
rows = [line for line in ledger_text.splitlines() if f"| {F.PROBE_ID} |" in line]
print("rows found:", len(rows))
cells = [c.strip() for c in rows[0].strip().strip("|").split("|")]
print("consumed cell:", cells[8])
print("ledger ceilings: calls", cells[9], "audio", cells[10], "gpu", cells[11])
print("machinery ceilings:", F.CEILING_CALLS, F.CEILING_AUDIO_SECONDS, F.CEILING_GPU_HOURS)

print()
print("== planned contacts ==")
print("bank", F.PLANNED_BANK_CONTACTS, "audio-q", F.PLANNED_AUDIO_QUERY_CONTACTS,
      "text-q", F.PLANNED_TEXT_QUERY_CONTACTS, "c-decode", F.PLANNED_C_DECODE_CONTACTS,
      "gates<=", F.GATE_CONTACTS_MAX, "=> plan", F.DEFAULT_PLANNED_MODEL_CALLS)
print("planned audio seconds:", F.DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS)

print()
print("== run dir absence ==")
for rel in (f"runs/{F.PROBE_ID}", f"derived/embeddings/{F.PROBE_ID}", f"attempts/{F.PROBE_ID}"):
    print(f"  {rel}: exists={ (root/rel).exists() }")
print("BANK/BINDING CHECK DONE")
PY
