"""Model-free: does the real FrozenCoreGate admit Audio2Tool media identity?

Adapted from the archived P-A2T Stage-2 probe (``docs/checks/
speech-aware-evidence-acquisition/2026-08-18-a2t-s2-flight/launcher/
probe_d1.py``), itself adapted from Stage-1 A0. The samples offered to the gate
are drawn from THIS flight's own 120-sample headroom set (resolved through
``Audio2ToolAdapter.load_split('discovery')`` then filtered by the frozen
headroom manifest), so a PASS here proves the D1 closure admits the very samples
this Stage-2b flight will send -- the same 120 ids Stage-2 already flew.
"""

from pathlib import Path
import json
import sys

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flight_identity import build_values  # noqa: E402
from speech_aware_evidence_acquisition.contracts import FrozenCoreGate  # noqa: E402
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    model_lock_key,
    runtime_receipt_relpath,
)
from speech_aware_evidence_acquisition.data.carriers import (  # noqa: E402
    resolve_media_identity_carrier,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_s2b_flight import (  # noqa: E402
    load_headroom_manifest,
)

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/a2t-s2b-flight.json").read_text(encoding="utf-8")
)

lock = load_lock(umbrella_lock_path())
root = data_root()
values = build_values(REPO)
gate = FrozenCoreGate.for_study_repo(
    REPO,
    root,
    Path("/home/chao"),
    runtime_receipt_relpath=runtime_receipt_relpath(values),
    expected_model_lock_key=model_lock_key(values),
)
print("resolve_media_identity_carrier('audio2tool') ->", resolve_media_identity_carrier("audio2tool"))

headroom = load_headroom_manifest(REPO / str(FLIGHT_CFG["headroom_manifest"]))
samples = Audio2ToolAdapter(lock, root, repo_root=REPO).load_split("discovery")
by_id = {s.sample_id: s for s in samples}
headroom_samples = [by_id[sid] for sid in headroom.sample_ids]
print(f"headroom samples resolved: {len(headroom_samples)}/{len(headroom.sample_ids)}")

first, last = headroom_samples[0], headroom_samples[-1]
offered = {s.sample_id: (s.media_relpath, s.audio_seconds) for s in (first, last)}
print(f"offering 2 real headroom samples: {sorted(offered)}")
try:
    gate.verify_media_identity("audio2tool", offered)
    print("verify_media_identity('audio2tool') on 2 headroom samples: PASS")
except Exception as error:  # noqa: BLE001
    print(f"verify_media_identity('audio2tool'): REFUSED -> {type(error).__name__}: {error}")
    raise SystemExit(1)

# The whole 120 at once -- this flight sends every one of them, twice.
all_offered = {s.sample_id: (s.media_relpath, s.audio_seconds) for s in headroom_samples}
try:
    gate.verify_media_identity("audio2tool", all_offered)
    print(f"verify_media_identity('audio2tool') on all {len(all_offered)} headroom samples: PASS")
except Exception as error:  # noqa: BLE001
    print(f"verify_media_identity(all 120): REFUSED -> {type(error).__name__}: {error}")
    raise SystemExit(1)

# A sample id that is NOT in the frozen receipt must be refused (fail-closed
# semantics the partial-closure commit relies on).
try:
    gate.verify_media_identity(
        "audio2tool", {"tier1_direct:999999": (first.media_relpath, first.audio_seconds)}
    )
    print("NEGATIVE CONTROL FAILED: an unlisted sample id was admitted")
    raise SystemExit(1)
except SystemExit:
    raise
except Exception as error:  # noqa: BLE001
    print(f"negative control (unlisted id): correctly refused -> {type(error).__name__}")
