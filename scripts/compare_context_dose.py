#!/usr/bin/env python3
"""R4 (SAEA-E-002) context-dose three-arm WER comparison entry point.

Model-free: reads already-produced run bundles (run-manifest.json +
outputs.jsonl) under the three arms' stable run_dirs and reuses the frozen
scoring stack to report per-sample/corpus/macro WER and the pre-registered
paired contrasts. Never opens a model session. See
``speech_aware_evidence_acquisition.analysis.context_dose`` for the
implementation and ``docs/readiness/2026-08-09-r4-analysis-plan.md`` for the
pre-registered statistics.

Usage:
    python scripts/compare_context_dose.py \\
        --nocontext-run-dir  "$SPEECHRL_DATA_DIR/runs/SAEA-E-002-r4-nocontext" \\
        --matched-run-dir    "$SPEECHRL_DATA_DIR/runs/SAEA-E-002-r4-matched" \\
        --mismatched-run-dir "$SPEECHRL_DATA_DIR/runs/SAEA-E-002-r4-mismatched" \\
        --output docs/checks/speech-aware-evidence-acquisition/r4-context-dose-comparison.json
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.context_dose import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
