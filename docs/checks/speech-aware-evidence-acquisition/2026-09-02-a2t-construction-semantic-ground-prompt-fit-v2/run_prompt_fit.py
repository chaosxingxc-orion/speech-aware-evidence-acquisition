"""Measure exact tokenizer fit for the construction-semantic ground."""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
SOURCE = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-executable-ground-prompt-fit-v1/run_prompt_fit.py"
)
SPEC = importlib.util.spec_from_file_location("saea_ground_prompt_fit_v1", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load the frozen prompt-fit runner")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)

RUNNER.EXPERIMENT_ID = "SAEA-A2T-MF-CONSTRUCTION-SEMANTIC-GROUND-PROMPT-FIT-V2"
RUNNER.CHECK_DIR = Path(__file__).resolve().parent
RUNNER.OUTPUT = RUNNER.CHECK_DIR / "prompt-fit-result.json"
RUNNER.HANDBOOK_RELPATH = Path(
    "knowledge/audio2tool/construction-semantic-ground-v2/handbook.txt"
)
RUNNER.HANDBOOK_SHA256 = (
    "04c9c78d03b002faf6c828a5b35f1786aadc7f5da3fee2bf675374e7ea2ea697"
)
RUNNER.BUILD_RECEIPT_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-construction-semantic-ground-build-v2/build-receipt.json"
)
RUNNER.BUILD_RECEIPT_SHA256 = (
    "ad7a96c11fbd633e0d1643d385e44726f5a456c522619720e8dcc3f54da56b0d"
)


if __name__ == "__main__":
    raise SystemExit(RUNNER.main())
