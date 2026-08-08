"""Split receipt authenticity: strict parse + live recomputation (R0 repair T1).

``docs/receipts/splits.json`` is an external, editable artifact. Before it may
reach a model-facing run, this module enforces two independent trust checks:

1. **Internal consistency** (:func:`verify_receipt_document`) — the document
   carries the expected schema, exactly the three contract splits, and each
   split's ``split_role``/``carrier_lock_key``/``count``/``ids``/
   ``identity_hash`` are mutually consistent (sorted, unique, carrier-prefixed
   ids; ``identity_hash`` independently recomputed from ``ids``; same-carrier
   splits pairwise disjoint).
2. **Live recomputation** (:func:`load_verified_split`) — the split is
   independently re-derived from the current carrier loader
   (``data.splits.discovery_split`` / ``dev_split`` / ``confirmatory_split``)
   and must match the receipt byte-for-byte (ids and identity_hash).

A receipt that only satisfies (1) is self-certifying, not verified: it proves
the document is internally coherent, not that it describes reality. Only a
receipt that survives both checks is safe for a model-facing path to consume.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..data.splits import (
    SPLITS_RECEIPT_NAME,
    SPLITS_SCHEMA,
    confirmatory_split,
    dev_split,
    discovery_split,
    split_identity_hash,
)

# Each contract split's name IS its declared role (matches the E0 ledger
# convention baked into data/splits.py: freeze_splits stores split_role ==
# the split's own key for all three splits).
_CONTRACT_ROLE = {"discovery": "discovery", "dev": "dev", "confirmatory": "confirmatory"}

_LIVE_SPLIT = {
    "discovery": discovery_split,
    "dev": dev_split,
    "confirmatory": confirmatory_split,
}


class SplitReceiptError(RuntimeError):
    """A splits receipt failed strict internal parsing or live recomputation."""


@dataclass(frozen=True)
class VerifiedSplit:
    name: str
    carrier_lock_key: str
    split_role: str
    ids: tuple[str, ...]
    prefixed_ids: tuple[str, ...]
    identity_hash: str


def _fail(split_name: str, reason: str) -> SplitReceiptError:
    return SplitReceiptError(f"splits receipt: split {split_name!r} {reason}")


def verify_receipt_document(document: Mapping[str, object]) -> dict[str, VerifiedSplit]:
    """Strict, self-contained parse of a splits receipt document.

    Verifies schema, exact split key set, and per-split shape (role, carrier
    prefix, sorted+unique ids, count, identity_hash recomputed from ids), plus
    pairwise disjointness between same-carrier splits. Raises
    :class:`SplitReceiptError` naming the offending split on any drift; does
    not touch disk or the carrier loader.
    """

    if not isinstance(document, Mapping):
        raise SplitReceiptError("splits receipt: document must be a JSON object")
    if document.get("schema") != SPLITS_SCHEMA:
        raise SplitReceiptError(
            f"splits receipt: schema {document.get('schema')!r} != {SPLITS_SCHEMA!r}"
        )
    splits = document.get("splits")
    if not isinstance(splits, Mapping):
        raise SplitReceiptError("splits receipt: 'splits' must be a JSON object")
    if set(splits) != set(_CONTRACT_ROLE):
        raise SplitReceiptError(
            f"splits receipt: split key set {sorted(splits)} != {sorted(_CONTRACT_ROLE)}"
        )

    verified: dict[str, VerifiedSplit] = {}
    for name, expected_role in _CONTRACT_ROLE.items():
        entry = splits[name]
        if not isinstance(entry, Mapping):
            raise _fail(name, "must be a JSON object")

        role = entry.get("split_role")
        if role != expected_role:
            raise _fail(name, f"split_role {role!r} != contract role {expected_role!r}")

        carrier = entry.get("carrier_lock_key")
        if not isinstance(carrier, str) or not carrier:
            raise _fail(name, "carrier_lock_key must be a non-empty string")

        raw_ids = entry.get("ids")
        if not isinstance(raw_ids, list) or not raw_ids or not all(
            isinstance(sample_id, str) for sample_id in raw_ids
        ):
            raise _fail(name, "ids must be a non-empty list of strings")

        prefix = f"{carrier}/"
        for prefixed_id in raw_ids:
            if not prefixed_id.startswith(prefix) or prefixed_id == prefix:
                raise _fail(name, f"id {prefixed_id!r} is not prefixed {prefix!r}")

        if len(set(raw_ids)) != len(raw_ids):
            raise _fail(name, "ids contain a duplicate")
        if list(raw_ids) != sorted(raw_ids):
            raise _fail(name, "ids are not sorted")

        count = entry.get("count")
        if count != len(raw_ids):
            raise _fail(name, f"count {count!r} != len(ids) {len(raw_ids)}")

        recomputed_hash = split_identity_hash(raw_ids)
        stored_hash = entry.get("identity_hash")
        if recomputed_hash != stored_hash:
            raise _fail(
                name,
                f"identity_hash {stored_hash!r} does not match the hash recomputed "
                f"from ids ({recomputed_hash!r})",
            )

        bare_ids = tuple(prefixed_id[len(prefix):] for prefixed_id in raw_ids)
        verified[name] = VerifiedSplit(
            name=name,
            carrier_lock_key=carrier,
            split_role=role,
            ids=bare_ids,
            prefixed_ids=tuple(raw_ids),
            identity_hash=stored_hash,
        )

    by_carrier: dict[str, list[str]] = {}
    for split in verified.values():
        by_carrier.setdefault(split.carrier_lock_key, []).append(split.name)
    for carrier, names in by_carrier.items():
        for i, left in enumerate(names):
            for right in names[i + 1 :]:
                overlap = set(verified[left].prefixed_ids) & set(verified[right].prefixed_ids)
                if overlap:
                    raise SplitReceiptError(
                        f"splits receipt: splits {left!r} and {right!r} share carrier "
                        f"{carrier!r} but are not disjoint: {sorted(overlap)[:5]}"
                    )

    return verified


def load_verified_split(
    repo_root: Path, split_name: str, lock: Mapping[str, object], root: Path
) -> VerifiedSplit:
    """Load, strictly verify, and live-recompute one split from the receipt.

    Raises :class:`SplitReceiptError` if the receipt is missing/unreadable,
    fails :func:`verify_receipt_document`, names an unknown split, or if the
    live recomputation via the current carrier loader (``data.splits``)
    disagrees with the receipt on ids or identity_hash.
    """

    # P1 scaffold: any split name OUTSIDE the three contract splits resolves
    # as a frozen probe-sample receipt (docs/receipts/probe-samples/<name>.json,
    # sample-once policy) -- see reproduction.probe_split's module docstring
    # for the receipt-hash vs run-hash convention and the trust split. The
    # three contract names below keep the exact strict-parse + live-recompute
    # path they always had; the import is deferred because probe_split imports
    # THIS module for VerifiedSplit/SplitReceiptError.
    if split_name not in _CONTRACT_ROLE:
        from ..reproduction.probe_split import load_verified_probe_split

        return load_verified_probe_split(repo_root, split_name)

    receipt_path = Path(repo_root) / "docs" / "receipts" / SPLITS_RECEIPT_NAME
    if not receipt_path.is_file():
        raise SplitReceiptError(
            f"splits receipt missing: {receipt_path} (freeze splits first)"
        )
    try:
        document = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SplitReceiptError(
            f"cannot read splits receipt {receipt_path}: {error}"
        ) from error

    verified = verify_receipt_document(document)
    if split_name not in verified:
        raise SplitReceiptError(
            f"unknown split {split_name!r}; frozen splits: {sorted(verified)}"
        )
    split = verified[split_name]

    live_fn = _LIVE_SPLIT[split_name]
    live = live_fn(lock, root)
    if tuple(live.ids) != split.prefixed_ids or live.identity_hash != split.identity_hash:
        raise _fail(
            split_name,
            "does not match live recomputation from the current carrier loader",
        )

    return split
