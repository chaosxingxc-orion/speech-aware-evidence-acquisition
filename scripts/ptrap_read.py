#!/usr/bin/env python3
"""P-TRAP pinned offline read suite entry point.

Model-free: reads an already-produced P-TRAP flight attempt directory
(``outputs.jsonl`` + ``flight-receipt.json``, the shape
``rails.probes.ptrap_flight.run_ptrap_flight`` writes) and reuses the frozen
SLURP scoring stack plus the consumed P-SLU read suite's own primitives to
compute the capture detector, per-sample table, SLU-F1 guardrail vs the
cited consumed A3 aggregate, induced-substitution count, empty/parse rates,
the per-sample paired cluster bootstrap CI, the mandatory reachability
statement, and the CI-gated ACOUSTIC-MEDIATED/KEY-ONLY-MATCHING/
INCONCLUSIVE-TRAP evaluator. Never opens a model session; never mutates the
attempt directory. See
``speech_aware_evidence_acquisition.analysis.ptrap_read`` for the
implementation and
``docs/readiness/2026-08-19-ptrap-preregistration-REGISTERED.md`` for the
pre-registered metrics and verdicts this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before any
work happens.

Usage:
    python scripts/ptrap_read.py \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-ptrap-120/attempt-<id>" \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/ptrap-read-report
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.ptrap_read import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
