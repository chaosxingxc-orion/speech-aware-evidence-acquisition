#!/usr/bin/env python3
"""Owner decision D-3: offline/deferred entity-class WER scoring entry point.

Model-free: reads an already-produced, FINALIZED attempt's persisted outputs
(run-manifest.json + outputs.jsonl) under a stable run_dir and scores them
through the SAME registered ``entity-wer`` scorer the in-run path uses. Never
opens a model session; never modifies the attempt directory. See
``speech_aware_evidence_acquisition.analysis.entity_wer_offline`` for the
implementation.

Usage:
    python scripts/score_entity_wer.py --run SAEA-E-003-b2a-conec

Writes its verdict to
``$SPEECHRL_DATA_DIR/derived/entity-wer/<run_id>/<run_id>.<attempt_id>.entity-wer.json``.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.entity_wer_offline import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
