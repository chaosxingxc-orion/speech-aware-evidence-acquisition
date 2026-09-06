#!/usr/bin/env python3
"""CLI: turn the EVO-S1 fold roster receipts into flyable products (MODEL-FREE).

Exposure row ``SAEA-SN-MF-SLURP-EVO-FOLD-SUPPLEMENTS-V2``. Per fold it writes
the D1 media supplement, the speech-native runtime view and the probe-sample
view, all from ONE measurement pass, and prints the model-free packet-coverage
audit the flight agent's preprocessing scope needs. Every build rule lives in
``analysis.slurp_evo_flight_products``; this file only resolves paths and
writes bytes. ZERO CONTACTS: flac bytes are hashed and flac HEADERS are read;
the SLURP loader is consulted for ``media_relpath`` and nothing else.
``--write`` lands the artifacts, which are refuse-on-overwrite.

Run in WSL2 (data root on /mnt/e, feature caches on ext4)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/build_slurp_evo_fold_flight_products.py --version V2 --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.slurp_evo_flight_products import (  # noqa: E402
    MAX_WORKERS,
    build_fold_products,
)
from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (  # noqa: E402
    DEFAULT_VERSION,
    ROSTER_SLUGS,
    roster_stem,
)
from speech_aware_evidence_acquisition.core.roster import read_roster  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402

PARENT_D1 = REPO_ROOT / "docs/receipts/artifacts/d1-identity.json"
ROSTERS = REPO_ROOT / "docs/receipts/rosters"
FOLDS = ("fold_a", "fold_b")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _writer(write: bool):
    """``(relpath, document) -> file sha256``; refuses to overwrite."""

    def emit(relpath: str, document: object) -> str:
        payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        path = REPO_ROOT / relpath
        if not write:
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if path.exists():
            raise SystemExit(f"refusing to overwrite an existing artifact: {relpath}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
        return _sha256_file(path)

    return emit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument(
        "--rosters",
        default=",".join(FOLDS),
        help=(
            "comma-separated roster names to build products for. The two folds are "
            "the default and are what SAEA-SN-MF-SLURP-EVO-FOLD-SUPPLEMENTS-V2 "
            "registered; 'exemplars' builds the SAME three artifacts for the "
            "proposer's own pool, which the text-only proposer arm needs because its "
            "draw ANCHORS are TRAIN rows and contracts.gate.FrozenCoreGate refuses a "
            "TRAIN row with no additive D1 receipt (row "
            "SAEA-SN-MF-SLURP-EVO-EXEMPLAR-SUPPLEMENT-V2)"
        ),
    )
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument(
        "--feature-cache-root", type=Path, default=Path.home() / "feat-cache"
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    # media_relpath ONLY: no sentence, scenario, action, intent or entity
    # field is read out of the loader, and none reaches any artifact here.
    relpath_by_id = {
        record.sample_id: record.media_relpath
        for record in load_slurp_split(lock, root, "train")
    }
    parent = json.loads(PARENT_D1.read_text(encoding="utf-8"))
    parent_sha256 = _sha256_file(PARENT_D1)
    writer = _writer(args.write)

    requested = tuple(name.strip() for name in str(args.rosters).split(",") if name.strip())
    unknown = sorted(set(requested) - set(ROSTER_SLUGS))
    if unknown:
        raise SystemExit(f"unknown roster name(s): {unknown}; known: {sorted(ROSTER_SLUGS)}")

    summary: dict[str, object] = {}
    for name in requested:
        roster_path = ROSTERS / f"{roster_stem(name, args.version)}.json"
        products = build_fold_products(
            read_roster(roster_path),
            slug=ROSTER_SLUGS[name],
            version=args.version,
            relpath_by_id=relpath_by_id,
            data_root=root,
            parent_d1=parent,
            parent_d1_sha256=parent_sha256,
            feature_cache_root=args.feature_cache_root,
            workers=args.workers,
            writer=writer,
        )
        summary[name] = {
            "roster_receipt": f"docs/receipts/rosters/{roster_path.name}",
            "roster_receipt_file_sha256": _sha256_file(roster_path),
            **products,
        }
    print(
        json.dumps(
            {
                "written": args.write,
                "parent_d1_sha256": parent_sha256,
                "rosters": list(requested),
                "folds": summary,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
