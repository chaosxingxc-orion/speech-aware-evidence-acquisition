#!/usr/bin/env python3
"""P-PHON failure-class decomposition pinned offline read suite entry point.

Model-free: reads five ALREADY-CONSUMED flight attempt directories (pslu
A0+A3, pslu-s2 A1'r, a2t A0, a2t-s2b B1/B2, a2t-s2c C1/C2/C3 -- the SAME
``outputs.jsonl`` shapes ``scripts.pslu_read``/``scripts.pslu_s2_read``/
``scripts.a2t_read``/``scripts.a2t_s2b_read``/``scripts.a2t_s2c_read``
already read) and classifies every A0-failed SLURP slot / A2T argument into
MISSING/EQUIV-FORMAT/NEAR-MISS/FAR-WRONG, mechanically evaluating the
SLURP-A3 SPEECH-SNAP-PRESENT/FORMAT-DOMINANT/MIXED verdict and A1'r
concordance. Never opens a model session; never mutates any attempt
directory. See ``speech_aware_evidence_acquisition.analysis.pphon_decomp``
for the implementation and
``docs/readiness/2026-08-18-pphon-preregistration-REGISTERED.md`` for the
pre-registered classes and verdict rules this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before any
work happens.

Usage:
    python scripts/pphon_decomp.py \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/attempt-<id>" \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-s2-183/attempt-<id>" \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pa2t-a0-120/attempt-<id>" \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2b-120/attempt-<id>" \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2c-120/attempt-<id>" \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/2026-08-18-pphon-decomp
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.pphon_decomp import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
