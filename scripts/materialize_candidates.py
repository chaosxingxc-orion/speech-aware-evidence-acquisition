#!/usr/bin/env python3
"""Offline materializer for the ``derived-candidates`` evidence source.

Model-free, deterministic: reads a draft run's newest attempt outputs.jsonl,
retrieval-gates a per-sample candidate vocabulary (``--pack-source``) against
its stitched hypothesis via ``core.retrieval.retrieve``, and writes the
top-``k`` one-per-line under ``$SPEECHRL_DATA_DIR/derived/evidence-
candidates/<out-id>/<sample_id>.candidates.txt`` plus a ``manifest.json``.
Never opens a model session. See
``speech_aware_evidence_acquisition.core.candidate_materializer`` for the
implementation.

Usage:
    python scripts/materialize_candidates.py \\
        --draft-run SAEA-E-00X-draft \\
        --pack-source conec-contexts \\
        --k 20 --min-score 0.6 \\
        --out-id mat-2026-08-12-e00x

    python scripts/materialize_candidates.py --dry-run \\
        --draft-run SAEA-E-00X-draft --pack-source conec-names \\
        --k 10 --min-score 0.5 --out-id mat-dry-run-check
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.candidate_materializer import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
