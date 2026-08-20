#!/usr/bin/env bash
# Zero-contact: compile the launcher, import it, and prove the binding-config
# digest + gate-wav bytes are what the machinery pins. Loads no model.
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"
python -m py_compile flight_identity.py control_loaders.py launch_pemb3m_flight.py
echo "COMPILE OK"
python - <<'PY'
import sys
sys.path.insert(0, ".")
import flight_identity as fid
import launch_pemb3m_flight as L  # noqa: F401
import control_loaders  # noqa: F401
import hashlib, json
from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path, data_root
from speech_aware_evidence_acquisition.rails.probes.pemb3m_flight import (
    BINDING_CONFIG_SHA256, binding_config_sha256, assert_binding_config_sha256,
    GATE_CONTACTS_MAX, PLANNED_TOTAL_EMBEDDING_CONTACTS, CEILING_CALLS,
)
lock = load_lock(umbrella_lock_path())
assert_binding_config_sha256(lock)
print("binding_config_sha256 PINNED  :", BINDING_CONFIG_SHA256)
print("binding_config_sha256 LIVE    :", binding_config_sha256(lock))
print("binding_config_sha256 STABLE  :", binding_config_sha256(lock) == binding_config_sha256(lock))
wav = fid.build_gate_wav_bytes()
print("gate wav bytes:", len(wav), "sha256:", hashlib.sha256(wav).hexdigest())
wav2 = fid.build_gate_wav_bytes()
print("gate wav deterministic:", wav == wav2)
print("planned gate contacts:", fid.PLANNED_GATE_CONTACTS, "<= GATE_CONTACTS_MAX", GATE_CONTACTS_MAX)
print("planned scored contacts:", PLANNED_TOTAL_EMBEDDING_CONTACTS)
print("intended total:", PLANNED_TOTAL_EMBEDDING_CONTACTS + fid.PLANNED_GATE_CONTACTS, "<= ceiling", CEILING_CALLS)
print("LCO argv (last):", fid.lco_session_args("last"))
print("LCO argv (mean):", fid.lco_session_args("mean"))
print("qwen3-emb argv:", list(fid.QWEN3_EMB_SERVER_ARGS))
print("LCO gguf:", fid.lco_gguf_relpaths())
print("qwen3 gguf:", fid.qwen3_emb_gguf_relpaths())
print("feat cache dir:", fid.resolve_feat_cache_dir())
print("data_root:", data_root())
# decode the synthetic clip through the control audio path helper (no model)
import numpy as np
w = control_loaders.decode_audio_to_mono_16k(wav)
print("gate wav decodes to:", w.shape, w.dtype, "min/max", float(w.min()), float(w.max()))
PY
