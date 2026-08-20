#!/usr/bin/env python3
"""P-EMB-4R pinned offline read suite entry point.

Model-free: reads an already-produced P-EMB-4R flight's own
``retrieval_plan.json`` (the shape ``rails.probes.pemb4r_flight.
build_retrieval_plan_document``/``write_retrieval_plan`` writes) plus
explicit, caller-supplied flight facts (dropped arms, the pooling-override
scope flag per model, measured repeat-call jitter deltas per model) and
computes per-arm vote-accuracy (top-K majority, tie -> highest mean cosine),
recall@1/3/5, per-sample argmax-stability vs the measured jitter noise
floor, cross-arm agreement, the feasibility matrix, and the registered
verdict evaluators. Never opens a model session; never mutates a flight
artifact. See ``speech_aware_evidence_acquisition.analysis.pemb4r_read`` for
the implementation and ``docs/readiness/
2026-08-20-pemb4r-preregistration-REGISTERED.md`` for the pre-registered
metrics and verdicts this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before any
work happens.

Usage:
    python scripts/pemb4r_read.py \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/pemb4r-read-report \\
        [--dropped-arms-json dropped.json] \\
        [--pooling-override-json pooling.json] \\
        [--repeat-delta-json jitter.json]
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.pemb4r_read import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
