"""Attempt-4 pre-flight confinement sanity (READ-ONLY, model-free).

Reproduces exactly what launch_pslu_flight.py does to obtain carrier_root
(``data.lock.asset_dir(lock, SLURP_LOCK_KEY, root)`` -- the same call
``core/driver/run.py`` makes) and confirms that after umbrella lock commit
344dfdc it agrees with the loader-emitted ``media_relpath`` of the request-1
sample, i.e. the payload media-confinement rail that refused attempt 3 now
passes.

Reads no response, contacts no model.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import (  # noqa: E402
    SLURP_LOCK_KEY,
    SlurpAdapter,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    load_pslu_sample_manifest,
    select_pslu_samples,
)

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/pslu-flight.json").read_text(encoding="utf-8")
)

lock = load_lock(umbrella_lock_path())
root = data_root()

print("umbrella lock:", umbrella_lock_path())
print("data_root:    ", root)

raw = json.loads(umbrella_lock_path().read_text(encoding="utf-8"))
raw_entry = next(
    e
    for e in raw.get("entries", raw.get("datasets", []))
    if e.get("name") == SLURP_LOCK_KEY
)
print()
print("=== lock entry (slurp) ===")
print("  local_subdir:   ", raw_entry.get("local_subdir"))
print("  governed_copy:  ", (raw_entry.get("annotations") or {}).get("governed_copy"))

carrier_root = asset_dir(lock, SLURP_LOCK_KEY, root)
print()
print("=== carrier_root, resolved the way core/driver/run.py does ===")
print("  asset_dir(...):  ", carrier_root)
print("  realpath:        ", carrier_root.resolve())
print("  exists:          ", carrier_root.is_dir())

expected = root / "datasets/slurp"
print("  == $SPEECHRL_DATA_DIR/datasets/slurp ?", carrier_root.resolve() == expected.resolve())

adapter = SlurpAdapter(lock, root, repo_root=REPO)
manifest = load_pslu_sample_manifest(REPO / FLIGHT_CFG["sample_manifest"])
print()
print("loading devel split (model-free sha256 pass) ...", flush=True)
samples = select_pslu_samples(adapter.load_split("devel"), manifest)
print(f"  frozen sample set: {len(samples)} samples")

first = samples[0]
print()
print("=== request-1 sample ===")
print("  sample_id:      ", first.sample_id)
print("  media_relpath:  ", first.media_relpath)
abs_media = (root / first.media_relpath).resolve()
print("  absolute:       ", abs_media)
print("  exists:         ", abs_media.is_file())
inside = str(abs_media).startswith(str(carrier_root.resolve()) + "/")
print("  INSIDE carrier_root:", inside)

print()
print("=== all 60 media_relpaths confined? ===")
bad = [
    s.sample_id
    for s in samples
    if not str((root / s.media_relpath).resolve()).startswith(str(carrier_root.resolve()) + "/")
]
print(f"  outside carrier_root: {len(bad)}/{len(samples)}")
if bad:
    print("  offenders:", bad[:5])

print()
print("=== build_payload_binding (the rail that refused attempt 3) ===")
binding = build_payload_binding(
    carrier_lock_key=SLURP_LOCK_KEY,
    samples=samples,
    data_root=root,
    carrier_root=carrier_root,
)
print("  binding constructed OK:", type(binding).__name__)
print("  carrier_root on binding:", getattr(binding, "carrier_root", "<n/a>"))
print()
print("CONFINEMENT SANITY:", "PASS" if inside and not bad else "FAIL")
