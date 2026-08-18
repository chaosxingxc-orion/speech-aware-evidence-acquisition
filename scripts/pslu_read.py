#!/usr/bin/env python3
"""P-SLU pinned offline read suite entry point.

Model-free: reads an already-produced flight attempt directory (``outputs.jsonl``
+ ``predicted-scenarios.json`` + ``flight-receipt.json``, the shape
``docs/checks/speech-aware-evidence-acquisition/2026-08-17-pslu-flight/launcher/
launch_pslu_flight.py`` writes) and reuses the frozen SLURP scoring stack plus
the frozen roster-construction function to compute official SLU-F1,
slot_f1_exact, intent accuracy, copy-rate, induced-substitution count, the
silence-swap comparison, and the mechanical branch-rule evaluator (SUPPLY-
CONVERTS / COPY-TRAP / DOSE-CONFIRM / INERT / VOID). Never opens a model
session; never mutates the attempt directory. See
``speech_aware_evidence_acquisition.analysis.pslu_read`` for the
implementation and
``docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md`` for the
pre-registered metrics and branch rules this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before any
work happens.

Usage:
    python scripts/pslu_read.py \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/attempt-<id>" \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/pslu-read-report
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.pslu_read import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
