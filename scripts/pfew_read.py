#!/usr/bin/env python3
"""P-FEW pinned offline read suite entry point.

Model-free: reads an already-produced P-FEW flight attempt directory
(``outputs.jsonl`` + ``flight-receipt.json``, the shape
``rails.probes.pfew_flight.run_pfew_flight`` writes) and computes closed-set
accuracy per arm vs gold, mapping-outcome distributions, the per-sample
3-arm table, the paired bootstrap on both registered contrasts, the
skew-label capture rate, the mandatory reachability statement, and the
CI-gated FS-HELPS/FS-INERT/BIAS-SENSITIVE/INCONCLUSIVE-FEW evaluator. Never
opens a model session; never mutates the attempt directory. See
``speech_aware_evidence_acquisition.analysis.pfew_read`` for the
implementation and
``docs/readiness/2026-08-19-pfew-preregistration-REGISTERED.md`` for the
pre-registered metrics and verdicts this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before any
work happens.

Usage:
    python scripts/pfew_read.py \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pfew-180/attempt-<id>" \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/pfew-read-report
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.pfew_read import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
