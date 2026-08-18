"""Model-free: does the real FrozenCoreGate admit Audio2Tool media identity?

Adapted from the archived P-SLU probe (``.../2026-08-17-pslu-flight/launcher/
probe_d1.py``). The one substantive change: the sample offered to the gate is
not hand-typed -- it is drawn from the REAL frozen 400-item discovery split
through ``Audio2ToolAdapter.load_split('discovery')``, so a PASS here proves
the D1 closure admits the very samples this flight will send.
"""

from pathlib import Path
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

samples = Audio2ToolAdapter(lock, root, repo_root=REPO).load_split("discovery")
first, last = samples[0], samples[-1]
offered = {
    s.sample_id: (s.media_relpath, s.audio_seconds) for s in (first, last)
}
print(f"offering 2 real frozen-split samples: {sorted(offered)}")
try:
    gate.verify_media_identity("audio2tool", offered)
    print("verify_media_identity('audio2tool'): PASS")
except Exception as error:  # noqa: BLE001
    print(f"verify_media_identity('audio2tool'): REFUSED -> {type(error).__name__}: {error}")
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
