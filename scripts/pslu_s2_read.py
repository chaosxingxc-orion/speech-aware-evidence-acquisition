#!/usr/bin/env python3
"""P-SLU Stage-2 follow-up pinned offline read suite entry point.

Model-free: reads an already-produced flight attempt directory
(``outputs.jsonl`` + ``flight-receipt.json``, the shape
``rails.probes.pslu_s2_flight.run_pslu_s2_flight`` writes) and reuses the
frozen SLURP scoring stack plus the frozen roster/filler-construction
functions to compute official SLU-F1, slot_f1_exact, entity TP/FP/FN,
intent accuracy (reported), copy-rate (reported, no clause),
induced-substitution count, the supplied-item audit, the phase-1
mapping/fallback summary, the silence-swap comparison, and the mechanical
Q-A / Q-B / VOID evaluators. Never opens a model session; never mutates the
attempt directory. See
``speech_aware_evidence_acquisition.analysis.pslu_s2_read`` for the
implementation and
``docs/readiness/2026-08-18-pslu-s2-preregistration-REGISTERED.md`` for the
pre-registered metrics and verdicts this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before any
work happens.

Usage:
    python scripts/pslu_s2_read.py \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-s2-183/attempt-<id>" \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/pslu-s2-read-report
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.pslu_s2_read import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
