#!/usr/bin/env python3
"""P-EMB-3L pinned offline read suite entry point.

Model-free: loads the three already-written per-arm embedding-vector
manifests (``rails.probes.pemb3l_flight.write_pemb3l_arm_manifest``'s own
shape) and scores each with the pinned argmax-cosine matcher against
scoring-side-only gold, computing the registered three-arm-sweep verdict.
Never opens a model session; never mutates a manifest.

See ``speech_aware_evidence_acquisition.analysis.pemb3l_read`` for the
implementation and
``docs/readiness/2026-08-20-pemb3l-preregistration-REGISTERED.md`` for the
pre-registered metrics and verdict this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before
any work happens.

Usage:
    python scripts/pemb3l_read.py \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/pemb3l-read-report
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.pemb3l_read import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
