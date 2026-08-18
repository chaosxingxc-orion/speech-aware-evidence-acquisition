#!/usr/bin/env python3
"""P-A2T selection-loss decomposition pinned offline read suite entry point.

Model-free: reads three ALREADY-CONSUMED flight attempt directories (Stage-2
S1p/S2/S4/N0r, Stage-2b B1/B2, Stage-2c C1/C2/C3 -- the SAME ``outputs.jsonl``
/ ``flight-receipt.json`` / ``{RUN_ID}.arm-plan.json`` shapes ``scripts.
a2t_s2_read`` / ``scripts.a2t_s2b_read`` / ``scripts.a2t_s2c_read`` already
read) and classifies every A0-correct-to-arm-incorrect loss into
DRAGGED-TO-SUPPLIED / DRIFTED-OTHER / EMPTY / PARSE-FAIL, mechanically
evaluating the B2 DRAG-CONFIRMED / DRIFT-CONFIRMED / MIXED verdict against
the N0r reference shape. Never opens a model session; never mutates any
attempt directory. See
``speech_aware_evidence_acquisition.analysis.a2t_loss_decomp`` for the
implementation and
``docs/readiness/2026-08-18-a2t-loss-decomp-preregistration-REGISTERED.md``
for the pre-registered classes and verdict rules this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before any
work happens.

Usage:
    python scripts/a2t_loss_decomp.py \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2-120/attempt-<id>" \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2b-120/attempt-<id>" \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2c-120/attempt-<id>" \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-loss-decomp
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.a2t_loss_decomp import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
