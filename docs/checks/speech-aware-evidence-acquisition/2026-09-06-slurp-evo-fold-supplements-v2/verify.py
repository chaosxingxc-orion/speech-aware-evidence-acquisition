#!/usr/bin/env python3
"""Verify the EVO-S1 V2 fold flight products offline, through the real gate.

Zero contacts. For each fold this re-opens the committed artifacts and asks
the production checks -- not a re-implementation of them -- whether they hold:

1. ``core.roster.read_roster`` recomputes the roster receipt's own
   ``split_identity_hash`` fail-closed;
2. ``contracts.gate.FrozenCoreGate.verify_media_identity`` re-hashes every one
   of the fold's flac files against the D1 media supplement, resolving D1
   through the E0 closure receipt exactly as a real model touch does. This is
   the check that decides whether the fold can ever be sent to the frozen
   core, and it reads only ``e0_receipt``, ``data_root`` and the supplement --
   no model, no runtime, no ledger;
3. ``reproduction.probe_split.load_verified_probe_split`` parses the
   probe-sample view and derives the run-identity hash the dataset fragment
   publishes, so fragment, probe receipt and roster receipt agree by
   construction;
4. the runtime view's own ``runtime_view_sha256`` is recomputed, and its item
   set is compared id by id with the roster's.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python docs/checks/speech-aware-evidence-acquisition/\\
2026-09-06-slurp-evo-fold-supplements-v2/verify.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.slurp_evo_flight_products import (  # noqa: E402
    canonical_sha256,
)
from speech_aware_evidence_acquisition.contracts.gate import FrozenCoreGate  # noqa: E402
from speech_aware_evidence_acquisition.core.roster import read_roster  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.probe_split import (  # noqa: E402
    load_verified_probe_split,
)

FOLDS = {
    "fold_a": (
        "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
        "configs/dataset/slurp-speech-native-evo-fold-a-1080.json",
        "receipts/artifacts/d1-slurp-evo-fold-a-v2.json",
    ),
    "fold_b": (
        "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
        "configs/dataset/slurp-speech-native-evo-fold-b-1080.json",
        "receipts/artifacts/d1-slurp-evo-fold-b-v2.json",
    ),
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(name: str, roster_rel: str, view_rel: str, supplement_rel: str) -> dict:
    roster = read_roster(REPO_ROOT / roster_rel)
    view = json.loads((REPO_ROOT / view_rel).read_text(encoding="utf-8"))
    unsigned = {k: v for k, v in view.items() if k != "runtime_view_sha256"}
    if view["runtime_view_sha256"] != canonical_sha256(unsigned):
        raise SystemExit(f"{name}: runtime view fails its own hash")
    if canonical_sha256(roster) != view["source_binding_sha256"]:
        raise SystemExit(f"{name}: runtime view does not bind this roster receipt")
    roster_ids = sorted(str(item["sample_id"]) for item in roster["items"])
    view_ids = sorted(str(item["sample_id"]) for item in view["items"])
    if roster_ids != view_ids:
        raise SystemExit(f"{name}: runtime view and roster name different samples")

    supplement_path = REPO_ROOT / "docs" / supplement_rel
    gate = FrozenCoreGate(
        e0_receipt=REPO_ROOT / "docs" / "receipts" / "e0-closure.json",
        runtime_receipt=REPO_ROOT / "docs" / "receipts" / "runtime-q4km.json",
        data_root=data_root(),
        lock_path=REPO_ROOT / "docs" / "datasets.lock.json",
        runtime_root=REPO_ROOT,
        exposure_ledger=REPO_ROOT / "docs" / "exposure-ledger.md",
        source_root=REPO_ROOT,
        d1_media_supplement=supplement_path,
        d1_media_supplement_sha256=_sha256_file(supplement_path),
    )
    gate.verify_media_identity(
        "slurp",
        {
            str(item["sample_id"]): (
                str(item["media_relpath"]),
                float(item["audio_seconds"]),
            )
            for item in view["items"]
        },
    )
    verified = load_verified_probe_split(REPO_ROOT, str(view["split_name"]))
    if verified.identity_hash != view["split_identity_hash"]:
        raise SystemExit(f"{name}: probe receipt and fragment disagree on run identity")
    if verified.split_role != view["split_role"] or verified.carrier_lock_key != "slurp":
        raise SystemExit(f"{name}: probe receipt role or carrier disagrees")
    if list(verified.ids) != view_ids:
        raise SystemExit(f"{name}: probe receipt and fragment name different samples")
    return {
        "roster_receipt": roster_rel,
        "roster_id": roster["roster_id"],
        "dataset_fragment": view_rel,
        "d1_media_supplement": f"docs/{supplement_rel}",
        "d1_media_supplement_sha256": gate.d1_media_supplement_sha256,
        "probe_sample_view": f"docs/receipts/probe-samples/{view['split_name']}.json",
        "rows": len(view_ids),
        "audio_seconds_total": view["audio_seconds_total"],
        "run_identity_hash": view["split_identity_hash"],
        "receipt_identity_hash": json.loads(
            (
                REPO_ROOT / "docs" / "receipts" / "probe-samples" / f"{view['split_name']}.json"
            ).read_text(encoding="utf-8")
        )["split_identity_hash"],
        "runtime_view_sha256": view["runtime_view_sha256"],
        "verify_media_identity": "PASS",
        "load_verified_probe_split": "PASS",
        "read_roster": "PASS",
    }


def main() -> int:
    report = {
        "schema": "saea-slurp-evo-fold-supplement-verification-v1",
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": "SAEA-SN-MF-SLURP-EVO-FOLD-SUPPLEMENTS-V2",
        "contacts": {"model": 0, "gpu": 0, "network": 0, "tokenizer": 0, "scorer": 0},
        "parent_d1_sha256": _sha256_file(
            REPO_ROOT / "docs" / "receipts" / "artifacts" / "d1-identity.json"
        ),
        "folds": {name: verify(name, *paths) for name, paths in FOLDS.items()},
    }
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    (HERE / "verify.json").write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
