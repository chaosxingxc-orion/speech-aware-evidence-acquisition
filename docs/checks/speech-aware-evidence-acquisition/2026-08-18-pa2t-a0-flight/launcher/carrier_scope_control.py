"""Control: is the audio2tool refusal carrier-specific, or does my dry-run
harness refuse everything? Runs the SAME gate method against the slurp carrier
using the already-consumed P-SLU row's own registered identity.

Model-free: _resolve_carrier_dataset_entry reads only the umbrella lock.
"""
from pathlib import Path
REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
from speech_aware_evidence_acquisition.contracts import FrozenCoreGate
from speech_aware_evidence_acquisition.core.config import model_lock_key, runtime_receipt_relpath
from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from flight_identity import build_values

lock = load_lock(umbrella_lock_path())
values = build_values(REPO)
gate = FrozenCoreGate.for_study_repo(
    REPO, data_root(), Path("/home/chao"),
    runtime_receipt_relpath=runtime_receipt_relpath(values),
    expected_model_lock_key=model_lock_key(values),
)
for key in ("slurp", "earnings21-original", "conec", "audio2tool"):
    try:
        entry = gate._resolve_carrier_dataset_entry(key, lock)
        print(f"{key:22s} -> IN SCOPE   profiles={entry.get('profiles')} lifecycle={entry.get('lifecycle')}")
    except Exception as error:
        print(f"{key:22s} -> REFUSED    {type(error).__name__}: {error}")
