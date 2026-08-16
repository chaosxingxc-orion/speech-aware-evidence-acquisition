#!/usr/bin/env python3
"""P2 R-ladder pinned offline read suite entry point.

Model-free: reads already-produced run bundles (run-manifest.json +
outputs.jsonl + trace.jsonl) under the five arms' stable run_dirs and
reuses the frozen scoring stack to compute macro/entity-WER, HER, RIR,
wrong-reference copy count, the co-primary paired Wilcoxon contrasts, and
the mechanical branch-rule evaluator. Never opens a model session; never
mutates an attempt directory. See
``speech_aware_evidence_acquisition.analysis.p2_reads`` for the
implementation and ``docs/arms/p2-rladder.arms`` /
``docs/p2-metric-definitions-mirror.md`` for the pre-registered reads,
branch rules, and metric definitions this tool implements.

Usage:
    python scripts/p2_reads.py \\
        --r0bias-run-dir   "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r0bias" \\
        --r1verify-run-dir "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r1verify" \\
        --r2draft-run-dir  "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r2draft" \\
        --r0wrong-run-dir  "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r0wrong" \\
        --r1wrong-run-dir  "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r1wrong" \\
        --output docs/checks/speech-aware-evidence-acquisition/p2-reads-report.json

r0bias's own COMPLETED attempt died at manifest bind and was salvaged
offline instead of re-flown (one-shot semantics); ``--r0bias-run-dir`` is
therefore mutually exclusive with ``--r0bias-salvage-dir`` (exactly one
required) --

    python scripts/p2_reads.py \\
        --r0bias-salvage-dir "docs/checks/speech-aware-evidence-acquisition/2026-08-16-p2-r0bias-salvage" \\
        --r1verify-run-dir "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r1verify" \\
        --r2draft-run-dir  "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r2draft" \\
        --r0wrong-run-dir  "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r0wrong" \\
        --r1wrong-run-dir  "$SPEECHRL_DATA_DIR/runs/SAEA-P2-r1wrong" \\
        --output docs/checks/speech-aware-evidence-acquisition/p2-reads-report.json
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.p2_reads import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
