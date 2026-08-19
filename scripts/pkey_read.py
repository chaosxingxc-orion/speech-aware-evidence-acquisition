#!/usr/bin/env python3
"""P-KEY pinned offline read suite entry point.

Model-free: reads an already-produced flight attempt directory
(``outputs.jsonl`` + ``flight-receipt.json``, the shape
``rails.probes.pkey_flight.run_pkey_flight`` writes) and reuses the frozen
SLURP scoring stack plus the frozen roster-construction function to compute
per-arm official SLU-F1, Delta_AUD/Delta_TXT/INTERACTION with the four
registered verdicts, the perception-gap descriptive, the converted-set
difference (with an optional soft P-PHON cross-reference), T0-vs-gold WER
(scoring-side only -- gold text never enters any prompt path), induced-
substitution count, the silence-swap comparison, and the mechanical VOID
evaluator. Never opens a model session; never mutates the attempt directory.
See ``speech_aware_evidence_acquisition.analysis.pkey_read`` for the
implementation and
``docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md`` for the
pre-registered metrics and verdicts this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before any
work happens.

Usage:
    python scripts/pkey_read.py \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey-303/attempt-<id>" \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/pkey-read-report \\
        [--pphon-verdict <path to an already-written P-PHON verdict.json>]
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.pkey_read import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
