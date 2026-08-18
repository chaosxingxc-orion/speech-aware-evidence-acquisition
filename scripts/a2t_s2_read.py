#!/usr/bin/env python3
"""P-A2T Stage-2 supply-probe pinned offline read suite entry point.

Model-free: reads an already-produced flight attempt directory
(``outputs.jsonl`` + ``flight-receipt.json`` + ``{RUN_ID}.arm-plan.json``,
the shape ``docs/checks/speech-aware-evidence-acquisition/
2026-08-18-a2t-s2-flight/launcher/launch_pa2t_s2.py`` writes) plus the
frozen Stage-1 A0 headroom manifest, and reuses the frozen tool-call
scoring stack (``reproduction.toolcall_scoring``,
``data.audio2tool.load_expected_calls``) to compute per-arm and per-tier
EM-conversion rate, tool-selection retention, slot precision/recall/F1,
empty-call rate, induced-substitution count, and parse-failure rate, then
mechanically evaluates the VOID / COPY-TRAP / SCHEMA-ONLY / SUPPLY-CONVERTS
/ INERT branch rules (with the DOSE point reported as a secondary,
descriptive signal). Never opens a model session; never mutates the
attempt directory. See
``speech_aware_evidence_acquisition.analysis.a2t_s2_read`` for the
implementation and
``docs/readiness/2026-08-18-pa2t-stage2-preregistration-REGISTERED.md``
for the pre-registered metrics and branch rules this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before any
work happens.

Usage:
    python scripts/a2t_s2_read.py \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2-120/attempt-<id>" \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/a2t-s2-read-report
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.a2t_s2_read import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
