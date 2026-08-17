"""Model-free: does the real FrozenCoreGate admit SLURP media identity?"""
from pathlib import Path
import sys
REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from flight_identity import build_values
from speech_aware_evidence_acquisition.contracts import FrozenCoreGate
from speech_aware_evidence_acquisition.core.config import model_lock_key, runtime_receipt_relpath
from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path
from speech_aware_evidence_acquisition.data.carriers import resolve_media_identity_carrier

lock = load_lock(umbrella_lock_path()); root = data_root()
values = build_values(REPO)
gate = FrozenCoreGate.for_study_repo(
    REPO, root, Path("/home/chao"),
    runtime_receipt_relpath=runtime_receipt_relpath(values),
    expected_model_lock_key=model_lock_key(values),
)
print("resolve_media_identity_carrier('slurp') ->", resolve_media_identity_carrier("slurp"))
try:
    gate.verify_media_identity(
        "slurp",
        {"slurp:devel:005518:audio-1490203960": ("repos/slurp/scripts/audio/slurp_real/audio-1490203960.flac", 3.0)},
    )
    print("verify_media_identity('slurp'): PASS")
except Exception as error:
    print(f"verify_media_identity('slurp'): REFUSED -> {type(error).__name__}: {error}")
