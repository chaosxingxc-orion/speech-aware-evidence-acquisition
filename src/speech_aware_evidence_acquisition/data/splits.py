"""Split identity and the frozen discovery/dev/confirmatory partition (R0).

Convention (matches the E0 ledger row SAEA-E0-CLOSURE-2026-08-04 exactly):
a split's identity hash is SHA-256 over the LF-joined sorted list of
carrier-prefixed sample ids ``f"{lock_key}/{sample_id}"`` with no trailing
newline. The confirmatory split is enumerated from media file names only —
no annotation content is read here.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from ..e0.artifacts import write_json_artifact
from .loader import LoaderError, earnings22_subset10_ids, load_earnings22
from .lock import asset_dir, data_root, load_lock, umbrella_lock_path

SPLITS_SCHEMA = "saea-splits-v1"
SPLITS_RECEIPT_NAME = "splits.json"
_CONVENTION = (
    "sha256 over LF-joined sorted carrier-prefixed sample ids "
    "(f'{lock_key}/{sample_id}', UTF-8, no trailing newline)"
)


def split_identity_hash(prefixed_ids: Iterable[str]) -> str:
    return hashlib.sha256("\n".join(sorted(prefixed_ids)).encode("utf-8")).hexdigest()


def prefixed(lock_key: str, ids: Iterable[str]) -> list[str]:
    return sorted(f"{lock_key}/{sample_id}" for sample_id in ids)


@dataclass(frozen=True)
class SplitSpec:
    name: str
    carrier_lock_key: str
    split_role: str
    ids: tuple[str, ...]
    identity_hash: str

    @property
    def count(self) -> int:
        return len(self.ids)


def _spec(name: str, lock_key: str, role: str, raw_ids: Iterable[str]) -> SplitSpec:
    ids = tuple(prefixed(lock_key, raw_ids))
    if not ids:
        raise LoaderError(f"split {name!r} resolved to zero samples")
    return SplitSpec(
        name=name,
        carrier_lock_key=lock_key,
        split_role=role,
        ids=ids,
        identity_hash=split_identity_hash(ids),
    )


def discovery_split(lock: Mapping[str, object], root: Path) -> SplitSpec:
    media_dir = asset_dir(lock, "earnings21-original", root) / "media"
    if not media_dir.is_dir():
        raise LoaderError(f"earnings21 media directory missing: {media_dir}")
    ids = [
        path.name[: -len(".mp3")]
        for path in media_dir.glob("*.mp3")
        if path.is_file()
    ]
    return _spec("discovery", "earnings21-original", "discovery", ids)


def dev_split(lock: Mapping[str, object], root: Path) -> SplitSpec:
    return _spec(
        "dev", "earnings22-original", "dev", earnings22_subset10_ids(lock, root)
    )


def confirmatory_split(lock: Mapping[str, object], root: Path) -> SplitSpec:
    all_ids = {sample.sample_id for sample in load_earnings22(lock, root)}
    subset10 = set(earnings22_subset10_ids(lock, root))
    if not subset10 <= all_ids:
        raise LoaderError("subset10 is not a subset of earnings22 media identity")
    return _spec(
        "confirmatory", "earnings22-original", "confirmatory", all_ids - subset10
    )


def freeze_splits(
    lock: Mapping[str, object], root: Path, receipts_dir: Path
) -> dict[str, object]:
    splits = {
        spec.name: {
            "carrier_lock_key": spec.carrier_lock_key,
            "split_role": spec.split_role,
            "count": spec.count,
            "ids": list(spec.ids),
            "identity_hash": spec.identity_hash,
        }
        for spec in (
            discovery_split(lock, root),
            dev_split(lock, root),
            confirmatory_split(lock, root),
        )
    }
    document: dict[str, object] = {
        "schema": SPLITS_SCHEMA,
        "convention": _CONVENTION,
        "splits": splits,
        "note": (
            "confirmatory ids are enumerated from media file names only and "
            "remain unread; any confirmatory result read requires Stage-3 "
            "authority or a dated owner allowance (consolidated contract §7)"
        ),
    }
    write_json_artifact(Path(receipts_dir) / SPLITS_RECEIPT_NAME, document)
    return document


def main() -> int:
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    receipts = Path(__file__).resolve().parents[3] / "docs" / "receipts"
    document = freeze_splits(lock, root, receipts)
    for name, split in document["splits"].items():
        print(f"{name}: {split['count']} samples, {split['identity_hash']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
