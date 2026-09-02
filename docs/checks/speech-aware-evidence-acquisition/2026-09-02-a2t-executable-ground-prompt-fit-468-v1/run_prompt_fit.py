"""Run the preregistered zero-contact 468-token prompt-fit successor."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[4]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    dev100_reviewer_audit as audit,
)
from speech_aware_evidence_acquisition.analysis.a2t_ground_prompt_fit_inheritance import (  # noqa: E402
    reprice_prompt_fit,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    require_clean_study_repo,
)


EXPERIMENT_ID = "SAEA-A2T-MF-EXECUTABLE-GROUND-PROMPT-FIT-468-V1"
CHECK_DIR = Path(__file__).resolve().parent
OUTPUT = CHECK_DIR / "prompt-fit-result.json"
PROMPT_FIT = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-executable-ground-prompt-fit-v1/prompt-fit-result.json"
)
PROMPT_FIT_SHA256 = "627e0efb01595eb45751a448fcc2b9029ce35f38f73810107506226f86a55c63"
PREPROCESSING = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-ground-qual-104-preprocess/preprocess-report.json"
)
PREPROCESSING_SHA256 = "c2120c9500ac943dc485d1953087965312e13f491ee850775df23347c4dccb0a"
PROMOTION_RECEIPT_SHA256 = (
    "b350567a6dd8b5d9021725756424f2b6ae99803c8c0327901c724fe3ebe8a47f"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise RuntimeError("PYTHONDONTWRITEBYTECODE=1 is required")
    if OUTPUT.exists():
        raise RuntimeError("prompt-fit result already exists")
    study_commit = require_clean_study_repo(REPO)
    attempts = audit.arm_offline_guard()
    if _sha256(PROMPT_FIT) != PROMPT_FIT_SHA256:
        raise RuntimeError("source prompt-fit result drifted")
    if _sha256(PREPROCESSING) != PREPROCESSING_SHA256:
        raise RuntimeError("preprocess report drifted")
    prompt_fit = json.loads(PROMPT_FIT.read_text(encoding="utf-8"))
    preprocessing = json.loads(PREPROCESSING.read_text(encoding="utf-8"))
    if preprocessing.get("promotion_receipt_sha256") != PROMOTION_RECEIPT_SHA256:
        raise RuntimeError("promotion receipt binding drifted")
    result = reprice_prompt_fit(prompt_fit, preprocessing)
    if attempts.count:
        raise RuntimeError(
            "offline guard observed outbound targets: %r" % (attempts.targets,)
        )
    output = {
        "schema": "saea-a2t-executable-ground-prompt-fit-468-result-v1",
        "study": "speech-aware-evidence-acquisition",
        "experiment_id": EXPERIMENT_ID,
        "execution_profile": "model-free-check",
        "study_commit": study_commit,
        "source_hashes": {
            "prompt_fit_result": PROMPT_FIT_SHA256,
            "preprocess_report": PREPROCESSING_SHA256,
            "promotion_receipt": PROMOTION_RECEIPT_SHA256,
        },
        "bounds": result,
        "contacts": {
            "model": 0,
            "tokenizer": 0,
            "audio_decode": 0,
            "network": 0,
            "retriever": 0,
            "embedding": 0,
            "scorer": 0,
            "gpu_hours": 0.0,
            "outbound_attempts": attempts.count,
            "outbound_targets": list(attempts.targets),
        },
        "gold_read": False,
        "test_read": False,
        "decision": (
            "permit separately preregistered ground-qualification implementation "
            "and zero-contact preflight only"
        ),
        "engineering_scope": {
            "complete_manifest_outer_parallel_scoring": True,
            "official_scorer_single_process_per_manifest": True,
            "dataset_sharding": False,
            "network_jitter_testing": False,
        },
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
