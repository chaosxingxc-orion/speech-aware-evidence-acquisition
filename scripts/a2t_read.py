#!/usr/bin/env python3
"""P-A2T Stage-1 A0 baseline pinned offline read suite entry point.

Model-free: reads an already-produced flight attempt directory
(``outputs.jsonl`` + ``flight-receipt.json``, the shape
``docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-flight/
launcher/launch_pa2t_a0.py`` writes) and reuses
``rails.adapters.audio2tool.Audio2ToolAdapter.score`` -- the SAME frozen
scorer the flight itself used -- to compute per-tier and overall
tool-accuracy/exact-match, the tool-acc-minus-EM gap (the retired
84.6%/15.6% headroom claim's replacement number), the empty-tool-call rate,
and the Stage-2 headroom sample list (``tool_accuracy == 1.0 AND
exact_match == 0.0``). Carries no branch rules (this is a baseline read, not
a probe). Never opens a model session; never mutates the attempt directory.
See ``speech_aware_evidence_acquisition.analysis.a2t_read`` for the
implementation and
``docs/readiness/2026-08-17-pa2t-preregistration-draft.md`` section 8 for
the Stage-1 purpose this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before any
work happens.

Usage:
    python scripts/a2t_read.py \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-BASE-a2t-a0-400/attempt-20260818T055500Z-res315" \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/pa2t-a0-read-report
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.a2t_read import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
