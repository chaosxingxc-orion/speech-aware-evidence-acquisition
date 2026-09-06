#!/usr/bin/env python3
"""Model-free proof of the speech term the EVO-S1 prompt fit used, and of the
fold packets once they exist.

The prompt fit runs BEFORE ``SAEA-SLURP-EVO-FOLD-PACKETS-V2`` on purpose
(preregistration section 13: a geometry surprise must cost no packet contacts),
so it cannot read the folds' own packets and bounds the speech term instead with
``13 * ceil(audio_seconds / 0.96)``. This script is why that bound is evidence
rather than an assumption:

* PHASE 1, always: replay the bound against every one of the 1,000 committed
  DEV-1000 packets -- the same encoder, the same featcache build, the same
  packet root -- and fail closed on a single row whose realized token count
  exceeds it.
* PHASE 2, once the fold packets land: replay it against all 2,160 fold packets
  and record the realized maximum beside the bound the geometry was fitted
  against.

Zero model contacts, zero servers, zero sockets. Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python docs/checks/.../prompt-fit/verify.py <output.json>
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
PACKET_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
CHUNK_TOKENS, CHUNK_SECONDS = 13, 0.96
POPULATIONS = (
    ("DEV-1000", "slurp-speech-native-dev1000", "DEV-1000-promotion.json"),
    ("SLURP-EVO-FOLD-A-V2", "slurp-speech-native-evo-fold-a-1080", "EVO-FOLD-A-V2-promotion.json"),
    ("SLURP-EVO-FOLD-B-V2", "slurp-speech-native-evo-fold-b-1080", "EVO-FOLD-B-V2-promotion.json"),
)


def bound(seconds: float) -> int:
    return CHUNK_TOKENS * math.ceil(float(seconds) / CHUNK_SECONDS)


def main() -> int:
    from speech_aware_evidence_acquisition.core.model.speech_features import (
        load_speech_feature_packet,
    )

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("speech-token-bound.json")
    results = []
    for label, fragment, promotion in POPULATIONS:
        receipt = PACKET_ROOT / promotion
        if not receipt.exists():
            results.append({"population": label, "state": "PENDING", "promotion_receipt": str(receipt)})
            continue
        view = json.loads((REPO / "configs" / "dataset" / f"{fragment}.json").read_text(encoding="utf-8"))
        seconds = {str(item["packet_id"]): float(item["audio_seconds"]) for item in view["items"]}
        packets = json.loads(receipt.read_text(encoding="utf-8"))["packets"]
        violations, realized, bounds = [], [], []
        for entry in packets:
            packet_id = str(entry["packet_id"])
            tokens = sum(chunk.n_tokens for chunk in load_speech_feature_packet(PACKET_ROOT, packet_id).chunks)
            limit = bound(seconds[packet_id])
            realized.append(tokens)
            bounds.append(limit)
            if tokens > limit:
                violations.append({"packet_id": packet_id, "tokens": tokens, "bound": limit})
        results.append({
            "population": label,
            "state": "VERIFIED",
            "promotion_receipt": str(receipt),
            "rows": len(packets),
            "max_realized_tokens": max(realized),
            "max_bound_tokens": max(bounds),
            "max_shortfall_tokens": max(b - r for r, b in zip(realized, bounds)),
            "violations": violations,
            "pass": not violations,
        })
    document = {
        "schema": "saea-slurp-evo-s1-speech-token-bound-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "scope": "model-free replay of the prompt fit's speech term; zero contacts, zero servers",
        "formula": "13 * ceil(audio_seconds / 0.96)",
        "packet_root": str(PACKET_ROOT),
        "model_contacts": 0,
        "populations": results,
        "verdict": "PASS" if all(r.get("pass", True) for r in results) else "FAIL",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({r["population"]: {k: v for k, v in r.items() if k != "violations"} for r in results},
                     indent=2, sort_keys=True))
    return 0 if document["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
