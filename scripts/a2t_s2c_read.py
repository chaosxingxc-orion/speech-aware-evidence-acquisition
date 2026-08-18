#!/usr/bin/env python3
"""P-A2T Stage-2c form-robustness probe pinned offline read suite entry point.

Model-free: reads an already-produced C1/C2/C3 flight attempt directory
(``outputs.jsonl`` + ``flight-receipt.json``, the row shape
``rails.probes.a2t_s2c_flight.run_a2t_s2c_flight`` writes -- IDENTICAL to
Stage-2/2b's own, reused directly) plus the frozen Stage-1 A0 headroom
manifest and Stage-2's OWN already-flown ``{RUN_ID}.arm-plan.json`` (reused
verbatim -- default resolved from the committed
``configs/probes/g0-binding/a2t-s2c-flight.json``'s own
``stage2_arm_plan_path``, ``$SPEECHRL_DATA_DIR`` expanded), and reuses the
frozen tool-call scoring stack (``reproduction.toolcall_scoring``,
``data.audio2tool.load_expected_calls``) to compute per-arm and per-tier
EM-conversion rate, tool-selection retention, slot precision/recall/F1,
empty-call rate, induced-substitution count, and parse-failure rate, then
mechanically evaluates the primary form-robustness verdict (ROBUST /
FORM-FRAGILE / INCONCLUSIVE-C, from C1+C2 jointly) and the independent
DEPLOY-AUGMENT overlay (DEPLOYABLE / CHANNEL-REOPENED / no flag, from C3
alone). Never opens a model session; never mutates the attempt directory.
See ``speech_aware_evidence_acquisition.analysis.a2t_s2c_read`` for the
implementation and
``docs/readiness/2026-08-18-pa2t-stage2c-preregistration-REGISTERED.md``
for the pre-registered metrics and verdict rules this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before any
work happens.

Usage:
    python scripts/a2t_s2c_read.py \\
        "$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-a2t-s2c-120/attempt-<id>" \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/a2t-s2c-read-report
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.a2t_s2c_read import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
