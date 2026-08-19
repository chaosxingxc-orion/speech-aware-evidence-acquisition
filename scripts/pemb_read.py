#!/usr/bin/env python3
"""P-EMB pinned offline read suite entry point.

Model-free: loads an already-written embedding-vector manifest
(``rails.probes.pemb_flight.write_embedding_manifest``'s own shape) and
scores it with the pinned argmax-cosine matcher against scoring-side-only
gold, computing the registered verdict for whichever run is named. Never
opens a model session; never mutates the manifest.

See ``speech_aware_evidence_acquisition.analysis.pemb_read`` for the
implementation and
``docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md`` for the
pre-registered metrics and verdicts this tool implements.

Refuses to run twice against the same ``--output-dir`` (one-shot read
discipline): a pre-existing ``verdict.json`` there stops the read before
any work happens.

Usage:
    python scripts/pemb_read.py run-a \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/pemb1-read-report

    python scripts/pemb_read.py run-b \\
        --output-dir docs/checks/speech-aware-evidence-acquisition/pemb2-read-report
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.pemb_read import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
